"""Data query and management tools — list invoices, transactions, mark paid."""

from datetime import datetime, timezone
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.db.session import get_async_session
from clarifi.models.bank_transaction import BankTransaction
from clarifi.models.invoice import Invoice, InvoiceDirection, InvoiceStatus


@tool
async def query_invoices(
    direction: str = "all",
    status: str = "all",
    limit: int = 50,
) -> dict:
    """List invoices with optional filters.
    Args:
        direction — 'issued', 'received', or 'all'
        status — 'paid', 'unpaid', 'overdue', or 'all'
        limit — max results (default 50)
    Returns list of invoices with key fields."""
    from clarifi.agent.company_scope import get_user_company_ids
    from sqlalchemy import or_

    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        q = select(Invoice).where(Invoice.is_deleted == False)  # noqa: E712
        if company_ids:
            q = q.where(or_(
                Invoice.issuer_company_id.in_(company_ids),
                Invoice.recipient_company_id.in_(company_ids),
            ))

        if direction == "issued":
            q = q.where(Invoice.direction == InvoiceDirection.ISSUED)
        elif direction == "received":
            q = q.where(Invoice.direction == InvoiceDirection.RECEIVED)

        if status == "paid":
            q = q.where(Invoice.status == InvoiceStatus.PAID)
        elif status == "unpaid":
            q = q.where(Invoice.status.not_in([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]))
        elif status == "overdue":
            from datetime import date
            q = q.where(
                Invoice.status.not_in([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
                Invoice.due_date < date.today(),
            )

        q = q.order_by(Invoice.issue_date.desc()).limit(min(limit, 200))
        invoices = (await session.execute(q)).scalars().all()

    return {
        "count": len(invoices),
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "direction": inv.direction.value,
                "status": inv.status.value,
                "total_amount": float(inv.total_amount),
                "amount_remaining": float(inv.amount_remaining),
                "currency": inv.currency,
                "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "contract_id": inv.contract_id,
                "freshness": inv.freshness_status,
            }
            for inv in invoices
        ],
    }


@tool
async def query_transactions(
    days: int = 30,
    limit: int = 50,
) -> dict:
    """List recent bank transactions.
    Args:
        days — how many days back to look (default 30)
        limit — max results (default 50)
    Returns list of transactions with amounts, counterparties, matching status."""
    from datetime import date, timedelta

    cutoff = date.today() - timedelta(days=days)

    async with get_async_session() as session:
        q = (
            select(BankTransaction)
            .where(BankTransaction.is_deleted == False, BankTransaction.transaction_date >= cutoff)
            .order_by(BankTransaction.transaction_date.desc())
            .limit(min(limit, 200))
        )
        txns = (await session.execute(q)).scalars().all()

    return {
        "count": len(txns),
        "transactions": [
            {
                "id": txn.id,
                "date": txn.transaction_date.isoformat(),
                "type": txn.transaction_type.value,
                "amount": float(txn.amount),
                "currency": txn.currency,
                "description": txn.description,
                "counterparty": txn.counterparty_name,
                "reference": txn.reference,
                "is_matched": txn.is_matched,
                "balance_after": float(txn.balance_after) if txn.balance_after else None,
            }
            for txn in txns
        ],
    }


@tool
async def mark_invoice_paid(invoice_id: str, amount_paid: float | None = None) -> dict:
    """Mark an invoice as paid (fully or partially).
    Args:
        invoice_id — the invoice ID
        amount_paid — amount paid (defaults to full remaining amount)
    Use when: user says "am incasat factura X" or "invoice X was paid"."""
    now = datetime.now(timezone.utc)

    async with get_async_session() as session:
        inv = await session.get(Invoice, invoice_id)
        if not inv:
            return {"error": f"Invoice {invoice_id} not found"}

        payment = Decimal(str(amount_paid)) if amount_paid else inv.amount_remaining
        inv.amount_paid = (inv.amount_paid or Decimal("0")) + payment
        inv.amount_remaining = max(Decimal("0"), inv.total_amount - inv.amount_paid)

        if inv.amount_remaining <= 0:
            inv.status = InvoiceStatus.PAID
            inv.amount_remaining = Decimal("0")
        else:
            inv.status = InvoiceStatus.PARTIALLY_PAID

        inv.updated_at = now
        number = inv.invoice_number
        new_status = inv.status.value
        remaining = float(inv.amount_remaining)

    return {
        "status": "updated",
        "invoice_number": number,
        "new_status": new_status,
        "amount_paid": float(payment),
        "remaining": remaining,
    }
