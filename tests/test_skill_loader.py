"""Test the skill loader — skill parsing, tool binding, and context formatting.
Note: LLM-based selection (select_skills_llm) requires API key — tested in e2e.
These tests verify the sync fallback (select_skills) and infrastructure."""

from clarifi.skills.loader import (
    _load_all_skills,
    format_skill_context,
    get_tools_for_skills,
    select_skills,
)


def test_all_skills_load():
    """All .md skill files should parse without errors."""
    skills = _load_all_skills()
    assert len(skills) >= 8, f"Expected at least 8 skills, got {len(skills)}"

    for name, skill in skills.items():
        assert skill["content"], f"Skill '{name}' has no content"
        assert skill["tools"], f"Skill '{name}' has no tools defined"
        assert skill["description"], f"Skill '{name}' has no description"


def test_each_skill_has_tools():
    """Every skill must declare at least one tool."""
    skills = _load_all_skills()
    for name, skill in skills.items():
        assert len(skill["tools"]) >= 1, f"Skill '{name}' has no tools"


def test_tools_exist_in_all_tools():
    """Every tool referenced in a skill must exist in ALL_TOOLS."""
    from clarifi.tools import ALL_TOOLS
    tool_names = {t.name for t in ALL_TOOLS}
    skills = _load_all_skills()

    for name, skill in skills.items():
        for tool in skill["tools"]:
            assert tool in tool_names, f"Skill '{name}' references unknown tool '{tool}'"


def test_select_skills_returns_results():
    """select_skills should always return at least one skill."""
    result = select_skills("random unknown text xyz")
    assert len(result) > 0, "Should return fallback skills"


def test_select_skills_cashflow():
    """Cashflow-related queries should include cashflow skill."""
    result = select_skills("cashflow analysis")
    names = [s["name"] for s in result]
    assert "cashflow" in names


def test_select_skills_receivables():
    """Receivables queries should match."""
    result = select_skills("receivables aging")
    names = [s["name"] for s in result]
    assert "receivables" in names


def test_max_skills_limit():
    """Should not return more than max_skills."""
    result = select_skills("everything about cashflow receivables contracts alerts risk", max_skills=2)
    assert len(result) <= 2


def test_tools_for_skills():
    """Selected skills should declare their tools."""
    skills = _load_all_skills()
    cashflow = skills.get("cashflow")
    assert cashflow is not None
    tools = get_tools_for_skills([cashflow])
    assert "query_cashflow" in tools


def test_format_skill_context():
    """Skill context should be a non-empty string with skill content."""
    skills = _load_all_skills()
    cashflow = skills.get("cashflow")
    context = format_skill_context([cashflow])
    assert len(context) > 100
    assert "## Tools" in context
