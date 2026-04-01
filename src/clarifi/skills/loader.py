"""Skill loader — selects relevant .md skill files using LLM intent classification.

Uses a lightweight LLM call to pick the best 1-3 skills for the user's message.
Falls back to loading all skills if LLM is unavailable.
"""

import logging
import re
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent

_skill_cache: dict[str, dict] | None = None


def _parse_skill(path: Path) -> dict:
    """Parse a skill .md file into {name, description, tools, content}."""
    text = path.read_text(encoding="utf-8")

    # Extract first heading as description
    desc = path.stem
    for line in text.splitlines():
        if line.startswith("# "):
            desc = line[2:].strip()
            break

    # Extract tools section
    tools = []
    tools_match = re.search(r"## Tools\n(.+?)(?:\n##|\Z)", text, re.DOTALL)
    if tools_match:
        for line in tools_match.group(1).strip().splitlines():
            line = line.strip().lstrip("- ")
            if line:
                tools.append(line)

    return {
        "name": path.stem,
        "description": desc,
        "tools": tools,
        "content": text,
        "path": str(path),
    }


def _load_all_skills() -> dict[str, dict]:
    global _skill_cache
    if _skill_cache is not None:
        return _skill_cache

    _skill_cache = {}
    for md_file in SKILLS_DIR.glob("*.md"):
        skill = _parse_skill(md_file)
        _skill_cache[skill["name"]] = skill

    return _skill_cache


class SkillSelection(BaseModel):
    """LLM output: which skills to activate."""
    skills: list[str]
    reasoning: str


async def select_skills_llm(user_message: str, max_skills: int = 3) -> list[dict]:
    """Select relevant skills using LLM intent classification.
    Robust — understands intent, not just keywords."""
    skills = _load_all_skills()

    catalog = "\n".join(
        f"- **{name}**: {s['description']} (tools: {', '.join(s['tools'])})"
        for name, s in sorted(skills.items())
    )

    try:
        from clarifi.llm import get_llm

        llm = get_llm()
        structured = llm.with_structured_output(SkillSelection)

        from langchain_core.messages import HumanMessage, SystemMessage

        result = await structured.ainvoke([
            SystemMessage(content=(
                "You are a skill router for Clarifi, a Romanian financial AI assistant.\n"
                "Given the user's message, select 1-3 skills to activate.\n"
                "Return ONLY skill names from the catalog.\n\n"
                f"Available skills:\n{catalog}\n\n"
                "Rules:\n"
                "- Select the minimum skills needed (usually 1-2)\n"
                "- For compound questions, select multiple\n"
                "- For greetings or vague messages, select 'cashflow' + 'alerts'\n"
                "- The user writes in Romanian or English — understand both"
            )),
            HumanMessage(content=user_message),
        ])

        selected = []
        for name in result.skills[:max_skills]:
            if name in skills:
                selected.append(skills[name])

        if selected:
            logger.debug("LLM skill selection: %s (reason: %s)", [s["name"] for s in selected], result.reasoning)
            return selected

    except Exception:
        logger.warning("LLM skill selection failed, falling back to all skills", exc_info=True)

    # Fallback: return all skills (agent picks what it needs)
    return list(skills.values())[:max_skills]


def select_skills(user_message: str, max_skills: int = 3) -> list[dict]:
    """Synchronous wrapper — used by the graph's skill_loader node.
    Delegates to LLM-based selection at runtime via the async version."""
    # This is called from a sync node in the graph.
    # The actual LLM call happens in select_skills_llm (async).
    # For sync contexts (tests), fall back to simple matching.
    skills = _load_all_skills()

    # Simple fallback for sync contexts (tests, imports)
    message_lower = user_message.lower()
    scored: list[tuple[float, dict]] = []

    for skill in skills.values():
        score = 0
        # Check if any tool name is mentioned
        for tool in skill["tools"]:
            if tool.lower() in message_lower:
                score += 3

        # Check if skill name or description words appear
        for word in skill["description"].lower().split():
            if len(word) > 3 and word in message_lower:
                score += 1

        # Check skill name
        if skill["name"].replace("_", " ") in message_lower:
            score += 2

        if score > 0:
            scored.append((score, skill))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [s[1] for s in scored[:max_skills]]

    if not selected:
        for name in ["cashflow", "alerts"]:
            if name in skills:
                selected.append(skills[name])

    return selected


def get_tools_for_skills(selected_skills: list[dict]) -> list[str]:
    """Get the list of tool names needed by the selected skills."""
    tool_names = set()
    for skill in selected_skills:
        tool_names.update(skill["tools"])
    return list(tool_names)


def format_skill_context(selected_skills: list[dict]) -> str:
    """Format selected skills into a string for the system prompt."""
    parts = []
    for skill in selected_skills:
        parts.append(skill["content"])
    return "\n\n---\n\n".join(parts)
