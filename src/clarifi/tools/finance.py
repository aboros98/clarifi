"""Financial tools: cashflow, receivables, profitability."""

from datetime import date, timedelta
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import func, or_, select

from clarifi.agent.company_scope import get_user_company_ids
from clarifi.db.session import get_async_session
from clarifi.models.bank_transaction import BankTransaction, TransactionType
from clarifi.models.invoice import Invoice, InvoiceDirection, InvoiceStatus
from clarifi.models.project import Project, ProjectStatus


def _invoice_belongs_to(company_ids: list[str]):
    """Filter: invoice where our company is issuer OR recipient."""
    return or_(
        Invoice.issuer_company_id.in_(company_ids),
        Invoice.recipient_company_id.in_(company_ids),
    )


@tool
async def query_cashflow() -> dict:
    """Get financial position split into ACTUAL (bank data), EXPECTED (unpaid invoices),
    COMMITTED (contract value not yet invoiced), and RISK indicators.
    This is the primary financial overview tool."""
    today = date.today()
    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        # ACTUAL: latest bank balance (real money)
        bal_q = (
            select(BankTransaction.balance_after, BankTransaction.transaction_date)
            .where(BankTransaction.balance_after.isnot(None), BankTransaction.is_deleted == False)
            .order_by(BankTransaction.transaction_date.desc())
            .limit(1)
        )
        bal_row = (await session.execute(bal_q)).first()
        cash = Decimal(str(bal_row[0])) if bal_row else Decimal("0")
        last_bank_date = bal_row[1].isoformat() if bal_row else None
        bank_data_age_days = (today - bal_row[1]).days if bal_row else None

        # ACTUAL: burn rate (real bank debits over last 90 days)
        burn_q = select(func.coalesce(func.sum(BankTransaction.amount), 0)).where(
            BankTransaction.transaction_type == TransactionType.DEBIT,
            BankTransaction.transaction_date >= today - timedelta(days=90),
            BankTransaction.is_deleted == False,
        )
        burn_total = Decimal(str((await session.execute(burn_q)).scalar_one()))
        burn_rate = burn_total / 3 if burn_total > 0 else Decimal("0")

        # EXPECTED: unpaid invoices (projected, not yet in bank)
        inv_scope = _invoice_belongs_to(company_ids) if company_ids else True

        async def _sum_invoices(direction, days):
            cutoff = today + timedelta(days=days)
            q = select(func.coalesce(func.sum(Invoice.amount_remaining), 0)).where(
                inv_scope,
                Invoice.direction == direction,
                Invoice.status.not_in([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
                Invoice.due_date <= cutoff,
                Invoice.is_deleted == False,
            )
            return Decimal(str((await session.execute(q)).scalar_one()))

        inflows_30 = await _sum_invoices(InvoiceDirection.ISSUED, 30)
        inflows_90 = await _sum_invoices(InvoiceDirection.ISSUED, 90)
        outflows_30 = await _sum_invoices(InvoiceDirection.RECEIVED, 30)
        outflows_90 = await _sum_invoices(InvoiceDirection.RECEIVED, 90)

        # EXPECTED: overdue receivables (subset — already past due)
        overdue_q = select(func.coalesce(func.sum(Invoice.amount_remaining), 0)).where(
            inv_scope,
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.status.not_in([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
            Invoice.due_date < today,
            Invoice.is_deleted == False,
        )
        overdue = Decimal(str((await session.execute(overdue_q)).scalar_one()))

        # COMMITTED: contract value not yet invoiced
        from clarifi.models.contract import Contract, ContractMilestone, ContractStatus
        contract_total_q = select(func.coalesce(func.sum(Contract.total_value), 0)).where(
            Contract.status == ContractStatus.ACTIVE, Contract.is_deleted == False,
        )
        contract_total = Decimal(str((await session.execute(contract_total_q)).scalar_one()))

        invoiced_total_q = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            inv_scope,
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.contract_id.isnot(None),
            Invoice.status != InvoiceStatus.CANCELLED,
            Invoice.is_deleted == False,
        )
        invoiced_total = Decimal(str((await session.execute(invoiced_total_q)).scalar_one()))
        not_yet_invoiced = max(Decimal("0"), contract_total - invoiced_total)

        # COMMITTED: milestones due within 30 days
        ms_q = select(func.coalesce(func.sum(ContractMilestone.amount), 0)).where(
            ContractMilestone.completed == False,
            ContractMilestone.amount.isnot(None),
            ContractMilestone.due_date >= today,
            ContractMilestone.due_date <= today + timedelta(days=30),
        )
        upcoming_ms_amount = Decimal(str((await session.execute(ms_q)).scalar_one()))

    runway = int(cash / (burn_rate / 30)) if burn_rate > 0 else None

    return {
        "actual": {
            "cash_in_bank": float(cash),
            "last_bank_date": last_bank_date,
            "bank_data_age_days": bank_data_age_days,
            "monthly_burn_rate": float(burn_rate),
            "runway_days": runway,
        },
        "expected": {
            "inflows_30d": float(inflows_30),
            "outflows_30d": float(outflows_30),
            "net_30d": float(cash + inflows_30 - outflows_30),
            "inflows_90d": float(inflows_90),
            "outflows_90d": float(outflows_90),
            "net_90d": float(cash + inflows_90 - outflows_90),
        },
        "committed": {
            "contract_value_not_invoiced": float(not_yet_invoiced),
            "upcoming_milestones_30d": float(upcoming_ms_amount),
        },
        "risk": {
            "overdue_receivables": float(overdue),
            "data_freshness": (
                f"Datele bancare au {bank_data_age_days} zile" if bank_data_age_days
                else "Nicio tranzacție bancară încărcată"
            ),
        },
        "as_of": today.isoformat(),
    }


@tool
async def query_receivables(status: str = "all") -> dict:
    """Get unpaid invoices we issued (money owed to us), with aging breakdown.
    Args: status — 'all', 'overdue', or 'current'.
    Returns: total_receivable, invoices grouped by aging bucket."""
    today = date.today()
    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        filters = [
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.status.not_in([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
            Invoice.is_deleted == False,  # noqa: E712
        ]
        if company_ids:
            filters.append(_invoice_belongs_to(company_ids))

        q = (
            select(Invoice)
            .where(*filters)
            .order_by(Invoice.due_date)
            .limit(200)
        )
        invoices = (await session.execute(q)).scalars().all()

    buckets = {"current": [], "overdue_1_30": [], "overdue_31_60": [], "overdue_60_plus": []}
    total = Decimal("0")

    for inv in invoices:
        days_overdue = max(0, (today - inv.due_date).days)
        entry = {
            "invoice_number": inv.invoice_number,
            "amount_remaining": float(inv.amount_remaining),
            "due_date": inv.due_date.isoformat(),
            "days_overdue": days_overdue,
            "currency": inv.currency,
        }
        total += inv.amount_remaining

        if days_overdue == 0:
            buckets["current"].append(entry)
        elif days_overdue <= 30:
            buckets["overdue_1_30"].append(entry)
        elif days_overdue <= 60:
            buckets["overdue_31_60"].append(entry)
        else:
            buckets["overdue_60_plus"].append(entry)

    if status == "overdue":
        buckets.pop("current", None)
    elif status == "current":
        buckets = {"current": buckets["current"]}

    return {
        "total_receivable": float(total),
        "count": len(invoices),
        "count_overdue": len(invoices) - len(buckets.get("current", [])),
        "buckets": buckets,
    }


@tool
async def query_profitability(project_code: str | None = None) -> dict:
    """Get profit margins. If project_code given, returns for that project. Otherwise returns global + all projects.
    Returns: revenue, costs, profit, margin_pct, and per-project breakdown."""
    async with get_async_session() as session:
        base_rev = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.status.not_in([InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT]),
            Invoice.is_deleted == False,
        )
        base_cost = select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            Invoice.direction == InvoiceDirection.RECEIVED,
            Invoice.status != InvoiceStatus.CANCELLED,
            Invoice.is_deleted == False,
        )

        if project_code:
            proj = (await session.execute(
                select(Project).where(Project.project_code == project_code)
            )).scalar_one_or_none()
            if not proj:
                return {"error": f"Project '{project_code}' not found"}
            rev = Decimal(str((await session.execute(base_rev.where(Invoice.project_id == proj.id))).scalar_one()))
            cost = Decimal(str((await session.execute(base_cost.where(Invoice.project_id == proj.id))).scalar_one()))
            profit = rev - cost
            margin = float(profit / rev * 100) if rev > 0 else 0.0
            return {
                "project": project_code,
                "name": proj.name,
                "revenue": float(rev),
                "costs": float(cost),
                "profit": float(profit),
                "margin_pct": margin,
                "budget": float(proj.budget) if proj.budget else None,
                "budget_used_pct": float(cost / proj.budget * 100) if proj.budget and proj.budget > 0 else None,
            }

        # Global
        total_rev = Decimal(str((await session.execute(base_rev)).scalar_one()))
        total_cost = Decimal(str((await session.execute(base_cost)).scalar_one()))
        profit = total_rev - total_cost
        margin = float(profit / total_rev * 100) if total_rev > 0 else 0.0

        # Per-project (grouped queries)
        proj_rev_q = (
            select(Invoice.project_id, func.coalesce(func.sum(Invoice.total_amount), 0))
            .where(Invoice.direction == InvoiceDirection.ISSUED, Invoice.status.not_in([InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT]), Invoice.is_deleted == False, Invoice.project_id.isnot(None))
            .group_by(Invoice.project_id)
        )
        proj_cost_q = (
            select(Invoice.project_id, func.coalesce(func.sum(Invoice.total_amount), 0))
            .where(Invoice.direction == InvoiceDirection.RECEIVED, Invoice.status != InvoiceStatus.CANCELLED, Invoice.is_deleted == False, Invoice.project_id.isnot(None))
            .group_by(Invoice.project_id)
        )
        rev_map = dict((await session.execute(proj_rev_q)).all())
        cost_map = dict((await session.execute(proj_cost_q)).all())

        projects = (await session.execute(
            select(Project).where(Project.status.in_([ProjectStatus.ACTIVE, ProjectStatus.COMPLETED]), Project.is_deleted == False)
        )).scalars().all()

        by_project = []
        for p in projects:
            r = Decimal(str(rev_map.get(p.id, 0)))
            c = Decimal(str(cost_map.get(p.id, 0)))
            pr = r - c
            m = float(pr / r * 100) if r > 0 else 0.0
            by_project.append({
                "project_code": p.project_code, "name": p.name,
                "revenue": float(r), "costs": float(c), "profit": float(pr), "margin_pct": m,
                "budget": float(p.budget) if p.budget else None,
            })
        by_project.sort(key=lambda x: x["margin_pct"])

    return {
        "global": {"revenue": float(total_rev), "costs": float(total_cost), "profit": float(profit), "margin_pct": margin},
        "by_project": by_project,
    }
