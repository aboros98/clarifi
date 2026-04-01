"""Advanced analysis tools: unissued invoices, cashflow projection, client risk scoring."""

from datetime import date, timedelta
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import func, select

from clarifi.db.session import get_async_session
from clarifi.models.bank_transaction import BankTransaction
from clarifi.models.company import Company
from clarifi.models.contract import Contract, ContractMilestone, ContractStatus
from clarifi.models.invoice import Invoice, InvoiceDirection, InvoiceStatus


@tool
async def detect_unissued_invoices() -> dict:
    """Detect invoices that should have been issued but weren't.
    Checks completed milestones without matching invoices and recurring billing gaps.
    Returns list of missing invoices with contract details."""
    today = date.today()

    async with get_async_session() as session:
        # Find completed milestones with amounts but no matching invoice
        milestones = (await session.execute(
            select(ContractMilestone).where(
                ContractMilestone.completed == True,
                ContractMilestone.amount.isnot(None),
                ContractMilestone.amount > 0,
            )
        )).scalars().all()

        missing = []
        for ms in milestones:
            # Check if an invoice exists for this contract with a similar amount
            # issued around the milestone completion date
            inv_q = select(func.count(Invoice.id)).where(
                Invoice.contract_id == ms.contract_id,
                Invoice.direction == InvoiceDirection.ISSUED,
                Invoice.status != InvoiceStatus.CANCELLED,
                Invoice.is_deleted == False,
                Invoice.total_amount >= ms.amount * Decimal("0.9"),
                Invoice.total_amount <= ms.amount * Decimal("1.1"),
            )
            count = (await session.execute(inv_q)).scalar_one()

            if count == 0:
                # Get contract info
                contract = await session.get(Contract, ms.contract_id)
                missing.append({
                    "type": "milestone_not_invoiced",
                    "contract_number": contract.contract_number if contract else "unknown",
                    "milestone": ms.title,
                    "completed_date": ms.completed_date.isoformat() if ms.completed_date else None,
                    "expected_amount": float(ms.amount),
                    "severity": "critical",
                    "message": f"Milestone '{ms.title}' finalizat dar nefacturat (~{ms.amount} lei)",
                })

        # Find contracts with billing_frequency='monthly' that missed a month
        monthly_contracts = (await session.execute(
            select(Contract).where(
                Contract.status == ContractStatus.ACTIVE,
                Contract.billing_frequency == "monthly",
                Contract.is_deleted == False,
            )
        )).scalars().all()

        for c in monthly_contracts:
            # Check last invoice date for this contract
            last_inv_q = select(func.max(Invoice.issue_date)).where(
                Invoice.contract_id == c.id,
                Invoice.direction == InvoiceDirection.ISSUED,
                Invoice.status != InvoiceStatus.CANCELLED,
                Invoice.is_deleted == False,
            )
            last_date = (await session.execute(last_inv_q)).scalar_one()

            if last_date and (today - last_date).days > 35:
                days_since = (today - last_date).days
                missing.append({
                    "type": "monthly_gap",
                    "contract_number": c.contract_number,
                    "last_invoice_date": last_date.isoformat(),
                    "days_since_last": days_since,
                    "severity": "warning",
                    "message": f"Contract #{c.contract_number} (lunar) — ultima factură acum {days_since} zile",
                })

    return {
        "missing_invoices": missing,
        "count": len(missing),
        "critical": sum(1 for m in missing if m["severity"] == "critical"),
    }


