"""Test tool functions against seeded SQLite database."""

import asyncio
import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set env before any clarifi imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_tools.db"
os.environ["GOOGLE_API_KEY"] = "test-key"

from clarifi.models import Base


@pytest_asyncio.fixture(scope="module")
async def seeded_engine():
    """Create tables and seed test data."""
    engine = create_async_engine("sqlite+aiosqlite:///./test_tools.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed data
    from scripts.seed_db import seed

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if os.path.exists("./test_tools.db"):
        os.unlink("./test_tools.db")


@pytest_asyncio.fixture
async def patch_session(seeded_engine, monkeypatch):
    """Patch clarifi.db.session to use the test engine."""
    from clarifi.db import session as session_module

    factory = async_sessionmaker(seeded_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(session_module, "async_session_factory", factory)
    yield


@pytest.mark.asyncio
async def test_query_cashflow(patch_session):
    from clarifi.tools.finance import query_cashflow

    result = await query_cashflow.ainvoke({})
    assert "actual" in result, "Should have 'actual' category"
    assert "expected" in result, "Should have 'expected' category"
    assert "committed" in result, "Should have 'committed' category"
    assert "risk" in result, "Should have 'risk' category"
    assert result["actual"]["cash_in_bank"] > 0, "Should have positive cash from seed data"
    assert result["actual"]["monthly_burn_rate"] > 0
    assert result["actual"]["runway_days"] is not None


@pytest.mark.asyncio
async def test_query_receivables(patch_session):
    from clarifi.tools.finance import query_receivables

    result = await query_receivables.ainvoke({"status": "all"})
    assert result["count"] > 0, "Should have unpaid invoices from seed data"
    assert result["total_receivable"] > 0
    assert "buckets" in result


@pytest.mark.asyncio
async def test_query_receivables_overdue(patch_session):
    from clarifi.tools.finance import query_receivables

    result = await query_receivables.ainvoke({"status": "overdue"})
    assert result["count_overdue"] >= 3, "Seed data has 3 overdue invoices"


@pytest.mark.asyncio
async def test_query_profitability(patch_session):
    from clarifi.tools.finance import query_profitability

    result = await query_profitability.ainvoke({})
    assert "global" in result
    assert result["global"]["revenue"] > 0
    assert "by_project" in result
    assert len(result["by_project"]) >= 2, "Should have project-level data"


@pytest.mark.asyncio
async def test_query_profitability_single_project(patch_session):
    from clarifi.tools.finance import query_profitability

    result = await query_profitability.ainvoke({"project_code": "PRJ-001"})
    assert "project" in result
    assert result["project"] == "PRJ-001"
    assert result["revenue"] > 0


@pytest.mark.asyncio
async def test_query_profitability_unknown_project(patch_session):
    from clarifi.tools.finance import query_profitability

    result = await query_profitability.ainvoke({"project_code": "NONEXISTENT"})
    assert "error" in result


@pytest.mark.asyncio
async def test_query_contracts(patch_session):
    from clarifi.tools.contracts import query_contracts

    result = await query_contracts.ainvoke({"status": "active"})
    assert result["count"] >= 4, "Seed data has 4+ active contracts"


@pytest.mark.asyncio
async def test_query_milestones(patch_session):
    from clarifi.tools.contracts import query_milestones

    result = await query_milestones.ainvoke({"days_ahead": 90})
    # Milestone "Backend Dev" is due 2026-03-30; may or may not be overdue depending on test date
    assert result["count_overdue"] + result["count_upcoming"] >= 1, "Should have at least 1 milestone"


@pytest.mark.asyncio
async def test_query_alerts(patch_session):
    from clarifi.tools.alerts import query_alerts

    result = await query_alerts.ainvoke({})
    assert result["count"] > 0, "Should have alerts from seed data (overdue invoices)"
    assert result["critical"] >= 1, "Should have at least 1 critical alert"


@pytest.mark.asyncio
async def test_list_reminders(patch_session):
    from clarifi.tools.scheduling import list_reminders

    result = await list_reminders.ainvoke({})
    assert result["count"] >= 4, "Seed data has 4 default recurring tasks"


@pytest.mark.asyncio
async def test_check_freshness(patch_session):
    from clarifi.tools.feedback import check_freshness

    result = await check_freshness.ainvoke({})
    # Freshness check might return 0 if no unverified data is old enough
    assert "items" in result
    assert "count" in result
