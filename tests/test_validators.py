"""Tests for extraction validators — Romanian format normalization."""

from clarifi.tools.validators import validate_and_normalize


# --- Date normalization ---

def test_date_ddmmyyyy_dot():
    data = {"issue_date": "15.03.2026", "due_date": "15.04.2026"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["issue_date"] == "2026-03-15"
    assert result["due_date"] == "2026-04-15"
    assert len(warnings) == 0


def test_date_ddmmyyyy_slash():
    data = {"issue_date": "15/03/2026", "due_date": "15/04/2026"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["issue_date"] == "2026-03-15"
    assert result["due_date"] == "2026-04-15"


def test_date_iso_passthrough():
    data = {"issue_date": "2026-03-15", "due_date": "2026-04-15"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["issue_date"] == "2026-03-15"
    assert result["due_date"] == "2026-04-15"


def test_date_invalid():
    data = {"issue_date": "not-a-date", "due_date": "2026-04-15"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert len(warnings) == 1
    assert "unrecognized date format" in warnings[0]


def test_date_none_passthrough():
    data = {"issue_date": None, "due_date": "2026-04-15"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["issue_date"] is None


# --- Amount normalization ---

def test_amount_romanian_format():
    """1.234,56 (dot=thousands, comma=decimal) → 1234.56"""
    data = {"total_amount": "1.234,56", "subtotal": "1.037,44", "vat_amount": "197,12"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["total_amount"] == 1234.56
    assert result["subtotal"] == 1037.44
    assert result["vat_amount"] == 197.12


def test_amount_comma_decimal_only():
    """1234,56 (no thousands separator) → 1234.56"""
    data = {"total_amount": "15000,00", "subtotal": "12605,04", "vat_amount": "2394,96"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["total_amount"] == 15000.0
    assert result["subtotal"] == 12605.04


def test_amount_with_currency_suffix():
    data = {"total_amount": "15.000 lei", "subtotal": "12.605,04 RON", "vat_amount": "2394.96"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["total_amount"] == 15000.0
    assert result["subtotal"] == 12605.04


def test_amount_numeric_passthrough():
    data = {"total_amount": 15000.0, "subtotal": 12605.04, "vat_amount": 2394.96}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["total_amount"] == 15000.0


def test_amount_integer():
    data = {"total_amount": 15000, "subtotal": 12605, "vat_amount": 2395}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["total_amount"] == 15000.0


# --- CUI validation ---

def test_cui_valid_with_ro():
    data = {"vendor_or_client_tax_id": "RO12345678"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["vendor_or_client_tax_id"] == "RO12345678"
    assert len(warnings) == 0


def test_cui_without_ro():
    data = {"vendor_or_client_tax_id": "12345678"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["vendor_or_client_tax_id"] == "RO12345678"


def test_cui_with_prefix():
    data = {"vendor_or_client_tax_id": "CUI: RO87654321"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert result["vendor_or_client_tax_id"] == "RO87654321"


def test_cui_invalid():
    data = {"vendor_or_client_tax_id": "abc"}
    result, warnings = validate_and_normalize(data, "invoice")
    assert len(warnings) == 1
    assert "invalid" in warnings[0].lower() or "no digits" in warnings[0].lower()


# --- Amount consistency ---

def test_amount_consistency_ok():
    data = {"total_amount": 15000.0, "subtotal": 12605.04, "vat_amount": 2394.96}
    result, warnings = validate_and_normalize(data, "invoice")
    amount_warnings = [w for w in warnings if "mismatch" in w.lower()]
    assert len(amount_warnings) == 0


def test_amount_consistency_mismatch():
    data = {"total_amount": 15000.0, "subtotal": 10000.0, "vat_amount": 2000.0}
    result, warnings = validate_and_normalize(data, "invoice")
    amount_warnings = [w for w in warnings if "mismatch" in w.lower()]
    assert len(amount_warnings) == 1


# --- Contract milestones normalization ---

def test_contract_milestones_dates():
    data = {
        "contract_number": "CTR-001",
        "total_value": "150.000,00",
        "milestones": [
            {"name": "Phase 1", "due_date": "15.10.2025", "amount": "30.000"},
            {"name": "Phase 2", "due_date": "15.01.2026", "amount": "45.000,00"},
        ],
    }
    result, warnings = validate_and_normalize(data, "contract")
    assert result["total_value"] == 150000.0
    assert result["milestones"][0]["due_date"] == "2025-10-15"
    assert result["milestones"][1]["amount"] == 45000.0


# --- Bank statement transactions normalization ---

def test_bank_statement_transactions():
    data = {
        "opening_balance": "120.000,00",
        "closing_balance": "87.000,00",
        "transactions": [
            {"date": "03.01.2026", "amount": "-6.000,00"},
            {"date": "15.01.2026", "amount": "25.000,00"},
        ],
    }
    result, warnings = validate_and_normalize(data, "bank_statement")
    assert result["opening_balance"] == 120000.0
    assert result["closing_balance"] == 87000.0
    assert result["transactions"][0]["date"] == "2026-01-03"
    assert result["transactions"][0]["amount"] == -6000.0
    assert result["transactions"][1]["amount"] == 25000.0
