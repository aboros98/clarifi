"""Payment matching tools: match bank transactions to invoices."""

from datetime import datetime, timezone
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.db.session import get_async_session
from clarifi.models.bank_transaction import (
    BankTransaction,
    MatchConfidence,
    PaymentInvoiceMatch,
    TransactionType,
)
from clarifi.models.invoice import Invoice, InvoiceDirection, InvoiceStatus


def _score_match(txn: BankTransaction, inv: Invoice) -> tuple[float, str]:
    """Score how likely a transaction matches an invoice. Returns (score, reason)."""
    score = 0.0
    reasons = []

    # Amount match
    if inv.amount_remaining and inv.amount_remaining > 0:
        diff_pct = abs(float(txn.amount - inv.amount_remaining)) / float(inv.amount_remaining)
        if diff_pct == 0:
            score += 0.4
            reasons.append("exact amount match")
        elif diff_pct < 0.02:
            score += 0.25
            reasons.append(f"amount within {diff_pct:.1%}")

    # Reference contains invoice number
    ref = (txn.reference or "") + " " + (txn.description or "")
    if inv.invoice_number and inv.invoice_number.lower() in ref.lower():
        score += 0.3
        reasons.append(f"reference contains '{inv.invoice_number}'")

    # Date proximity
    if inv.due_date:
        days_diff = abs((txn.transaction_date - inv.due_date).days)
        if days_diff <= 3:
            score += 0.2
            reasons.append(f"within {days_diff} days of due date")
        elif days_diff <= 14:
            score += 0.1
            reasons.append(f"within {days_diff} days of due date")

    # Counterparty name partial match (very basic)
    if txn.counterparty_name and inv.issuer_company_id:
        # We'd need to join company for proper name matching
        # For now, just check if any words overlap
        pass

    return min(score, 1.0), "; ".join(reasons) if reasons else "no strong signal"


@tool
async def run_payment_matching() -> dict:
    """Auto-match unmatched bank credit transactions to unpaid issued invoices.
    Returns suggested matches with confidence scores for user confirmation."""

    from clarifi.agent.company_scope import get_user_company_ids
    from sqlalchemy import or_

    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        # Unmatched credit transactions
        txns = (await session.execute(
            select(BankTransaction).where(
                BankTransaction.is_matched == False,
                BankTransaction.transaction_type == TransactionType.CREDIT,
                BankTransaction.is_deleted == False,
            ).order_by(BankTransaction.transaction_date.desc()).limit(50)
        )).scalars().all()

        # Unpaid issued invoices — scoped to user's companies
        inv_q = select(Invoice).where(
            Invoice.direction == InvoiceDirection.ISSUED,
            Invoice.status.not_in([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
            Invoice.is_deleted == False,
        )
        if company_ids:
            inv_q = inv_q.where(or_(
                Invoice.issuer_company_id.in_(company_ids),
                Invoice.recipient_company_id.in_(company_ids),
            ))
        invoices = (await session.execute(inv_q.limit(100))).scalars().all()

        suggestions = []
        for txn in txns:
            best_score = 0.0
            best_inv = None
            best_reason = ""

            for inv in invoices:
                score, reason = _score_match(txn, inv)
                if score > best_score:
                    best_score = score
                    best_inv = inv
                    best_reason = reason

            if best_inv and best_score >= 0.3:
                confidence = (
                    MatchConfidence.HIGH if best_score >= 0.7
                    else MatchConfidence.MEDIUM if best_score >= 0.5
                    else MatchConfidence.LOW
                )
                suggestions.append({
                    "transaction_date": txn.transaction_date.isoformat(),
                    "transaction_amount": float(txn.amount),
                    "transaction_ref": txn.reference,
                    "counterparty": txn.counterparty_name,
                    "invoice_number": best_inv.invoice_number,
                    "invoice_amount": float(best_inv.amount_remaining),
                    "confidence": confidence.value,
                    "score": best_score,
                    "reason": best_reason,
                    "transaction_id": str(txn.id),
                    "invoice_id": str(best_inv.id),
                })

    suggestions.sort(key=lambda s: s["score"], reverse=True)

    return {
        "unmatched_transactions": len(txns),
        "unpaid_invoices": len(invoices),
        "suggestions": suggestions,
        "high_confidence": sum(1 for s in suggestions if s["confidence"] == "high"),
        "medium_confidence": sum(1 for s in suggestions if s["confidence"] == "medium"),
    }


@tool
async def confirm_match(transaction_id: str, invoice_id: str) -> dict:
    """Confirm a payment-invoice match. Updates both the transaction and invoice records.
    Args: transaction_id, invoice_id — IDs from run_payment_matching suggestions."""
    now = datetime.now(timezone.utc)

    async with get_async_session() as session:
        txn = await session.get(BankTransaction, transaction_id)
        inv = await session.get(Invoice, invoice_id)

        if not txn:
            return {"error": f"Transaction {transaction_id} not found"}
        if not inv:
            return {"error": f"Invoice {invoice_id} not found"}

        matched_amount = min(txn.amount, inv.amount_remaining)

        # Create match record
        match = PaymentInvoiceMatch(
            bank_transaction_id=transaction_id,
            invoice_id=invoice_id,
            matched_amount=matched_amount,
            confidence=MatchConfidence.MANUAL,
            confidence_score=Decimal("1.00"),
            match_reason="User confirmed match",
            confirmed=True,
            confirmed_by="user",
            confirmed_at=now,
        )
        session.add(match)

        # Update transaction
        txn.is_matched = True

        # Update invoice
        inv.amount_paid = (inv.amount_paid or Decimal("0")) + matched_amount
        inv.amount_remaining = inv.total_amount - inv.amount_paid
        if inv.amount_remaining <= 0:
            inv.status = InvoiceStatus.PAID
            inv.amount_remaining = Decimal("0")
        elif inv.amount_paid > 0:
            inv.status = InvoiceStatus.PARTIALLY_PAID

        await session.flush()
        match_id = str(match.id)

    return {
        "status": "matched",
        "match_id": match_id,
        "matched_amount": float(matched_amount),
        "invoice_number": inv.invoice_number,
        "invoice_new_status": inv.status.value,
        "remaining": float(inv.amount_remaining),
    }
