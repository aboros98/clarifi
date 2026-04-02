"""Correlation tools: link Contract → Estimate → Invoice → Payment."""

from datetime import date
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import func, select

from clarifi.db.session import get_async_session
from clarifi.models.contract import Contract, ContractMilestone
from clarifi.models.estimate import Estimate
from clarifi.models.invoice import Invoice, InvoiceDirection, InvoiceStatus
from clarifi.models.project import Project


@tool
async def check_contract_status(contract_number: str) -> dict:
    """Check if a contract is fully invoiced and fully collected.
    Shows: contract value, total invoiced, total collected, gaps, delays.
    Args: contract_number — e.g. 'CTR-2025-001'."""
    from clarifi.agent.company_scope import get_user_company_ids

    today = date.today()
    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        q = select(Contract).where(
            Contract.contract_number == contract_number,
            Contract.is_deleted == False,  # noqa: E712
        )
        if company_ids:
            q = q.where(Contract.counterparty_id.in_(company_ids))
        contract = (await session.execute(q)).scalar_one_or_none()

        if not contract:
            return {"error": f"Contract '{contract_number}' not found"}

        # Total invoiced (issued invoices linked to this contract)
        inv_q = select(
            func.coalesce(func.sum(Invoice.total_amount), 0),
            func.coalesce(func.sum(Invoice.amount_paid), 0),
            func.count(Invoice.id),
        ).where(
            Invoice.contract_id == contract.id,
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.status != InvoiceStatus.CANCELLED,
            Invoice.is_deleted == False,
        )
        inv_result = (await session.execute(inv_q)).one()
        total_invoiced = Decimal(str(inv_result[0]))
        total_collected = Decimal(str(inv_result[1]))
        invoice_count = inv_result[2]

        # Overdue invoices
        overdue_q = select(Invoice).where(
            Invoice.contract_id == contract.id,
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.status.not_in([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
            Invoice.due_date < today,
            Invoice.is_deleted == False,
        )
        overdue_invoices = (await session.execute(overdue_q)).scalars().all()

        # Milestones
        milestones = (await session.execute(
            select(ContractMilestone).where(ContractMilestone.contract_id == contract.id)
        )).scalars().all()

        completed_ms = [m for m in milestones if m.completed]
        overdue_ms = [m for m in milestones if not m.completed and m.due_date < today]

        # Estimates linked
        estimates = (await session.execute(
            select(Estimate).where(
                Estimate.contract_id == contract.id,
                Estimate.is_deleted == False,
            )
        )).scalars().all()

        contract_value = contract.total_value
        not_invoiced = contract_value - total_invoiced
        not_collected = total_invoiced - total_collected

    return {
        "contract_number": contract_number,
        "title": contract.title,
        "contract_value": float(contract_value),
        "currency": contract.currency,
        "status": contract.status.value,
        "start_date": contract.start_date.isoformat(),
        "end_date": contract.end_date.isoformat() if contract.end_date else None,
        "invoicing": {
            "total_invoiced": float(total_invoiced),
            "total_collected": float(total_collected),
            "not_yet_invoiced": float(not_invoiced),
            "not_yet_collected": float(not_collected),
            "invoice_count": invoice_count,
            "pct_invoiced": float(total_invoiced / contract_value * 100) if contract_value > 0 else 0,
            "pct_collected": float(total_collected / contract_value * 100) if contract_value > 0 else 0,
        },
        "overdue_invoices": [
            {"number": i.invoice_number, "amount": float(i.amount_remaining), "days_overdue": (today - i.due_date).days}
            for i in overdue_invoices
        ],
        "milestones": {
            "total": len(milestones),
            "completed": len(completed_ms),
            "overdue": len(overdue_ms),
            "overdue_details": [{"title": m.title, "due": m.due_date.isoformat(), "days_overdue": (today - m.due_date).days} for m in overdue_ms],
        },
        "estimates_count": len(estimates),
    }


@tool
async def reconcile_project(project_code: str) -> dict:
    """Full reconciliation for a project: budget vs contract vs invoiced vs collected vs costs.
    Args: project_code — e.g. 'PRJ-001'."""

    from clarifi.agent.company_scope import get_user_company_ids
    from sqlalchemy import or_

    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        project = (await session.execute(
            select(Project).where(
                Project.project_code == project_code,
                Project.is_deleted == False,  # noqa: E712
            )
        )).scalar_one_or_none()

        if not project:
            return {"error": f"Project '{project_code}' not found"}

        # Revenue invoiced (scoped to user's companies)
        inv_scope = []
        if company_ids:
            inv_scope = [or_(
                Invoice.issuer_company_id.in_(company_ids),
                Invoice.recipient_company_id.in_(company_ids),
            )]

        rev_q = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            Invoice.project_id == project.id,
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.status != InvoiceStatus.CANCELLED,
            Invoice.is_deleted == False,  # noqa: E712
            *inv_scope,
        )
        revenue = Decimal(str((await session.execute(rev_q)).scalar_one()))

        # Revenue collected
        collected_q = select(func.coalesce(func.sum(Invoice.amount_paid), 0)).where(
            Invoice.project_id == project.id,
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.status != InvoiceStatus.CANCELLED,
            Invoice.is_deleted == False,
        )
        collected = Decimal(str((await session.execute(collected_q)).scalar_one()))

        # Costs (received invoices)
        cost_q = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            Invoice.project_id == project.id,
            Invoice.direction == InvoiceDirection.RECEIVED,
            Invoice.status != InvoiceStatus.CANCELLED,
            Invoice.is_deleted == False,
        )
        costs = Decimal(str((await session.execute(cost_q)).scalar_one()))

        # Contract value
        contract_q = select(func.coalesce(func.sum(Contract.total_value), 0)).where(
            Contract.project_id == project.id,
            Contract.is_deleted == False,
        )
        contract_value = Decimal(str((await session.execute(contract_q)).scalar_one()))

        budget = project.budget or Decimal("0")
        profit = revenue - costs
        margin = float(profit / revenue * 100) if revenue > 0 else 0.0

    return {
        "project_code": project_code,
        "name": project.name,
        "status": project.status.value,
        "budget": float(budget),
        "contract_value": float(contract_value),
        "revenue_invoiced": float(revenue),
        "revenue_collected": float(collected),
        "outstanding": float(revenue - collected),
        "costs": float(costs),
        "profit": float(profit),
        "margin_pct": margin,
        "budget_used_pct": float(costs / budget * 100) if budget > 0 else None,
        "invoiced_vs_contract_pct": float(revenue / contract_value * 100) if contract_value > 0 else None,
        "gaps": {
            "not_invoiced": float(contract_value - revenue) if contract_value > revenue else 0,
            "not_collected": float(revenue - collected),
            "over_budget": float(costs - budget) if costs > budget else 0,
        },
    }
