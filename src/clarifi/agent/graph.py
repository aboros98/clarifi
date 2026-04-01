"""Clarifi agent graph — ReAct architecture with memU long-term memory.

Flow: skill_loader → memory_retriever → react_agent → memory_saver → END

- skill_loader: keyword match → select .md skills + tools (no LLM)
- memory_retriever: fetch relevant context from memU (if enabled)
- react_agent: single Gemini call with tools + skill + memory context
- memory_saver: store conversation in memU for future recall (async)
"""

import asyncio
import logging
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from clarifi.agent.logging_middleware import wrap_tools_with_logging
from clarifi.agent.prompts import SYSTEM_PROMPT
from clarifi.config import settings
from clarifi.llm import get_llm
from clarifi.memory.memu_client import get_memu_service, memorize as memu_memorize, retrieve as memu_retrieve
from clarifi.skills.loader import format_skill_context, get_tools_for_skills, select_skills_llm
from clarifi.tools import ALL_TOOLS

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    skill_context: str
    bound_tool_names: list[str]
    memory_context: str
    user_id: str
    mode: str  # "interactive" (default) or "background"


_TOOL_MAP = {t.name: t for t in ALL_TOOLS}


async def skill_loader(state: AgentState) -> dict:
    """Select skills. Background mode forces background_processing skill (no LLM routing)."""
    mode = state.get("mode", "interactive")

    if mode == "background":
        # Force background skill — no LLM routing, deterministic
        from clarifi.skills.loader import _load_all_skills
        all_skills = _load_all_skills()
        bg_skill = all_skills.get("background_processing")
        if bg_skill:
            return {
                "skill_context": format_skill_context([bg_skill]),
                "bound_tool_names": get_tools_for_skills([bg_skill]),
            }

    # Interactive mode — LLM selects skills
    messages = state.get("messages", [])
    user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            user_msg = msg.content
            break

    selected = await select_skills_llm(user_msg)
    context = format_skill_context(selected)
    tool_names = get_tools_for_skills(selected)

    return {
        "skill_context": context,
        "bound_tool_names": tool_names,
    }


async def memory_retriever(state: AgentState) -> dict:
    """Fetch relevant memories from memU to inject into agent context.
    Uses direct Python import of memU (self-hosted via Supabase PostgreSQL)."""
    if not get_memu_service():
        return {"memory_context": ""}

    user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, "type") and msg.type == "human":
            user_msg = msg.content
            break

    if not user_msg:
        return {"memory_context": ""}

    user_id = state.get("user_id", "default")
    memories = await memu_retrieve(user_msg, user_id=user_id, limit=5)
    if not memories:
        return {"memory_context": ""}

    lines = ["## Remembered Context (from memU)"]
    for m in memories:
        content = m.get("content") or m.get("text") or m.get("summary", "")
        if content:
            lines.append(f"- {content[:200]}")

    return {"memory_context": "\n".join(lines)}


async def react_agent_node(state: AgentState) -> dict:
    """Run the ReAct agent. Background mode excludes ask_user and adds strict instructions."""
    skill_context = state.get("skill_context", "")
    memory_context = state.get("memory_context", "")
    mode = state.get("mode", "interactive")

    # In background mode: exclude ask_user tool, the agent must not ask questions
    if mode == "background":
        tools = [t for t in ALL_TOOLS if t.name != "ask_user"]
    else:
        tools = list(ALL_TOOLS)

    logged_tools = wrap_tools_with_logging(tools)

    # Fetch company context for this user
    user_id = state.get("user_id", "anonymous")
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

    result = await agent.ainvoke({"messages": state["messages"]})
    return {"messages": result["messages"]}


async def memory_saver(state: AgentState) -> dict:
    """Store the conversation turn in memU for future recall (non-blocking).
    Uses direct Python import of memU."""
    if not get_memu_service():
        return {}

    # Extract the latest user message and agent response
    user_msg = ""
    agent_msg = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, "type"):
            if msg.type == "ai" and msg.content and not agent_msg:
                agent_msg = msg.content
            elif msg.type == "human" and not user_msg:
                user_msg = msg.content
        if user_msg and agent_msg:
            break

    if user_msg and agent_msg:
        user_id = state.get("user_id", "default")
        asyncio.create_task(memu_memorize(
            f"User: {user_msg}\nAssistant: {agent_msg[:1000]}",
            {"source": "clarifi_chat", "user_id": user_id},
        ))

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
    """Get or create the compiled graph with conversation checkpointer.

    Uses Supabase PostgreSQL if configured, falls back to local SQLite.
    """
    global _compiled_graph, _checkpointer
    if _compiled_graph is None:
        db_url = settings.database_url
        if db_url.startswith("postgresql"):
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

                pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
                _checkpointer = AsyncPostgresSaver.from_conn_string(pg_url)
                await _checkpointer.setup()
                logger.info("Checkpointer: Supabase PostgreSQL")
            except Exception:
                logger.warning("PostgreSQL checkpointer failed, falling back to SQLite", exc_info=True)
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
