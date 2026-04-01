"""Discovery tool — gives the agent a snapshot of what data exists.

Answers: "Do I have any data to work with? What has been uploaded?
How many invoices, contracts, bank statements exist?"

This should be the FIRST tool called when the agent isn't sure
what data is available for the current user/company.
"""

from datetime import date

from langchain_core.tools import tool
from sqlalchemy import func, select

from clarifi.db.session import get_async_session
from clarifi.models.bank_transaction import BankTransaction
from clarifi.models.company import Company, CompanyRole
from clarifi.models.contract import Contract
from clarifi.models.document import Document
from clarifi.models.estimate import Estimate
from clarifi.models.invoice import Invoice, InvoiceDirection
from clarifi.models.scheduled_task import ScheduledTask


@tool
async def discover_data() -> dict:
    """Descoperă ce date sunt disponibile pentru compania curentă.

    Apelează PRIMA DATĂ când nu știi ce date are utilizatorul.
    Returnează un rezumat: câte facturi, contracte, extrase bancare,
    documente sunt indexate, și dacă lipsește ceva important.

    Folosește rezultatul pentru a ghida conversația:
    - Dacă nu sunt date → spune utilizatorului să încarce documente
    - Dacă lipsesc extrase bancare → nu poți răspunde la "câți bani am?"
    - Dacă lipsesc contracte → nu poți verifica obligații
    """
    today = date.today()

    async with get_async_session() as session:
        # Company
        own = (await session.execute(
            select(Company).where(
                Company.role == CompanyRole.OWN_COMPANY,
            )
        )).scalar_one_or_none()

        # Counts
        n_invoices_issued = (await session.execute(
            select(func.count(Invoice.id)).where(
                Invoice.direction == InvoiceDirection.ISSUED,
            )
        )).scalar_one()

        n_invoices_received = (await session.execute(
            select(func.count(Invoice.id)).where(
                Invoice.direction == InvoiceDirection.RECEIVED,
            )
        )).scalar_one()

        n_contracts = (await session.execute(
            select(func.count(Contract.id))
        )).scalar_one()

        n_bank_txns = (await session.execute(
            select(func.count(BankTransaction.id))
        )).scalar_one()

        n_documents = (await session.execute(
            select(func.count(Document.id)).where(
                Document.is_deleted == False,  # noqa: E712
            )
        )).scalar_one()

        n_estimates = (await session.execute(
            select(func.count(Estimate.id))
        )).scalar_one()

        n_companies = (await session.execute(
            select(func.count(Company.id)).where(
                Company.role != CompanyRole.OWN_COMPANY,
            )
        )).scalar_one()

        n_reminders = (await session.execute(
            select(func.count(ScheduledTask.id)).where(
                ScheduledTask.is_active == True,  # noqa: E712
            )
        )).scalar_one()

        # Latest bank transaction date
        latest_bank = (await session.execute(
            select(func.max(BankTransaction.transaction_date))
        )).scalar_one()

        # Latest invoice date
        latest_invoice = (await session.execute(
            select(func.max(Invoice.issue_date))
        )).scalar_one()

    # Build gaps list
    gaps = []
    if n_bank_txns == 0:
        gaps.append("Nu ai extrase bancare — nu pot calcula soldul real")
    elif latest_bank and (today - latest_bank).days > 7:
        gaps.append(
            f"Ultimul extras bancar e din {latest_bank.strftime('%d.%m.%Y')} "
            f"({(today - latest_bank).days} zile)"
        )
    if n_invoices_issued == 0:
        gaps.append("Nu ai facturi emise — nu pot calcula creanțe")
    if n_contracts == 0:
        gaps.append("Nu ai contracte — nu pot verifica obligații")
    if not own:
        gaps.append("Nu ai companie configurată — finalizează onboarding-ul")

    has_data = (
        n_invoices_issued + n_invoices_received + n_contracts + n_bank_txns
    ) > 0

    return {
        "has_data": has_data,
        "company": {
            "name": own.legal_name if own else None,
            "tax_id": own.tax_id if own else None,
            "configured": own is not None,
        },
        "counts": {
            "facturi_emise": n_invoices_issued,
            "facturi_primite": n_invoices_received,
            "contracte": n_contracts,
            "tranzactii_bancare": n_bank_txns,
            "documente_incarcate": n_documents,
            "devize": n_estimates,
            "clienti_furnizori": n_companies,
            "remindere_active": n_reminders,
        },
        "latest": {
            "extras_bancar": latest_bank.isoformat() if latest_bank else None,
            "factura": latest_invoice.isoformat() if latest_invoice else None,
        },
        "gaps": gaps,
    }
