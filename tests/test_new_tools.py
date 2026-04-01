"""Tests for new tools: query_invoices, query_transactions, mark_invoice_paid,
new cashflow structure, onboarding, and save_extracted_data for contracts + bank statements."""

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_new_tools.db"
os.environ["GOOGLE_API_KEY"] = "test-key"

from clarifi.models import Base


@pytest_asyncio.fixture(scope="module")
async def seeded_engine():
    engine = create_async_engine("sqlite+aiosqlite:///./test_new_tools.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from scripts.seed_db import seed
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if os.path.exists("./test_new_tools.db"):
        os.unlink("./test_new_tools.db")


@pytest_asyncio.fixture
async def patch_session(seeded_engine, monkeypatch):
    from clarifi.db import session as session_module
    factory = async_sessionmaker(seeded_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(session_module, "async_session_factory", factory)
    yield


# --- query_invoices ---

@pytest.mark.asyncio
async def test_query_invoices_all(patch_session):
    from clarifi.tools.data_queries import query_invoices
    result = await query_invoices.ainvoke({"direction": "all", "status": "all"})
    assert result["count"] > 0, "Should have invoices from seed"
    assert "invoices" in result


@pytest.mark.asyncio
async def test_query_invoices_issued(patch_session):
    from clarifi.tools.data_queries import query_invoices
    result = await query_invoices.ainvoke({"direction": "issued", "status": "all"})
    assert result["count"] >= 9, "Seed has 9 issued invoices"
    for inv in result["invoices"]:
        assert inv["direction"] == "issued"


@pytest.mark.asyncio
async def test_query_invoices_unpaid(patch_session):
    from clarifi.tools.data_queries import query_invoices
    result = await query_invoices.ainvoke({"direction": "all", "status": "unpaid"})
    for inv in result["invoices"]:
        assert inv["status"] not in ("paid", "cancelled")


@pytest.mark.asyncio
async def test_query_invoices_overdue(patch_session):
    from clarifi.tools.data_queries import query_invoices
    result = await query_invoices.ainvoke({"direction": "issued", "status": "overdue"})
    assert result["count"] >= 2, "Seed has at least 2 overdue issued invoices"


# --- query_transactions ---

@pytest.mark.asyncio
async def test_query_transactions(patch_session):
    from clarifi.tools.data_queries import query_transactions
    result = await query_transactions.ainvoke({"days": 365})
    assert result["count"] > 0, "Should have bank transactions from seed"
    txn = result["transactions"][0]
    assert "date" in txn
    assert "amount" in txn
    assert "is_matched" in txn


# --- mark_invoice_paid ---

@pytest.mark.asyncio
async def test_mark_invoice_paid(patch_session):
    from clarifi.tools.data_queries import query_invoices, mark_invoice_paid

    # Find an unpaid invoice
    unpaid = await query_invoices.ainvoke({"direction": "issued", "status": "unpaid"})
    assert unpaid["count"] > 0
    inv = unpaid["invoices"][0]

    result = await mark_invoice_paid.ainvoke({"invoice_id": inv["id"]})
    assert result["status"] == "updated"
    assert result["new_status"] == "paid"
    assert result["remaining"] == 0


@pytest.mark.asyncio
async def test_mark_invoice_paid_partial(patch_session):
    from clarifi.tools.data_queries import query_invoices, mark_invoice_paid

    unpaid = await query_invoices.ainvoke({"direction": "issued", "status": "unpaid"})
    if unpaid["count"] == 0:
        pytest.skip("No unpaid invoices left")
    inv = unpaid["invoices"][0]

    result = await mark_invoice_paid.ainvoke({"invoice_id": inv["id"], "amount_paid": 1000.0})
    assert result["status"] == "updated"
    assert result["new_status"] == "partially_paid"
    assert result["remaining"] > 0


@pytest.mark.asyncio
async def test_mark_invoice_paid_not_found(patch_session):
    from clarifi.tools.data_queries import mark_invoice_paid
    result = await mark_invoice_paid.ainvoke({"invoice_id": "nonexistent"})
    assert "error" in result


# --- new cashflow structure ---

@pytest.mark.asyncio
async def test_cashflow_actual_expected_committed(patch_session):
    from clarifi.tools.finance import query_cashflow
    result = await query_cashflow.ainvoke({})

    # Structure
    assert "actual" in result
    assert "expected" in result
    assert "committed" in result
    assert "risk" in result

    # Actual fields
    assert "cash_in_bank" in result["actual"]
    assert "monthly_burn_rate" in result["actual"]
    assert "runway_days" in result["actual"]
    assert "last_bank_date" in result["actual"]
    assert "bank_data_age_days" in result["actual"]

    # Expected fields
    assert "inflows_30d" in result["expected"]
    assert "outflows_30d" in result["expected"]
    assert "net_30d" in result["expected"]

    # Committed fields
    assert "contract_value_not_invoiced" in result["committed"]
    assert "upcoming_milestones_30d" in result["committed"]

    # Risk fields
    assert "overdue_receivables" in result["risk"]
    assert "data_freshness" in result["risk"]

    # Values from seed data
    assert result["actual"]["cash_in_bank"] > 0
    assert result["actual"]["monthly_burn_rate"] > 0


# --- save_extracted_data for contract ---

@pytest.mark.asyncio
async def test_save_contract(patch_session):
    from clarifi.tools.documents import save_extracted_data

    result = await save_extracted_data.ainvoke({
        "entity_type": "contract",
        "data": {
            "contract_number": "CTR-TEST-001",
            "client_name": "Test Client SRL",
            "client_tax_id": "RO99999999",
            "total_value": 50000,
            "currency": "RON",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "milestones": [
                {"name": "Phase 1", "due_date": "2026-06-01", "amount": 25000},
                {"name": "Phase 2", "due_date": "2026-12-01", "amount": 25000},
            ],
            "obligations": ["Deliver monthly reports"],
            "penalties": ["Late delivery: 0.1% per day"],
        },
        "confirmed": True,
    })
    assert result["status"] == "saved"
    assert result["entity_type"] == "contract"
    assert result["milestones_saved"] == 2
    assert "id" in result


# --- save_extracted_data for bank_statement ---

@pytest.mark.asyncio
async def test_save_bank_statement(patch_session):
    from clarifi.tools.documents import save_extracted_data

    result = await save_extracted_data.ainvoke({
        "entity_type": "bank_statement",
        "data": {
            "account_iban": "RO49AAAA1B31007593840000",
            "currency": "RON",
            "opening_balance": 50000,
            "closing_balance": 45000,
            "transactions": [
                {"date": "2026-04-01", "amount": -3000, "description": "Chirie", "counterparty": "Office SRL"},
                {"date": "2026-04-02", "amount": -2000, "description": "Hosting", "counterparty": "Cloud SRL"},
                {"date": "2026-04-05", "amount": 10000, "description": "Plata factura", "reference": "INV-001", "counterparty": "Client SRL"},
            ],
        },
        "confirmed": True,
    })
    assert result["status"] == "saved"
    assert result["entity_type"] == "bank_statement"
    assert result["transactions_saved"] == 3


# --- save_extracted_data for invoice ---

@pytest.mark.asyncio
async def test_save_invoice_with_auto_company(patch_session):
    from clarifi.tools.documents import save_extracted_data

    result = await save_extracted_data.ainvoke({
        "entity_type": "invoice",
        "data": {
            "invoice_number": "INV-NEW-001",
            "vendor_or_client_name": "New Vendor SRL",
            "vendor_or_client_tax_id": "RO11111111",
            "issue_date": "2026-04-01",
            "due_date": "2026-05-01",
            "total_amount": 5000,
            "vat_amount": 950,
            "is_incoming": True,
        },
        "confirmed": True,
    })
    assert result["status"] == "saved"
    assert result["entity_type"] == "invoice"

    # Verify the company was auto-created
    from clarifi.db.session import get_async_session
    from clarifi.models.company import Company
    from sqlalchemy import select
    async with get_async_session() as session:
        co = (await session.execute(
            select(Company).where(Company.tax_id == "RO11111111")
        )).scalar_one_or_none()
        assert co is not None, "Company should be auto-created from extraction"
        assert co.legal_name == "New Vendor SRL"


# --- onboarding ---

@pytest.mark.asyncio
async def test_onboarding_get_company_context(patch_session):
    """Test that get_company_context returns empty for unknown user."""
    from clarifi.api.onboarding import get_company_context
    ctx = await get_company_context("nonexistent-user-id")
    assert ctx == ""
