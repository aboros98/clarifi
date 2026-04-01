"""Clarifi agent graph — ReAct architecture with memU long-term memory.

Flow: skill_loader → memory_retriever → react_agent → memory_saver → END

- skill_loader: LLM selects .md skills + tools
- memory_retriever: fetch relevant context from memU (if enabled)
- react_agent: Gemini call with tools + skill + memory context
- memory_saver: store conversation in memU for future recall (async)
"""

import asyncio
import logging
import time
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from clarifi.agent.context import current_user_id
from clarifi.agent.logging_middleware import wrap_tools_with_logging
from clarifi.agent.prompts import SYSTEM_PROMPT
from clarifi.config import settings
from clarifi.llm import get_llm
from clarifi.memory.memu_client import get_memu_service
from clarifi.memory.memu_client import memorize as memu_memorize
from clarifi.memory.memu_client import retrieve as memu_retrieve
from clarifi.skills.loader import (
    format_skill_context,
    get_tools_for_skills,
    select_skills_llm,
)
from clarifi.tools import ALL_TOOLS

logger = logging.getLogger("clarifi.graph")


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    skill_context: str
    bound_tool_names: list[str]
    memory_context: str
    user_id: str
    mode: str  # "interactive" (default) or "background"


_TOOL_MAP = {t.name: t for t in ALL_TOOLS}


async def skill_loader(state: AgentState) -> dict:
    """Select skills. Background mode forces background_processing skill."""
    mode = state.get("mode", "interactive")
    t0 = time.monotonic()

    if mode == "background":
        from clarifi.skills.loader import _load_all_skills

        all_skills = _load_all_skills()
        bg_skill = all_skills.get("background_processing")
        if bg_skill:
            logger.debug("skill_loader: background mode (forced)")
            return {
                "skill_context": format_skill_context([bg_skill]),
                "bound_tool_names": get_tools_for_skills([bg_skill]),
            }

    # Interactive mode — LLM selects skills
    messages = state.get("messages", [])
    user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            user_msg = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    try:
        selected = await select_skills_llm(user_msg)
    except Exception:
        logger.exception("skill_loader: LLM selection failed, using all skills")
        from clarifi.skills.loader import _load_all_skills

        selected = list(_load_all_skills().values())

    names = [s["name"] for s in selected]
    elapsed = int((time.monotonic() - t0) * 1000)
    logger.info("skill_loader: %s (%dms)", names, elapsed)

    return {
        "skill_context": format_skill_context(selected),
        "bound_tool_names": get_tools_for_skills(selected),
    }


async def memory_retriever(state: AgentState) -> dict:
    """Fetch relevant memories from memU to inject into agent context."""
    if not get_memu_service():
        return {"memory_context": ""}

    user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, "type") and msg.type == "human":
            user_msg = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    if not user_msg:
        return {"memory_context": ""}

    user_id = state.get("user_id", "default")
    t0 = time.monotonic()

    try:
        memories = await memu_retrieve(user_msg, user_id=user_id, limit=5)
    except Exception:
        logger.exception("memory_retriever: failed for user=%s", user_id)
        return {"memory_context": ""}

    elapsed = int((time.monotonic() - t0) * 1000)

    if not memories:
        logger.debug("memory_retriever: no memories (%dms)", elapsed)
        return {"memory_context": ""}

    lines = ["## Remembered Context (from memU)"]
    for m in memories:
        content = m.get("content") or m.get("text") or m.get("summary", "")
        if content:
            lines.append(f"- {content[:200]}")

    logger.info(
        "memory_retriever: %d memories for user=%s (%dms)",
        len(memories), user_id, elapsed,
    )
    return {"memory_context": "\n".join(lines)}


