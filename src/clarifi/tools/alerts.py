"""Alert tools."""

from datetime import date, timedelta

from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.db.session import get_async_session
from clarifi.models.alert import Alert, AlertStatus
from clarifi.models.contract import Contract, ContractMilestone, ContractStatus
from clarifi.models.invoice import Invoice, InvoiceDirection, InvoiceStatus


@tool
async def query_alerts() -> dict:
    """Get all active alerts and real-time warnings: overdue invoices, expiring contracts, due milestones.
    Returns alerts sorted by severity (critical first)."""
    today = date.today()
    alerts = []

    from clarifi.agent.company_scope import get_user_company_ids
    from sqlalchemy import or_

    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        # Persisted alerts
        db_alerts = (await session.execute(
            select(Alert).where(Alert.status == AlertStatus.NEW)
        )).scalars().all()
        for a in db_alerts:
            alerts.append({"type": a.alert_type.value, "severity": a.severity.value, "message": a.message})

        # Real-time: overdue invoices
        inv_filters = [
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.status.not_in([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
            Invoice.due_date < today,
            Invoice.is_deleted == False,  # noqa: E712
        ]
        if company_ids:
            inv_filters.append(or_(
                Invoice.issuer_company_id.in_(company_ids),
                Invoice.recipient_company_id.in_(company_ids),
            ))
        overdue = (await session.execute(
            select(Invoice).where(*inv_filters)
            .order_by(Invoice.due_date).limit(50)
        )).scalars().all()
        for inv in overdue:
            days = (today - inv.due_date).days
            alerts.append({
                "type": "invoice_overdue",
                "severity": "critical" if days > 30 else "warning",
                "message": f"Factura #{inv.invoice_number} — restantă {days} zile ({inv.amount_remaining} {inv.currency})",
            })

        # Overdue milestones
        overdue_ms = (await session.execute(
            select(ContractMilestone).where(ContractMilestone.completed == False, ContractMilestone.due_date < today)
        )).scalars().all()
        for ms in overdue_ms:
            days = (today - ms.due_date).days
            alerts.append({
                "type": "milestone_overdue",
                "severity": "warning",
                "message": f"Milestone '{ms.title}' depășit cu {days} zile",
            })

        # Expiring contracts (next 30 days)
        expiring = (await session.execute(
            select(Contract).where(
                Contract.status == ContractStatus.ACTIVE,
                Contract.end_date.isnot(None),
                Contract.end_date <= today + timedelta(days=30),
                Contract.end_date >= today, Contract.is_deleted == False,
            )
        )).scalars().all()
        for c in expiring:
            days = (c.end_date - today).days
            alerts.append({
                "type": "contract_expiring",
                "severity": "warning",
                "message": f"Contract #{c.contract_number} expiră în {days} zile",
            })

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))

    return {
        "alerts": alerts,
        "count": len(alerts),
        "critical": sum(1 for a in alerts if a["severity"] == "critical"),
        "warnings": sum(1 for a in alerts if a["severity"] == "warning"),
    }
