"""Post-extraction validators — normalize Romanian formats and validate data integrity."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def validate_and_normalize(data: dict, entity_type: str) -> tuple[dict, list[str]]:
    """Validate extracted data and normalize Romanian formats.

    Returns (normalized_data, list_of_warnings).
    Handles: DD.MM.YYYY dates, comma decimals, CUI format, amount consistency.
    """
    warnings: list[str] = []
    normalized = dict(data)

    # Normalize dates
    date_fields = _get_date_fields(entity_type)
    for field in date_fields:
        if field in normalized and normalized[field]:
            normalized[field], warn = _normalize_date(normalized[field], field)
            if warn:
                warnings.append(warn)

    # Normalize amounts
    amount_fields = _get_amount_fields(entity_type)
    for field in amount_fields:
        if field in normalized and normalized[field] is not None:
            normalized[field], warn = _normalize_amount(normalized[field], field)
            if warn:
                warnings.append(warn)

    # Validate CUI
    tax_field = _get_tax_id_field(entity_type)
    if tax_field and tax_field in normalized and normalized[tax_field]:
        normalized[tax_field], warn = _validate_cui(normalized[tax_field])
        if warn:
            warnings.append(warn)

    # Amount consistency check
    if entity_type == "invoice":
        warn = _check_invoice_amounts(normalized)
        if warn:
            warnings.append(warn)

    # Normalize nested data
    if entity_type == "contract" and "milestones" in normalized:
        for i, ms in enumerate(normalized.get("milestones", [])):
            if isinstance(ms, dict):
                if ms.get("due_date"):
                    ms["due_date"], _ = _normalize_date(ms["due_date"], f"milestone[{i}].due_date")
                if ms.get("amount"):
                    ms["amount"], _ = _normalize_amount(ms["amount"], f"milestone[{i}].amount")

    if entity_type == "bank_statement" and "transactions" in normalized:
        for i, txn in enumerate(normalized.get("transactions", [])):
            if isinstance(txn, dict):
                if txn.get("date"):
                    txn["date"], _ = _normalize_date(txn["date"], f"transaction[{i}].date")
                if txn.get("amount"):
                    txn["amount"], _ = _normalize_amount(txn["amount"], f"transaction[{i}].amount")

    return normalized, warnings


def _normalize_date(value, field_name: str) -> tuple[str | None, str | None]:
    """Convert DD.MM.YYYY or DD/MM/YYYY to YYYY-MM-DD. Pass through ISO dates."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10], None
    if not isinstance(value, str):
        return value, None

    value = value.strip()

    # Already ISO format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value, None

    # DD.MM.YYYY or DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$", value)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            d = date(year, month, day)
            return d.isoformat(), None
        except ValueError:
            return None, f"{field_name}: invalid date '{value}'"

    return value, f"{field_name}: unrecognized date format '{value}'"


def _normalize_amount(value, field_name: str) -> tuple[float | None, str | None]:
    """Normalize Romanian amount format: '1.234,56' → 1234.56."""
    if isinstance(value, (int, float, Decimal)):
        return float(value), None
    if not isinstance(value, str):
        return value, None

    value = value.strip().replace(" ", "")

    # Remove currency suffixes
    for suffix in ("lei", "LEI", "RON", "ron", "EUR", "eur", "€"):
        value = value.replace(suffix, "").strip()

    # Romanian format: 1.234,56 (dot=thousands, comma=decimal)
    if "," in value and "." in value:
        if value.rindex(",") > value.rindex("."):
            value = value.replace(".", "").replace(",", ".")

    # Dot-only as thousands separator: "15.000" (no comma, dot before 3 digits)
    # Distinguish from "15.50" (dot as decimal with <3 digits after)
    elif "." in value and "," not in value:
        parts = value.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            # "15.000" → thousands separator → remove dot
            value = value.replace(".", "")
        elif len(parts) > 2:
            # "1.234.567" → all dots are thousands separators
            value = value.replace(".", "")

    # Just comma as decimal: 1234,56
    elif "," in value and "." not in value:
        value = value.replace(",", ".")

    try:
        return float(Decimal(value)), None
    except (InvalidOperation, ValueError):
        return None, f"{field_name}: cannot parse amount '{value}'"


def _validate_cui(value: str) -> tuple[str, str | None]:
    """Validate Romanian CUI/CIF format. Normalize to RO + digits."""
    cleaned = value.strip().upper().replace(" ", "")
    # Remove common prefixes
    if cleaned.startswith("CUI:") or cleaned.startswith("CIF:"):
        cleaned = cleaned[4:].strip()

    # Should be RO + 1-13 digits, or just digits
    digits_only = re.sub(r"[^0-9]", "", cleaned)
    has_ro = cleaned.startswith("RO")

    if not digits_only:
        return value, f"CUI/CIF invalid: '{value}' (no digits found)"

    if len(digits_only) < 1 or len(digits_only) > 13:
        return value, f"CUI/CIF suspicious length: '{value}' ({len(digits_only)} digits)"

    normalized = f"RO{digits_only}" if not has_ro else f"RO{digits_only}"
    return normalized, None


def _check_invoice_amounts(data: dict) -> str | None:
    """Check: total ≈ subtotal + vat (within 1 lei tolerance)."""
    total = data.get("total_amount")
    subtotal = data.get("subtotal")
    vat = data.get("vat_amount")

    if total is None or subtotal is None or vat is None:
        return None

    try:
        t = float(total)
        s = float(subtotal)
        v = float(vat)
        if abs(t - (s + v)) > 1.0:
            return f"Amount mismatch: total ({t}) != subtotal ({s}) + vat ({v}). Difference: {t - s - v:.2f}"
    except (TypeError, ValueError):
        pass
    return None


def _get_date_fields(entity_type: str) -> list[str]:
    if entity_type == "invoice":
        return ["issue_date", "due_date"]
    elif entity_type == "contract":
        return ["start_date", "end_date", "contract_date"]
    elif entity_type == "bank_statement":
        return ["statement_period_start", "statement_period_end"]
    return []


def _get_amount_fields(entity_type: str) -> list[str]:
    if entity_type == "invoice":
        return ["total_amount", "subtotal", "vat_amount"]
    elif entity_type == "contract":
        return ["total_value"]
    elif entity_type == "bank_statement":
        return ["opening_balance", "closing_balance"]
    return []


def _get_tax_id_field(entity_type: str) -> str | None:
    if entity_type == "invoice":
        return "vendor_or_client_tax_id"
    elif entity_type == "contract":
        return "client_tax_id"
    return None
