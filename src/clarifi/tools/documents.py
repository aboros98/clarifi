"""Document ingestion and data persistence tools."""

import hashlib
import mimetypes
import shutil
from datetime import date as date_type
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.agent.context import current_user_id
from clarifi.config import settings
from clarifi.db.session import get_async_session
from clarifi.ingestion.parser_factory import ParserFactory
from clarifi.models.bank_transaction import BankTransaction, TransactionType
from clarifi.models.company import Company, CompanyRole
from clarifi.models.contract import (
    Contract,
    ContractMilestone,
    ContractObligation,
    ContractPenalty,
    ContractStatus,
)
from clarifi.models.document import Document, DocumentType, ProcessingStatus
from clarifi.models.estimate import Estimate, EstimateLineItem, EstimateStatus
from clarifi.models.invoice import Invoice, InvoiceDirection, InvoiceStatus


@tool
async def ingest_document(file_path: str) -> dict:
    """Parse a document (PDF, DOCX, image, CSV) and extract its text content.
    Returns the raw text and file metadata. Use this before asking the LLM to extract structured fields.
    Args: file_path — path to the file to process."""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    file_bytes = path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or "application/octet-stream"

    parser = ParserFactory.get_parser(mime_type)
    result = await parser.parse(path)

    # Copy file to permanent storage
    processed = Path(settings.processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    permanent_path = processed / f"{file_hash}_{path.name}"
    if not permanent_path.exists():
        shutil.copy2(str(path), str(permanent_path))

    async with get_async_session() as session:
        existing = (await session.execute(
            select(Document).where(Document.file_hash_sha256 == file_hash)
        )).scalar_one_or_none()
        if existing:
            return {
                "status": "duplicate",
                "message": f"Document already processed (ID: {existing.id})",
                "document_id": str(existing.id),
            }

        doc = Document(
            original_filename=path.name,
            storage_path=str(permanent_path),
            mime_type=mime_type,
            file_size_bytes=len(file_bytes),
            file_hash_sha256=file_hash,
            document_type=DocumentType.OTHER,
            processing_status=ProcessingStatus.PARSED,
            raw_text=result.text,
            page_count=result.page_count,
            ocr_applied=result.ocr_applied,
            user_id=current_user_id.get(),
        )
        session.add(doc)
        await session.flush()
        doc_id = str(doc.id)

    return {
        "status": "parsed",
        "document_id": doc_id,
        "filename": path.name,
        "mime_type": mime_type,
        "page_count": result.page_count,
        "ocr_applied": result.ocr_applied,
        "text_preview": result.text[:3000],
        "text_length": len(result.text),
    }


@tool
async def save_extracted_data(entity_type: str, data: dict, document_id: str = "", confirmed: bool = False) -> dict:
    """Save extracted data to the database. Supports: invoice, contract, bank_statement, estimate.
    Args:
        entity_type — 'invoice', 'contract', 'bank_statement', or 'estimate'
        data — extracted fields as a dict
        document_id — the source document ID from ingest_document
        confirmed — True if user has confirmed the data is correct
    Returns the saved entity ID or count."""
    from clarifi.tools.validators import validate_and_normalize

    # Validate and normalize Romanian formats before saving
    data, validation_warnings = validate_and_normalize(data, entity_type)

    freshness = "verified" if confirmed else "unverified"
    now = datetime.now(timezone.utc)

    async with get_async_session() as session:
        own = (await session.execute(
            select(Company)
            .where(
                Company.role == CompanyRole.OWN_COMPANY,
                Company.is_deleted == False,  # noqa: E712
            )
            .limit(1)
        )).scalar_one_or_none()
        if not own:
            return {"error": "Nicio companie configurata. Finalizeaza onboarding-ul mai intai."}
        own_id = own.id

        if entity_type == "invoice":
            result = await _save_invoice(session, data, document_id, freshness, now, own_id)
            if validation_warnings:
                result["warnings"] = validation_warnings
            return result
        elif entity_type == "contract":
            result = await _save_contract(session, data, document_id, freshness, now)
            if validation_warnings:
                result["warnings"] = validation_warnings
            return result
        elif entity_type == "bank_statement":
            result = await _save_bank_statement(session, data, document_id, freshness, now)
            if validation_warnings:
                result["warnings"] = validation_warnings
            return result
        elif entity_type == "estimate":
            result = await _save_estimate(
                session, data, document_id, freshness, now, own_id,
            )
            if validation_warnings:
                result["warnings"] = validation_warnings
            return result
        else:
            return {
                "error": f"Unknown entity_type '{entity_type}'. "
                "Supported: invoice, contract, bank_statement, estimate",
            }


async def _save_invoice(session, data, document_id, freshness, now, own_id):
    if not data.get("issue_date") or not data.get("due_date"):
        return {"error": "Missing required fields: issue_date and due_date are mandatory"}

    company_id = await _find_or_create_company(session, data.get("vendor_or_client_tax_id"), data.get("vendor_or_client_name"), "supplier" if data.get("is_incoming") else "client")
    contract_id = await _find_contract_by_ref(session, data.get("contract_reference"))

    is_incoming = data.get("is_incoming", True)
    direction = InvoiceDirection.RECEIVED if is_incoming else InvoiceDirection.ISSUED

    total = _safe_decimal(data.get("total_amount"))
    vat = _safe_decimal(data.get("vat_amount"))
    subtotal_raw = _safe_decimal(data.get("subtotal"))
    subtotal = subtotal_raw if subtotal_raw > 0 else (total - vat if total > 0 else Decimal("0"))

    inv = Invoice(
        invoice_number=data.get("invoice_number", "UNKNOWN"),
        direction=direction,
        status=InvoiceStatus.RECEIVED if is_incoming else InvoiceStatus.SENT,
        issuer_company_id=(company_id or own_id) if is_incoming else own_id,
        recipient_company_id=own_id if is_incoming else (company_id or own_id),
        contract_id=contract_id,
        issue_date=_to_date(data["issue_date"]),
        due_date=_to_date(data["due_date"]),
        subtotal=subtotal,
        vat_amount=vat,
        total_amount=total,
        currency=data.get("currency", "RON"),
        amount_paid=Decimal("0"),
        amount_remaining=total,
        source_document_id=document_id or None,
        freshness_status=freshness,
        verified_at=now if freshness == "verified" else None,
        data_source="extraction",
    )
    session.add(inv)
    await session.flush()
    return {"status": "saved", "entity_type": "invoice", "id": str(inv.id)}


async def _save_contract(session, data, document_id, freshness, now):
    if not data.get("contract_number"):
        return {"error": "Missing required field: contract_number"}

    counterparty_id = await _find_or_create_company(session, data.get("client_tax_id"), data.get("client_name"), "client")

    contract = Contract(
        contract_number=data["contract_number"],
        title=data.get("contract_number", "Untitled"),
        counterparty_id=counterparty_id,
        total_value=_safe_decimal(data.get("total_value")),
        currency=data.get("currency", "RON"),
        start_date=_to_date(data.get("start_date")),
        end_date=_to_date(data.get("end_date")),
        signed_date=_to_date(data.get("contract_date") or data.get("start_date")),
        status=ContractStatus.ACTIVE,
        payment_terms_days=data.get("payment_terms_days"),
        billing_frequency=data.get("billing_frequency"),
        source_document_id=document_id or None,
        freshness_status=freshness,
        verified_at=now if freshness == "verified" else None,
        data_source="extraction",
    )
    session.add(contract)
    await session.flush()
    contract_id = str(contract.id)

    # Save milestones
    milestones_saved = 0
    for ms in data.get("milestones", []):
        if ms.get("due_date"):
            milestone = ContractMilestone(
                contract_id=contract_id,
                title=ms.get("name", "Milestone"),
                due_date=_to_date(ms["due_date"]),
                amount=_safe_decimal(ms.get("amount")) if ms.get("amount") else None,
            )
            session.add(milestone)
            milestones_saved += 1

    # Save obligations
    for ob in data.get("obligations", []):
        if isinstance(ob, str) and ob.strip():
            session.add(ContractObligation(
                contract_id=contract_id,
                obligated_party="own",
                description=ob,
            ))

    # Save penalties
    for pen in data.get("penalties", []):
        if isinstance(pen, str) and pen.strip():
            session.add(ContractPenalty(
                contract_id=contract_id,
                trigger_condition=pen,
                penalty_type="described",
                penalty_value=Decimal("0"),
            ))

    await session.flush()
    return {
        "status": "saved",
        "entity_type": "contract",
        "id": contract_id,
        "milestones_saved": milestones_saved,
    }


async def _save_estimate(session, data, document_id, freshness, now, own_id):
    if not data.get("estimate_number"):
        return {"error": "Missing required field: estimate_number"}

    client_id = await _find_or_create_company(
        session,
        data.get("client_tax_id"),
        data.get("client_name"),
        "client",
    )

    total = _safe_decimal(data.get("total_amount"))
    vat = _safe_decimal(data.get("vat_amount"))
    subtotal_raw = _safe_decimal(data.get("subtotal"))
    subtotal = subtotal_raw if subtotal_raw > 0 else (
        total - vat if total > 0 else Decimal("0")
    )

    est = Estimate(
        estimate_number=data["estimate_number"],
        title=data.get("estimate_number", "Deviz"),
        client_company_id=client_id or own_id,
        issue_date=_to_date(data.get("issue_date")) or date_type.today(),
        valid_until=_to_date(data.get("valid_until")) or date_type.today(),
        subtotal=subtotal,
        vat_amount=vat,
        total_amount=total,
        currency=data.get("currency", "RON"),
        status=EstimateStatus.DRAFT,
        source_document_id=document_id or None,
        freshness_status=freshness,
        verified_at=now if freshness == "verified" else None,
        data_source="extraction",
    )
    session.add(est)
    await session.flush()

    # Save line items
    for i, item in enumerate(data.get("line_items", [])):
        li = EstimateLineItem(
            estimate_id=est.id,
            line_number=i + 1,
            description=str(item.get("description", "")),
            quantity=_safe_decimal(item.get("quantity", 1)),
            unit=item.get("unit"),
            unit_price=_safe_decimal(item.get("unit_price", 0)),
            line_total=_safe_decimal(item.get("amount", 0)),
        )
        session.add(li)

    return {
        "status": "saved",
        "entity_type": "estimate",
        "id": str(est.id),
    }


async def _save_bank_statement(session, data, document_id, freshness, now):
    iban = data.get("account_iban", "UNKNOWN")
    currency = data.get("currency", "RON")
    transactions = data.get("transactions", [])

    if not transactions:
        return {"error": "No transactions found in bank statement data"}

    opening = _safe_decimal(data.get("opening_balance"))
    running_balance = opening

    saved = 0
    for txn in transactions:
        amount = _safe_decimal(txn.get("amount"))
        tx_type = TransactionType.CREDIT if amount >= 0 else TransactionType.DEBIT
        abs_amount = abs(amount)

        running_balance = running_balance + amount

        bt = BankTransaction(
            bank_account_iban=iban,
            transaction_date=_to_date(txn.get("date")),
            transaction_type=tx_type,
            amount=abs_amount,
            currency=currency,
            description=txn.get("description"),
            reference=txn.get("reference"),
            counterparty_name=txn.get("counterparty"),
            counterparty_iban=txn.get("counterparty_iban"),
            balance_after=running_balance,
            is_matched=False,
            source_document_id=document_id or None,
            freshness_status=freshness,
            verified_at=now if freshness == "verified" else None,
            data_source="extraction",
        )
        session.add(bt)
        saved += 1

    await session.flush()

    # Validate closing balance matches running total
    closing = _safe_decimal(data.get("closing_balance"))
    warnings = []
    if closing > 0 and abs(running_balance - closing) > Decimal("1"):
        warnings.append(
            f"Sold final calculat ({running_balance}) difera de "
            f"sold final din extras ({closing}). Diferenta: "
            f"{running_balance - closing}"
        )

    result = {
        "status": "saved",
        "entity_type": "bank_statement",
        "transactions_saved": saved,
        "iban": iban,
        "opening_balance": str(opening),
        "closing_balance_calculated": str(running_balance),
    }
    if warnings:
        result["warnings"] = warnings
    return result


async def _find_or_create_company(session, tax_id: str | None, name: str | None = None, role: str = "client") -> str | None:
    """Find company by tax_id. If not found and tax_id + name available, auto-create it."""
    if not tax_id:
        return None
    co = (await session.execute(
        select(Company).where(Company.tax_id == tax_id, Company.is_deleted == False)
    )).scalar_one_or_none()
    if co:
        return co.id

    # Auto-create company from extraction data
    if name:
        from clarifi.models.company import CompanyRole
        new_role = CompanyRole.SUPPLIER if role == "supplier" else CompanyRole.CLIENT
        new_co = Company(
            legal_name=name,
            tax_id=tax_id,
            role=new_role,
            name_variants=[name],
        )
        session.add(new_co)
        await session.flush()
        return new_co.id

    return None


async def _find_contract_by_ref(session, ref: str | None) -> str | None:
    if not ref:
        return None
    ct = (await session.execute(
        select(Contract).where(Contract.contract_number == ref, Contract.is_deleted == False)
    )).scalar_one_or_none()
    return ct.id if ct else None


def _to_date(value) -> date_type | None:
    """Convert string/date to date object. Returns None on failure instead of crashing."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date_type):
        return value
    if isinstance(value, str):
        try:
            return date_type.fromisoformat(value)
        except ValueError:
            return None
    return None


def _safe_decimal(value, default: Decimal = Decimal("0")) -> Decimal:
    """Convert value to Decimal safely. Returns default on failure."""
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default
