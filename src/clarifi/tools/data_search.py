"""Data search tool — lets the agent query and filter entities in the DB.

Instead of loading ALL invoices or ALL contracts, the agent can search
for specific ones by name, date range, amount range, status, etc.
"""

from datetime import date

from langchain_core.tools import tool
from sqlalchemy import or_, select

from clarifi.db.session import get_async_session
from clarifi.models.bank_transaction import BankTransaction
from clarifi.models.company import Company
from clarifi.models.contract import Contract, ContractStatus
from clarifi.models.invoice import Invoice, InvoiceStatus


@tool
async def search_data(
    entity: str,
    name: str = "",
    status: str = "",
    min_amount: float = 0,
    max_amount: float = 0,
    from_date: str = "",
    to_date: str = "",
    limit: int = 20,
) -> dict:
    """Cauta si filtreaza date in baza de date.

    Args:
        entity — ce cauti: 'invoice', 'contract', 'company', 'transaction'
        name — filtreaza dupa nume/numar (cauta partial)
        status — filtreaza dupa status (ex: 'paid', 'overdue', 'active')
        min_amount — suma minima
        max_amount — suma maxima
        from_date — de la data (YYYY-MM-DD)
        to_date — pana la data (YYYY-MM-DD)
        limit — maxim rezultate (default 20)

    Exemple:
      search_data(entity="invoice", name="TechCorp")
      search_data(entity="invoice", status="overdue", min_amount=10000)
      search_data(entity="contract", from_date="2026-01-01")
      search_data(entity="company", name="StartupVibe")
      search_data(entity="transaction", name="salariu", from_date="2026-03-01")
    """
    limit = min(limit, 50)

    try:
        async with get_async_session() as session:
            if entity == "invoice":
                return await _search_invoices(
                    session, name, status, min_amount, max_amount,
                    from_date, to_date, limit,
                )
            elif entity == "contract":
                return await _search_contracts(
                    session, name, status, min_amount, max_amount,
                    from_date, to_date, limit,
                )
            elif entity == "company":
                return await _search_companies(session, name, limit)
            elif entity == "transaction":
                return await _search_transactions(
                    session, name, min_amount, max_amount,
                    from_date, to_date, limit,
                )
            else:
                return {
                    "error": f"Tip necunoscut: '{entity}'. "
                    "Foloseste: invoice, contract, company, transaction",
                }
    except Exception as e:
        return {"error": f"Eroare la cautare: {e!s}"}


def _parse_date(s: str) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


async def _search_invoices(session, name, status, min_amt, max_amt,
                           from_date, to_date, limit):
    q = select(Invoice)

    if name:
        # Search in invoice number or linked company
        q = q.where(
            or_(
                Invoice.invoice_number.ilike(f"%{name}%"),
            )
        )
    if status:
        # Map common LLM terms to actual enum values
        status_map = {
            "unpaid": "sent", "paid": "paid", "overdue": "overdue",
            "sent": "sent", "received": "received", "draft": "draft",
            "cancelled": "cancelled", "restant": "overdue",
            "neincasat": "sent", "platit": "paid",
        }
        mapped = status_map.get(status.lower())
        if mapped:
            try:
                q = q.where(Invoice.status == InvoiceStatus(mapped))
            except ValueError:
                pass
    if min_amt > 0:
        q = q.where(Invoice.total_amount >= min_amt)
    if max_amt > 0:
        q = q.where(Invoice.total_amount <= max_amt)

    d_from = _parse_date(from_date)
    d_to = _parse_date(to_date)
    if d_from:
        q = q.where(Invoice.issue_date >= d_from)
    if d_to:
        q = q.where(Invoice.issue_date <= d_to)

    q = q.order_by(Invoice.issue_date.desc()).limit(limit)
    rows = (await session.execute(q)).scalars().all()

    # Get company names for display
    company_ids = {r.issuer_company_id for r in rows} | {
        r.recipient_company_id for r in rows
    }
    companies = {}
    if company_ids:
        crows = (await session.execute(
            select(Company).where(Company.id.in_(company_ids))
        )).scalars().all()
        companies = {c.id: c.legal_name for c in crows}

    return {
        "entity": "invoice",
        "count": len(rows),
        "results": [
            {
                "id": r.id,
                "number": r.invoice_number,
                "direction": r.direction.value,
                "status": r.status.value,
                "issuer": companies.get(r.issuer_company_id, "?"),
                "recipient": companies.get(r.recipient_company_id, "?"),
                "total": float(r.total_amount) if r.total_amount else 0,
                "currency": r.currency,
                "issue_date": r.issue_date.isoformat() if r.issue_date else None,
                "due_date": r.due_date.isoformat() if r.due_date else None,
                "amount_remaining": float(r.amount_remaining)
                if r.amount_remaining
                else 0,
            }
            for r in rows
        ],
    }


