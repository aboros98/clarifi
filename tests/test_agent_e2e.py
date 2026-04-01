"""End-to-end agent tests — requires GOOGLE_API_KEY in .env.

These tests call the actual Gemini API (gemini-2.5-flash-lite).
Run: pytest tests/test_agent_e2e.py -v -s
"""

import os
import sys

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Must set env before imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_e2e.db")

from clarifi.config import settings

# Skip all tests if no real API key
_has_key = (
    settings.google_api_key
    and settings.google_api_key not in ("", "your-google-api-key-here", "test-key")
    and len(settings.google_api_key) > 20
)
pytestmark = pytest.mark.skipif(
    not _has_key,
    reason="GOOGLE_API_KEY not set in .env — skipping e2e tests",
)

from langchain_core.messages import HumanMessage

from clarifi.agent.graph import get_graph, _compiled_graph
from clarifi.models import Base
import clarifi.agent.graph as graph_module


@pytest_asyncio.fixture(scope="module")
async def seeded_db():
    """Create tables and seed test data for e2e tests."""
    engine = create_async_engine("sqlite+aiosqlite:///./test_e2e.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from scripts.seed_db import seed
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session)

    # Patch the session factory so tools use our test DB
    from clarifi.db import session as session_module
    session_module.async_session_factory = factory

    yield engine

    # Reset graph singleton for next test run
    graph_module._compiled_graph = None

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if os.path.exists("./test_e2e.db"):
        os.unlink("./test_e2e.db")


@pytest_asyncio.fixture
async def graph(seeded_db):
    """Get the compiled agent graph."""
    # Reset singleton to get fresh graph
    graph_module._compiled_graph = None
    return await get_graph()


@pytest.mark.asyncio
async def test_cashflow_question(graph):
    """Test: 'Câți bani am?' should return a response with cash amount."""
    result = await graph.ainvoke({
        "messages": [HumanMessage(content="Câți bani am azi?")]
    })
    messages = result.get("messages", [])
    assert len(messages) > 1, "Should have at least user message + AI response"

    # Find last AI message
    ai_msg = None
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            ai_msg = msg.content
            break

    assert ai_msg, "Agent should produce a response"
    print(f"\n--- Cashflow Response ---\n{ai_msg}\n")

    # Response should mention money/lei/RON or a number
    ai_lower = ai_msg.lower()
    assert any(w in ai_lower for w in ["lei", "ron", "disponibil", "cash", "cont"]), \
        f"Response should mention money. Got: {ai_msg[:200]}"


@pytest.mark.asyncio
async def test_receivables_question(graph):
    """Test: 'Cine îmi datorează bani?' should list debtors."""
    result = await graph.ainvoke({
        "messages": [HumanMessage(content="Cine îmi datorează bani?")]
    })
    messages = result.get("messages", [])
    ai_msg = None
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            ai_msg = msg.content
            break

    assert ai_msg, "Agent should produce a response"
    print(f"\n--- Receivables Response ---\n{ai_msg}\n")


@pytest.mark.asyncio
async def test_alerts_question(graph):
    """Test: 'Ce alerte am?' should list active alerts."""
    result = await graph.ainvoke({
        "messages": [HumanMessage(content="Ce alerte am?")]
    })
    messages = result.get("messages", [])
    ai_msg = None
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            ai_msg = msg.content
            break

    assert ai_msg, "Agent should produce a response"
    print(f"\n--- Alerts Response ---\n{ai_msg}\n")


@pytest.mark.asyncio
async def test_weekly_plan(graph):
    """Test: 'Ce trebuie să fac săptămâna asta?' should produce an action plan."""
    result = await graph.ainvoke({
        "messages": [HumanMessage(content="Ce trebuie să fac săptămâna asta?")]
    })
    messages = result.get("messages", [])
    ai_msg = None
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            ai_msg = msg.content
            break

    assert ai_msg, "Agent should produce a response"
    print(f"\n--- Weekly Plan Response ---\n{ai_msg}\n")


@pytest.mark.asyncio
async def test_profitability_question(graph):
    """Test: 'Ce proiecte sunt pe pierdere?' should analyze project margins."""
    result = await graph.ainvoke({
        "messages": [HumanMessage(content="Ce proiecte sunt pe pierdere?")]
    })
    messages = result.get("messages", [])
    ai_msg = None
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            ai_msg = msg.content
            break

    assert ai_msg, "Agent should produce a response"
    print(f"\n--- Profitability Response ---\n{ai_msg}\n")
