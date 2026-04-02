"""Contract and milestone tools."""

from datetime import date, timedelta

from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.agent.company_scope import get_user_company_ids
from clarifi.db.session import get_async_session
from clarifi.models.contract import Contract, ContractMilestone, ContractStatus


@tool
async def query_contracts(status: str = "active") -> dict:
    """Get contracts filtered by status. Returns contract details including value, dates, and counterparty.
    Args: status — 'active', 'all', 'expiring'."""
    today = date.today()
    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        q = select(Contract).where(Contract.is_deleted == False)
        if company_ids:
            q = q.where(Contract.counterparty_id.in_(company_ids))
        if status == "active":
            q = q.where(Contract.status == ContractStatus.ACTIVE)
        elif status == "expiring":
            q = q.where(
                Contract.status == ContractStatus.ACTIVE,
                Contract.end_date.isnot(None),
                Contract.end_date <= today + timedelta(days=30),
                Contract.end_date >= today,
            )
        contracts = (await session.execute(q)).scalars().all()

    return {
        "count": len(contracts),
        "contracts": [
            {
                "contract_number": c.contract_number,
                "title": c.title,
                "total_value": float(c.total_value),
                "currency": c.currency,
                "start_date": c.start_date.isoformat(),
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "status": c.status.value,
                "days_until_expiry": (c.end_date - today).days if c.end_date else None,
                "payment_terms_days": c.payment_terms_days,
            }
            for c in contracts
        ],
    }


@tool
async def query_milestones(days_ahead: int = 30) -> dict:
    """Get upcoming and overdue milestones.
    Args: days_ahead — how many days to look ahead (default 30).
    Returns: upcoming and overdue milestones with details."""
    today = date.today()
    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        # Scope milestones to contracts belonging to user's companies
        contract_scope = select(Contract.id).where(Contract.is_deleted == False)
        if company_ids:
            contract_scope = contract_scope.where(Contract.counterparty_id.in_(company_ids))

        upcoming_q = select(ContractMilestone).where(
            ContractMilestone.completed == False,
            ContractMilestone.due_date >= today,
            ContractMilestone.due_date <= today + timedelta(days=days_ahead),
            ContractMilestone.contract_id.in_(contract_scope),
        )
        overdue_q = select(ContractMilestone).where(
            ContractMilestone.completed == False,
            ContractMilestone.due_date < today,
            ContractMilestone.contract_id.in_(contract_scope),
        )
        upcoming = (await session.execute(upcoming_q)).scalars().all()
        overdue = (await session.execute(overdue_q)).scalars().all()

    def _fmt(ms):
        return {
            "title": ms.title,
            "due_date": ms.due_date.isoformat(),
            "amount": float(ms.amount) if ms.amount else None,
            "days_overdue": max(0, (today - ms.due_date).days),
        }

    return {
        "upcoming": [_fmt(m) for m in upcoming],
        "overdue": [_fmt(m) for m in overdue],
        "count_upcoming": len(upcoming),
        "count_overdue": len(overdue),
    }