async def react_agent_node(state: AgentState) -> dict:
    """Run the ReAct agent with filtered tools and injected context."""
    skill_context = state.get("skill_context", "")
    memory_context = state.get("memory_context", "")
    mode = state.get("mode", "interactive")
    bound_tool_names = set(state.get("bound_tool_names", []))
    user_id = state.get("user_id", "anonymous")
    t0 = time.monotonic()

    # Filter tools to what the skill needs + always-available tools
    always_available = {
        "ask_user", "search_documents", "list_documents",
        "get_document", "calculate", "discover_data", "search_data",
        "web_search",
    }
    wanted = bound_tool_names | always_available if bound_tool_names else set()

    if mode == "background" and wanted:
        tools = [t for t in ALL_TOOLS if t.name in wanted and t.name != "ask_user"]
    elif mode == "background":
        tools = [t for t in ALL_TOOLS if t.name != "ask_user"]
    elif wanted:
        tools = [t for t in ALL_TOOLS if t.name in wanted]
    else:
        tools = list(ALL_TOOLS)

    logged_tools = wrap_tools_with_logging(tools)

    # Fetch company context for this user
    from clarifi.api.onboarding import get_company_context

    company_context = await get_company_context(user_id)

    # Build system prompt: company + skills + memory + mode
    full_context = ""
    if mode == "background":
        full_context += (
            "## MOD BACKGROUND\n"
            "Procesezi automat, fără interacțiune cu utilizatorul.\n"
            "- NU întrebi nimic — nu e nimeni care să răspundă\n"
            "- Salvează cu confirmed=false (neconfirmat)\n"
            "- Dacă lipsesc date critice, salvează ce poți și continuă\n"
            "- NU genera răspunsuri conversaționale\n\n"
        )
    if company_context:
        full_context += company_context + "\n\n"
    full_context += skill_context
    if memory_context:
        full_context += "\n\n" + memory_context

    system_prompt = SYSTEM_PROMPT.format(skill_context=full_context)

    agent = create_react_agent(
        model=get_llm(),
        tools=logged_tools,
        prompt=system_prompt,
    )

    # Make user_id available to all tools via context variable
    current_user_id.set(user_id)

    try:
        result = await agent.ainvoke({"messages": state["messages"]})
    except Exception:
        logger.exception(
            "react_agent: failed (user=%s, mode=%s, tools=%d)",
            user_id, mode, len(tools),
        )
        raise

    elapsed = int((time.monotonic() - t0) * 1000)
    n_msgs = len(result.get("messages", []))
    tool_calls = [
        tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
        for m in result.get("messages", [])
        for tc in getattr(m, "tool_calls", [])
    ]
    logger.info(
        "react_agent: %d msgs, tools=%s (%dms, user=%s)",
        n_msgs, tool_calls or "none", elapsed, user_id,
    )

    return {"messages": result["messages"]}


async def memory_saver(state: AgentState) -> dict:
    """Store the conversation turn in memU for future recall (non-blocking)."""
    if not get_memu_service():
        return {}

    # Extract the latest user message and agent response
    user_msg = ""
    agent_msg = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, "type"):
            if msg.type == "ai" and msg.content and not agent_msg:
                content = msg.content
                if isinstance(content, list):
                    parts = []
                    for p in content:
                        if isinstance(p, dict) and p.get("text"):
                            parts.append(p["text"])
                        elif isinstance(p, str):
                            parts.append(p)
                    agent_msg = "\n".join(parts)
                else:
                    agent_msg = str(content)
            elif msg.type == "human" and not user_msg:
                user_msg = (
                    msg.content if isinstance(msg.content, str)
                    else str(msg.content)
                )
        if user_msg and agent_msg:
            break

    if user_msg and agent_msg:
        user_id = state.get("user_id", "default")
        task = asyncio.create_task(memu_memorize(
            f"User: {user_msg}\nAssistant: {agent_msg[:1000]}",
            {"source": "clarifi_chat", "user_id": user_id},
        ))

        # Attach error callback so exceptions aren't silently lost
        def _on_done(t: asyncio.Task):
            if t.exception():
                logger.error(
                    "memory_saver: background save failed (user=%s): %s",
                    user_id, t.exception(),
                )

        task.add_done_callback(_on_done)

    return {}


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("skill_loader", skill_loader)
    graph.add_node("memory_retriever", memory_retriever)
    graph.add_node("agent", react_agent_node)
    graph.add_node("memory_saver", memory_saver)

    graph.add_edge(START, "skill_loader")
    graph.add_edge("skill_loader", "memory_retriever")
    graph.add_edge("memory_retriever", "agent")
    graph.add_edge("agent", "memory_saver")
    graph.add_edge("memory_saver", END)
    return graph


_compiled_graph = None
_checkpointer = None


async def get_graph():
    """Get or create the compiled graph with conversation checkpointer."""
    global _compiled_graph, _checkpointer
    if _compiled_graph is None:
        db_url = settings.database_url
        if db_url.startswith("postgresql"):
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

                pg_url = db_url.replace(
                    "postgresql+asyncpg://", "postgresql://",
                )
                _checkpointer = AsyncPostgresSaver.from_conn_string(pg_url)
                await _checkpointer.setup()
                logger.info("Checkpointer: Supabase PostgreSQL")
            except Exception:
                logger.warning(
                    "PostgreSQL checkpointer failed, falling back to SQLite",
                    exc_info=True,
                )
                import aiosqlite

                conn = await aiosqlite.connect("memu.db")
                _checkpointer = AsyncSqliteSaver(conn=conn)
                await _checkpointer.setup()
        else:
            import aiosqlite

            conn = await aiosqlite.connect("memu.db")
            _checkpointer = AsyncSqliteSaver(conn=conn)
            await _checkpointer.setup()
            logger.info("Checkpointer: local SQLite (memu.db)")

        graph = build_graph()
        _compiled_graph = graph.compile(checkpointer=_checkpointer)
    return _compiled_graph


async def close_graph():
    """Close checkpointer connections on shutdown."""
    global _checkpointer
    if _checkpointer is not None:
        try:
            if hasattr(_checkpointer, 'conn') and _checkpointer.conn:
                await _checkpointer.conn.close()
        except Exception:
            pass
