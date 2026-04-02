"""Invoice emission tool — create invoices from conversations.

The agent can create invoices when the user says things like:
"Emite o factura de 5000 lei pentru RebelDot pentru consultanta"
"""

from datetime import date, timedelta
from decimal import Decimal

from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.agent.company_scope import get_user_company_ids
from clarifi.db.session import get_async_session
from clarifi.models.company import Company, CompanyRole
from clarifi.models.contract import Contract
from clarifi.models.invoice import Invoice, InvoiceDirection, InvoiceLineItem, InvoiceStatus


async def _get_next_invoice_number(session, company_id: str) -> str:
    """Generate next invoice number: {YEAR}-{NNNN}."""
    year = date.today().year
    prefix = f"{year}-"

    # Find highest number for this year
    last = (await session.execute(
        select(Invoice.invoice_number)
        .where(
            Invoice.issuer_company_id == company_id,
            Invoice.invoice_number.like(f"{prefix}%"),
        )
        .order_by(Invoice.invoice_number.desc())
        .limit(1)
    )).scalar_one_or_none()

    if last:
        try:
            num = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1

    return f"{prefix}{num:04d}"


@tool
async def emit_invoice(
    client_name: str,
    items: list[dict],
    client_tax_id: str = "",
    currency: str = "RON",
    vat_rate: float = 19.0,
    payment_terms_days: int = 30,
    contract_reference: str = "",
    notes: str = "",
) -> dict:
    """Emite o factura noua catre un client.

    Args:
        client_name — numele clientului (ex: "RebelDot Solutions SRL")
        items — lista de servicii/produse: [{"description": "Consultanta IT", "quantity": 1, "unit_price": 5000}]
        client_tax_id — CUI-ul clientului (optional)
        currency — moneda (default RON)
        vat_rate — procent TVA (default 19%)
        payment_terms_days — termen de plata in zile (default 30)
        contract_reference — numar contract asociat (optional)
        notes — observatii pe factura (optional)

    Returneaza factura creata cu numar, total, scadenta.
    """
    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        # Find own company
        own = None
        if company_ids:
            own = (await session.execute(
                select(Company).where(
                    Company.id.in_(company_ids),
                    Company.role == CompanyRole.OWN_COMPANY,
                ).limit(1)
            )).scalar_one_or_none()

        if not own:
            return {"error": "Nu ai companie configurata. Finalizeaza onboarding-ul."}

        # Find or create client company
        client_id = None
        if client_tax_id:
            client = (await session.execute(
                select(Company).where(
                    Company.tax_id == client_tax_id,
                    Company.is_deleted == False,  # noqa: E712
                )
            )).scalar_one_or_none()
            if client:
                client_id = client.id

        if not client_id:
            # Try by name
            client = (await session.execute(
                select(Company).where(
                    Company.legal_name.ilike(f"%{client_name}%"),
                    Company.is_deleted == False,  # noqa: E712
                ).limit(1)
            )).scalar_one_or_none()
            if client:
                client_id = client.id

        if not client_id:
            # Create new client company
            client = Company(
                legal_name=client_name,
                tax_id=client_tax_id or None,
                role=CompanyRole.CLIENT,
            )
            session.add(client)
            await session.flush()
            client_id = client.id

        # Generate invoice number
        inv_number = await _get_next_invoice_number(session, own.id)

        # Calculate amounts
        subtotal = Decimal("0")
        line_items_data = []
        for i, item in enumerate(items):
            qty = Decimal(str(item.get("quantity", 1)))
            price = Decimal(str(item.get("unit_price", 0)))
            line_total = qty * price
            subtotal += line_total
            line_items_data.append({
                "line_number": i + 1,
                "description": item.get("description", ""),
                "quantity": qty,
                "unit_price": price,
                "line_total": line_total,
            })

        vat = (subtotal * Decimal(str(vat_rate)) / 100).quantize(Decimal("0.01"))
        total = subtotal + vat
        today = date.today()
        due = today + timedelta(days=payment_terms_days)

        # Find linked contract
        contract_id = None
        if contract_reference:
            ct = (await session.execute(
                select(Contract).where(
                    Contract.contract_number == contract_reference,
                    Contract.is_deleted == False,  # noqa: E712
                ).limit(1)
            )).scalar_one_or_none()
            if ct:
                contract_id = ct.id

        # Create invoice
        inv = Invoice(
            invoice_number=inv_number,
            direction=InvoiceDirection.ISSUED,
            status=InvoiceStatus.SENT,
            issuer_company_id=own.id,
            recipient_company_id=client_id,
            contract_id=contract_id,
            issue_date=today,
            due_date=due,
            subtotal=subtotal,
            vat_amount=vat,
            total_amount=total,
            currency=currency,
            amount_paid=Decimal("0"),
            amount_remaining=total,
            payment_terms_days=payment_terms_days,
            notes=notes or None,
            freshness_status="verified",
            data_source="manual",
        )
        session.add(inv)
        await session.flush()

        # Create line items
        for li in line_items_data:
            session.add(InvoiceLineItem(
                invoice_id=inv.id,
                line_number=li["line_number"],
                description=li["description"],
                quantity=li["quantity"],
                unit_price=li["unit_price"],
                line_total=li["line_total"],
            ))

        inv_id = inv.id

    return {
        "status": "emitted",
        "invoice_number": inv_number,
        "client": client_name,
        "subtotal": float(subtotal),
        "vat": float(vat),
        "total": float(total),
        "currency": currency,
        "issue_date": today.isoformat(),
        "due_date": due.isoformat(),
        "invoice_id": inv_id,
        "line_items": len(line_items_data),
        "contract_reference": contract_reference or None,
    }
