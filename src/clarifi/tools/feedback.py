"""User feedback tools: confirm, correct, mark stale, check freshness."""

from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.config import settings
from clarifi.db.session import get_async_session
from clarifi.models.contract import Contract
from clarifi.models.invoice import Invoice


@tool
async def confirm_data(entity_type: str, entity_id: str) -> dict:
    """Mark extracted data as confirmed/verified by the user.
    Args: entity_type — 'invoice' or 'contract'; entity_id — the entity's ID."""
    now = datetime.now(timezone.utc)
    model = _resolve_model(entity_type)
    if not model:
        return {"error": f"Unknown entity type: {entity_type}"}

    async with get_async_session() as session:
        entity = await session.get(model, entity_id)
        if not entity:
            return {"error": f"{entity_type} {entity_id} not found"}
        entity.verified_at = now
        entity.verified_by = "user"
        entity.freshness_status = "verified"
    return {"status": "confirmed", "entity_type": entity_type, "id": entity_id}


@tool
async def correct_data(entity_type: str, entity_id: str, corrections: dict) -> dict:
    """Apply user corrections to extracted data. Updates the specified fields.
    Args: entity_type, entity_id, corrections — dict of {field_name: new_value}."""
    now = datetime.now(timezone.utc)
    model = _resolve_model(entity_type)
    if not model:
        return {"error": f"Unknown entity type: {entity_type}"}

    async with get_async_session() as session:
        entity = await session.get(model, entity_id)
        if not entity:
            return {"error": f"{entity_type} {entity_id} not found"}

        # Whitelist: only allow correcting data fields, not internal ones
        blocked_fields = {
            "id", "is_deleted", "deleted_at", "deleted_by",
            "created_at", "created_by", "updated_at", "updated_by",
            "verified_at", "verified_by", "freshness_status", "data_source",
            "source_document_id", "extraction_confidence", "extraction_notes",
        }
        applied = []
        for field, value in corrections.items():
            if field in blocked_fields:
                continue
            if hasattr(entity, field):
                # Type-coerce values to match column types
                value = _coerce_value(entity, field, value)
                setattr(entity, field, value)
                applied.append(field)

        entity.verified_at = now
        entity.verified_by = "user"
        entity.freshness_status = "verified"

    return {"status": "corrected", "fields_updated": applied, "entity_type": entity_type, "id": entity_id}


@tool
async def mark_stale(entity_type: str, entity_id: str, reason: str) -> dict:
    """Mark data as stale/outdated. Use when user says data is no longer accurate.
    Args: entity_type, entity_id, reason — why the data is stale."""
    model = _resolve_model(entity_type)
    if not model:
        return {"error": f"Unknown entity type: {entity_type}"}

    async with get_async_session() as session:
        entity = await session.get(model, entity_id)
        if not entity:
            return {"error": f"{entity_type} {entity_id} not found"}
        entity.freshness_status = "stale"
        entity.extraction_notes = f"Marked stale: {reason}"

    return {"status": "marked_stale", "entity_type": entity_type, "id": entity_id}


@tool
async def check_freshness() -> dict:
    """Check for data that needs user verification — unverified extractions, stale bank data, old overdue invoices.
    Returns items grouped by urgency."""
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(days=settings.freshness_unverified_days)
    items = []

    async with get_async_session() as session:
        # Unverified invoices older than threshold
        unverified_q = select(Invoice).where(
            Invoice.freshness_status == "unverified",
            Invoice.created_at < threshold,
            Invoice.is_deleted == False,
        )
        for inv in (await session.execute(unverified_q)).scalars().all():
            items.append({
                "type": "unverified_invoice",
                "urgency": "medium",
                "message": f"Factura #{inv.invoice_number} ({inv.total_amount} {inv.currency}) neconfirmată de {settings.freshness_unverified_days}+ zile",
                "entity_type": "invoice",
                "entity_id": str(inv.id),
            })

        # Stale items
        stale_q = select(Invoice).where(Invoice.freshness_status == "stale", Invoice.is_deleted == False)
        for inv in (await session.execute(stale_q)).scalars().all():
            items.append({
                "type": "stale_data",
                "urgency": "high",
                "message": f"Factura #{inv.invoice_number} marcată ca depășită",
                "entity_type": "invoice",
                "entity_id": str(inv.id),
            })

    return {"items": items, "count": len(items)}


def _resolve_model(entity_type: str):
    mapping = {"invoice": Invoice, "contract": Contract}
    return mapping.get(entity_type)


def _coerce_value(entity, field: str, value):
    """Coerce a correction value to match the column type."""
    from datetime import date as date_type
    from decimal import Decimal

    current = getattr(entity, field, None)
    if isinstance(current, date_type) and isinstance(value, str):
        try:
            return date_type.fromisoformat(value)
        except ValueError:
            return current
    if isinstance(current, Decimal) and not isinstance(value, Decimal):
        try:
            return Decimal(str(value))
        except Exception:
            return current
    return value