@tool
async def project_cashflow_daily(days: int = 60) -> dict:
    """Project daily cashflow for the next N days.
    Shows when cash might go negative. Returns day-by-day projection.
    Args: days — how many days to project (default 60)."""
    today = date.today()

    async with get_async_session() as session:
        # Current cash
        bal_q = (
            select(BankTransaction.balance_after)
            .where(BankTransaction.balance_after.isnot(None), BankTransaction.is_deleted == False)
            .order_by(BankTransaction.transaction_date.desc())
            .limit(1)
        )
        cash = float((await session.execute(bal_q)).scalar_one_or_none() or 0)

        # Get all unpaid invoices (both issued and received) with due dates
        inflows_q = select(Invoice.due_date, Invoice.amount_remaining).where(
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.status.not_in([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
            Invoice.due_date >= today,
            Invoice.due_date <= today + timedelta(days=days),
            Invoice.is_deleted == False,
        )
        outflows_q = select(Invoice.due_date, Invoice.amount_remaining).where(
            Invoice.direction == InvoiceDirection.RECEIVED,
            Invoice.status.not_in([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
            Invoice.due_date >= today,
            Invoice.due_date <= today + timedelta(days=days),
            Invoice.is_deleted == False,
        )

        inflows = (await session.execute(inflows_q)).all()
        outflows = (await session.execute(outflows_q)).all()

    # Build day-by-day projection
    # Also estimate recurring monthly costs (salary, rent, hosting)
    # from burn rate
    inflow_map: dict[str, float] = {}
    for due, amt in inflows:
        key = due.isoformat()
        inflow_map[key] = inflow_map.get(key, 0) + float(amt)

    outflow_map: dict[str, float] = {}
    for due, amt in outflows:
        key = due.isoformat()
        outflow_map[key] = outflow_map.get(key, 0) + float(amt)

    projection = []
    balance = cash
    first_negative_day = None

    for i in range(days):
        d = today + timedelta(days=i)
        key = d.isoformat()

        day_in = inflow_map.get(key, 0)
        day_out = outflow_map.get(key, 0)
        balance = balance + day_in - day_out

        projection.append({
            "date": key,
            "inflow": day_in,
            "outflow": day_out,
            "balance": round(balance, 2),
        })

        if balance < 0 and first_negative_day is None:
            first_negative_day = key

    return {
        "starting_cash": cash,
        "days_projected": days,
        "first_negative_day": first_negative_day,
        "final_balance": projection[-1]["balance"] if projection else cash,
        "min_balance": min(p["balance"] for p in projection) if projection else cash,
        "projection": projection[:30],  # Only return first 30 days to save tokens
        "risk_level": (
            "critical" if first_negative_day else
            "warning" if projection and min(p["balance"] for p in projection) < cash * 0.2 else
            "low"
        ),
    }


@tool
async def score_client_risk() -> dict:
    """Score each client's payment risk based on their history.
    Considers: average days late, total overdue amount, payment pattern.
    Returns clients sorted by risk (highest first)."""
    today = date.today()

    async with get_async_session() as session:
        # All issued invoices (paid + unpaid) grouped by recipient
        invoices = (await session.execute(
            select(Invoice).where(
                Invoice.direction == InvoiceDirection.ISSUED,
                Invoice.status != InvoiceStatus.CANCELLED,
                Invoice.is_deleted == False,
            ).limit(500)
        )).scalars().all()

    # Group by recipient company
    clients: dict[str, dict] = {}
    for inv in invoices:
        cid = str(inv.recipient_company_id)
        if cid not in clients:
            clients[cid] = {
                "company_id": cid,
                "total_invoiced": 0,
                "total_paid": 0,
                "total_overdue": 0,
                "invoice_count": 0,
                "overdue_count": 0,
                "late_days_sum": 0,
                "max_late_days": 0,
            }

        c = clients[cid]
        c["total_invoiced"] += float(inv.total_amount)
        c["total_paid"] += float(inv.amount_paid or 0)
        c["invoice_count"] += 1

        if inv.status in (InvoiceStatus.OVERDUE,) or (
            inv.due_date < today and inv.status not in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED)
        ):
            days_late = (today - inv.due_date).days
            c["overdue_count"] += 1
            c["total_overdue"] += float(inv.amount_remaining)
            c["late_days_sum"] += days_late
            if days_late > c["max_late_days"]:
                c["max_late_days"] = days_late

    # Fetch company names for display
    company_names: dict[str, str] = {}
    if clients:
        async with get_async_session() as session:
            companies = (await session.execute(
                select(Company.id, Company.legal_name).where(
                    Company.id.in_(list(clients.keys()))
                )
            )).all()
            company_names = {str(cid): name for cid, name in companies}

    # Score each client
    scored = []
    for c in clients.values():
        if c["invoice_count"] == 0:
            continue

        avg_late = c["late_days_sum"] / c["overdue_count"] if c["overdue_count"] > 0 else 0
        overdue_ratio = c["overdue_count"] / c["invoice_count"]
        amount_at_risk = c["total_overdue"]

        # Risk score 0-100
        score = min(100, int(
            overdue_ratio * 40 +  # 40% weight: what fraction of invoices are overdue
            min(avg_late / 60, 1) * 30 +  # 30% weight: average lateness (capped at 60 days)
            min(amount_at_risk / 50000, 1) * 30  # 30% weight: amount at risk (capped at 50k)
        ))

        risk_level = "high" if score >= 50 else "medium" if score >= 25 else "low"

        c["company_name"] = company_names.get(c["company_id"], "Unknown")
        c["risk_score"] = score
        c["risk_level"] = risk_level
        c["avg_late_days"] = round(avg_late, 1)
        c["overdue_ratio"] = round(overdue_ratio * 100, 1)
        scored.append(c)

    scored.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "clients": scored,
        "high_risk_count": sum(1 for c in scored if c["risk_level"] == "high"),
        "total_at_risk": sum(c["total_overdue"] for c in scored),
    }