async def _search_contracts(session, name, status, min_amt, max_amt,
                            from_date, to_date, limit):
    q = select(Contract).where(Contract.is_deleted == False)  # noqa: E712

    if name:
        q = q.where(
            or_(
                Contract.contract_number.ilike(f"%{name}%"),
                Contract.title.ilike(f"%{name}%"),
            )
        )
    if status:
        try:
            q = q.where(Contract.status == ContractStatus(status.upper()))
        except ValueError:
            pass
    if min_amt > 0:
        q = q.where(Contract.total_value >= min_amt)
    if max_amt > 0:
        q = q.where(Contract.total_value <= max_amt)

    d_from = _parse_date(from_date)
    d_to = _parse_date(to_date)
    if d_from:
        q = q.where(Contract.start_date >= d_from)
    if d_to:
        q = q.where(Contract.end_date <= d_to)

    q = q.order_by(Contract.start_date.desc()).limit(limit)
    rows = (await session.execute(q)).scalars().all()

    company_ids = {r.counterparty_id for r in rows if r.counterparty_id}
    companies = {}
    if company_ids:
        crows = (await session.execute(
            select(Company).where(Company.id.in_(company_ids))
        )).scalars().all()
        companies = {c.id: c.legal_name for c in crows}

    return {
        "entity": "contract",
        "count": len(rows),
        "results": [
            {
                "id": r.id,
                "number": r.contract_number,
                "title": r.title,
                "counterparty": companies.get(r.counterparty_id, "?")
                if r.counterparty_id
                else None,
                "total_value": float(r.total_value) if r.total_value else 0,
                "currency": r.currency,
                "status": r.status.value if r.status else "?",
                "start_date": r.start_date.isoformat()
                if r.start_date
                else None,
                "end_date": r.end_date.isoformat() if r.end_date else None,
            }
            for r in rows
        ],
    }


async def _search_companies(session, name, limit):
    q = select(Company).where(Company.is_deleted == False)  # noqa: E712

    if name:
        q = q.where(
            or_(
                Company.legal_name.ilike(f"%{name}%"),
                Company.trade_name.ilike(f"%{name}%"),
                Company.tax_id.ilike(f"%{name}%"),
            )
        )

    q = q.order_by(Company.legal_name).limit(limit)
    rows = (await session.execute(q)).scalars().all()

    return {
        "entity": "company",
        "count": len(rows),
        "results": [
            {
                "id": r.id,
                "name": r.legal_name,
                "trade_name": r.trade_name,
                "tax_id": r.tax_id,
                "role": r.role.value,
                "city": r.city,
                "email": r.email,
                "phone": r.phone,
            }
            for r in rows
        ],
    }


async def _search_transactions(session, name, min_amt, max_amt,
                               from_date, to_date, limit):
    q = select(BankTransaction)

    if name:
        q = q.where(
            or_(
                BankTransaction.description.ilike(f"%{name}%"),
                BankTransaction.counterparty_name.ilike(f"%{name}%"),
                BankTransaction.reference.ilike(f"%{name}%"),
            )
        )
    if min_amt > 0:
        q = q.where(BankTransaction.amount >= min_amt)
    if max_amt > 0:
        q = q.where(BankTransaction.amount <= max_amt)

    d_from = _parse_date(from_date)
    d_to = _parse_date(to_date)
    if d_from:
        q = q.where(BankTransaction.transaction_date >= d_from)
    if d_to:
        q = q.where(BankTransaction.transaction_date <= d_to)

    q = q.order_by(BankTransaction.transaction_date.desc()).limit(limit)
    rows = (await session.execute(q)).scalars().all()

    return {
        "entity": "transaction",
        "count": len(rows),
        "results": [
            {
                "id": r.id,
                "date": r.transaction_date.isoformat()
                if r.transaction_date
                else None,
                "type": r.transaction_type.value
                if r.transaction_type
                else "?",
                "amount": float(r.amount) if r.amount else 0,
                "description": r.description,
                "counterparty": r.counterparty_name,
                "reference": r.reference,
                "balance_after": float(r.balance_after)
                if r.balance_after
                else None,
                "iban": r.bank_account_iban,
            }
            for r in rows
        ],
    }
