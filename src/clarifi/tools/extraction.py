"""Extragere structurată — extrage câmpuri din textul documentelor folosind LLM.

Prompt în română cu exemple few-shot din documente reale românești.
Validare Pydantic pe output pentru a garanta structura corectă.
"""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from pydantic import BaseModel

from clarifi.llm import get_llm

logger = logging.getLogger(__name__)

# --- Pydantic schemas for validation ---

class ExtractedInvoice(BaseModel):
    document_type: str = "invoice"
    invoice_number: str | None = None
    vendor_or_client_name: str | None = None
    vendor_or_client_tax_id: str | None = None
    issue_date: str | None = None
    due_date: str | None = None
    subtotal: float | None = None
    vat_amount: float | None = None
    total_amount: float | None = None
    currency: str = "RON"
    is_incoming: bool | None = None
    contract_reference: str | None = None
    payment_reference: str | None = None
    line_items: list[dict] = []
    field_confidences: dict = {}

class ExtractedContract(BaseModel):
    document_type: str = "contract"
    contract_number: str | None = None
    client_name: str | None = None
    client_tax_id: str | None = None
    total_value: float | None = None
    currency: str = "RON"
    start_date: str | None = None
    end_date: str | None = None
    payment_terms: str | None = None
    payment_terms_days: int | None = None
    billing_frequency: str | None = None
    milestones: list[dict] = []
    penalties: list[str] = []
    obligations: list[str] = []
    field_confidences: dict = {}

class ExtractedBankStatement(BaseModel):
    document_type: str = "bank_statement"
    bank_name: str | None = None
    account_iban: str | None = None
    statement_period_start: str | None = None
    statement_period_end: str | None = None
    opening_balance: float | None = None
    closing_balance: float | None = None
    currency: str = "RON"
    transactions: list[dict] = []
    field_confidences: dict = {}

class ExtractedEstimate(BaseModel):
    document_type: str = "estimate"
    estimate_number: str | None = None
    client_name: str | None = None
    client_tax_id: str | None = None
    issue_date: str | None = None
    valid_until: str | None = None
    subtotal: float | None = None
    vat_amount: float | None = None
    total_amount: float | None = None
    currency: str = "RON"
    line_items: list[dict] = []
    field_confidences: dict = {}

SCHEMAS = {
    "invoice": ExtractedInvoice,
    "contract": ExtractedContract,
    "bank_statement": ExtractedBankStatement,
    "estimate": ExtractedEstimate,
}


EXTRACTION_PROMPT = """Ești un motor de extragere de date din documente românești.

Extrage TOATE câmpurile structurate din următorul document de tip {doc_type}.
Documentul este în limba română. Context:
- Moneda este de obicei RON (lei) dacă nu se specifică altfel
- TVA: cota standard 19%
- CUI/CIF = cod de identificare fiscală (ex: RO12345678)
- Nr. Reg. Com. = numărul de la Registrul Comerțului (ex: J40/1234/2020)
- Formatul datei: DD.MM.YYYY — CONVERTEȘTE întotdeauna la YYYY-MM-DD în output
- Sumele pot avea format românesc: "1.234,56" (punct=mii, virgulă=zecimale) — convertește la număr: 1234.56

Pentru FIECARE câmp, dă un scor de încredere (0.0-1.0) în dicționarul 'field_confidences'.
Dacă un câmp lipsește sau e neclar, pune null și încredere 0.0.

Returnează un obiect JSON valid. NU include markdown, code blocks sau text suplimentar.

{schema_instructions}

### Exemplu factură reală:
Input: "FACTURA FISCALA Nr. DS-2026-042 / Data: 15.03.2026 / Furnizor: SC Digital Solutions SRL, CUI: RO12345678 / Client: SC TechCorp SA, CUI: RO87654321 / Servicii consultanta IT: 12.605,04 lei / TVA 19%: 2.394,96 lei / TOTAL: 15.000,00 lei / Scadenta: 15.04.2026 / Ref. contract: CTR-2025-001"
Output: {{"document_type":"invoice","invoice_number":"DS-2026-042","vendor_or_client_name":"SC TechCorp SA","vendor_or_client_tax_id":"RO87654321","issue_date":"2026-03-15","due_date":"2026-04-15","subtotal":12605.04,"vat_amount":2394.96,"total_amount":15000.0,"currency":"RON","is_incoming":false,"contract_reference":"CTR-2025-001","line_items":[{{"description":"Servicii consultanta IT","quantity":1,"unit_price":12605.04,"amount":12605.04}}],"field_confidences":{{"invoice_number":0.99,"total_amount":0.99,"due_date":0.99,"vendor_or_client_name":0.99}}}}

### Exemplu contract real:
Input: "CONTRACT DE PRESTARI SERVICII Nr. CTR-2025-001 / Între: SC Digital Solutions SRL (Prestator) și SC TechCorp SA, CUI RO87654321 (Beneficiar) / Obiect: Redesign website / Valoare: 150.000 lei + TVA / Perioada: 01.09.2025 - 30.06.2026 / Plata: Net 30 zile / Etapa 1: Design - 15.10.2025 - 30.000 lei / Etapa 2: Frontend - 15.01.2026 - 45.000 lei / Penalizare: 0.1%/zi întârziere"
Output: {{"document_type":"contract","contract_number":"CTR-2025-001","client_name":"SC TechCorp SA","client_tax_id":"RO87654321","total_value":150000.0,"currency":"RON","start_date":"2025-09-01","end_date":"2026-06-30","payment_terms":"Net 30 zile","payment_terms_days":30,"milestones":[{{"name":"Design","due_date":"2025-10-15","amount":30000.0}},{{"name":"Frontend","due_date":"2026-01-15","amount":45000.0}}],"penalties":["0.1% pe zi de întârziere"],"field_confidences":{{"contract_number":0.99,"total_value":0.99,"client_name":0.99}}}}

--- Document de procesat ---
{text}"""

SCHEMA_INSTRUCTIONS = {
    "invoice": """Câmpuri pentru FACTURĂ:
invoice_number, vendor_or_client_name, vendor_or_client_tax_id, issue_date (YYYY-MM-DD), due_date (YYYY-MM-DD), subtotal, vat_amount, total_amount, currency, is_incoming (true dacă noi primim factura, false dacă noi emitem), contract_reference, payment_reference, line_items [{description, quantity, unit_price, amount}], field_confidences""",

    "contract": """Câmpuri pentru CONTRACT:
contract_number, client_name, client_tax_id, total_value, currency, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), payment_terms, payment_terms_days, billing_frequency, milestones [{name, due_date, amount}], penalties [...], obligations [...], field_confidences""",

    "bank_statement": """Câmpuri pentru EXTRAS DE CONT:
bank_name, account_iban, statement_period_start (YYYY-MM-DD), statement_period_end (YYYY-MM-DD), opening_balance, closing_balance, currency, transactions [{date (YYYY-MM-DD), description, amount (pozitiv=intrare, negativ=ieșire), reference, counterparty}], field_confidences""",

    "estimate": """Câmpuri pentru DEVIZ/OFERTĂ:
estimate_number, client_name, client_tax_id, issue_date, valid_until, total_amount, currency, line_items [{description, quantity, unit_price, amount}], field_confidences""",
}


CLASSIFY_PROMPT = """Clasifică acest document ca exact unul din: invoice, contract, bank_statement, estimate.
Răspunde DOAR cu numele tipului, nimic altceva.

Text (primele 1500 caractere):
{text}"""


@tool
async def extract_fields(text: str, document_type: str = "auto") -> dict:
    """Extrage câmpuri structurate din textul unui document folosind LLM.
    Args:
        text — textul brut din documentul parsat (de la ingest_document)
        document_type — 'invoice', 'contract', 'bank_statement', sau 'auto' pentru detectare
    Returnează câmpurile extrase ca dict cu scoruri de încredere."""

    if not text or len(text.strip()) < 20:
        return {"error": "Textul e prea scurt pentru extragere"}

    from clarifi.config import settings
    llm = get_llm(settings.llm_extraction_model)

    # Auto-detectare tip document
    if document_type == "auto":
        classify_response = await llm.ainvoke([
            HumanMessage(content=CLASSIFY_PROMPT.format(text=text[:1500]))
        ])
        document_type = classify_response.content.strip().lower()
        if document_type not in SCHEMAS:
            document_type = "invoice"

    # Construiește prompt cu instrucțiuni specifice tipului
    schema_instr = SCHEMA_INSTRUCTIONS.get(document_type, SCHEMA_INSTRUCTIONS["invoice"])
    # 16k tokens ≈ 48k chars for Romanian text (~3 chars/token)
    max_chars = 48000
    was_truncated = len(text) > max_chars

    prompt = EXTRACTION_PROMPT.format(
        doc_type=document_type,
        schema_instructions=schema_instr,
        text=text[:max_chars],
    )

    response = await llm.ainvoke([
        SystemMessage(content="Ești un motor precis de extragere de date. Returnează DOAR JSON valid."),
        HumanMessage(content=prompt),
    ])

    # Parsează răspunsul — handle string and list-of-parts format
    raw_content = response.content
    if isinstance(raw_content, list):
        content = " ".join(
            p["text"] if isinstance(p, dict) and p.get("text") else str(p)
            for p in raw_content
        )
    else:
        content = str(raw_content)
    content = content.strip()

    # Strip markdown code blocks (```json ... ```)
    import re as _re
    md_match = _re.search(r"```(?:json)?\s*\n?(.*?)```", content, _re.DOTALL)
    if md_match:
        content = md_match.group(1).strip()
    elif content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        brace_start = content.find("{")
        brace_end = content.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            try:
                raw = json.loads(content[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                return {
                    "error": "Nu am putut parsa răspunsul LLM ca JSON",
                    "raw_response": content[:2000],
                    "document_type": document_type,
                }
        else:
            return {
                "error": "Nu am putut parsa răspunsul LLM ca JSON",
                "raw_response": content[:2000],
                "document_type": document_type,
            }

    # Validare Pydantic — normalizează și completează câmpuri lipsă
    schema_cls = SCHEMAS.get(document_type)
    if schema_cls:
        try:
            validated = schema_cls.model_validate(raw)
            extracted = validated.model_dump()
        except Exception as e:
            logger.warning("Validare Pydantic eșuată: %s — folosesc datele brute", e)
            extracted = raw
    else:
        extracted = raw

    # Coerce critical fields to prevent DB type errors
    for str_field in ("invoice_number", "contract_number", "vendor_or_client_name", "vendor_or_client_tax_id", "bank_name", "account_iban"):
        if str_field in extracted and extracted[str_field] is not None:
            extracted[str_field] = str(extracted[str_field])
    for num_field in ("total_amount", "vat_amount", "subtotal", "total_value", "opening_balance", "closing_balance"):
        if num_field in extracted and extracted[num_field] is not None:
            try:
                extracted[num_field] = float(extracted[num_field])
            except (TypeError, ValueError):
                extracted[num_field] = None

    # Calculează încrederea medie (flatten nested dicts from LLM)
    field_confs = extracted.get("field_confidences", {})
    flat_values = []
    for v in (field_confs.values() if field_confs else []):
        if isinstance(v, (int, float)):
            flat_values.append(float(v))
        elif isinstance(v, dict):
            flat_values.extend(
                float(x) for x in v.values() if isinstance(x, (int, float))
            )
    avg_confidence = sum(flat_values) / len(flat_values) if flat_values else 0.5

    # --- Pass 2: LLM Review — validate extraction + find insights ---
    review_result = await _review_extraction(
        llm, text[:8000], document_type, extracted,
    )
    if review_result and isinstance(review_result, dict):
        try:
            corrections = review_result.get("corrections", {})
            if isinstance(corrections, dict):
                for field, value in corrections.items():
                    if field in extracted and value is not None:
                        extracted[field] = value
                        logger.info("Review corrected %s.%s", document_type, field)
        except Exception:
            logger.warning("Failed to apply review corrections", exc_info=True)

    extracted["_meta"] = {
        "document_type": document_type,
        "avg_confidence": avg_confidence,
        "fields_extracted": len([
            v for v in extracted.values()
            if v is not None and v != "" and v != []
        ]),
        "text_truncated": was_truncated,
        "text_length": len(text),
        "validated": schema_cls is not None,
        "review_passed": review_result.get("valid", True) if review_result else None,
        "review_issues": review_result.get("issues", []) if review_result else [],
        "suggested_reminders": review_result.get("reminders", []) if review_result else [],
    }

    return extracted


REVIEW_PROMPT = """Ești un auditor financiar care verifică date extrase automat dintr-un document.

Document original (primele caractere):
{original_text}

Date extrase ({doc_type}):
{extracted_json}

Verifică:
1. Numerele au sens? (total = subtotal + TVA, sumele sunt rezonabile)
2. Datele sunt logice? (scadența e DUPĂ emitere, perioada nu e în viitor extrem)
3. CUI-ul e valid? (format RO + cifre)
4. Direcția facturii (is_incoming) e corectă?
5. Ce remindere inteligente ar trebui create?

Returnează DOAR JSON valid:
{{
  "valid": true/false,
  "issues": ["problema 1", "problema 2"],
  "corrections": {{"field_name": "corrected_value"}},
  "reminders": [
    {{"title": "Scadenta factura X", "when": "YYYY-MM-DD", "priority": "high/medium/low", "message": "ce sa verifice"}},
    {{"title": "Reminder 1 sapt inainte", "when": "YYYY-MM-DD", "priority": "medium", "message": "..."}}
  ]
}}

Reguli pentru remindere:
- DOAR date VIITOARE — nu crea remindere cu date din trecut
- Factura cu scadenta viitoare → "Verifica plata factura [nr] de la [client] — [suma] lei"
- Contract cu milestone viitor → "Milestone [nume] din contractul [nr] scadent"
- Contract care expira → "Contractul [nr] cu [client] expira — [suma] lei"
- FARA remindere generice ca "verificare manuala"
- FARA remindere daca nu ai date concrete (numar, suma, client)
- Pentru extrase bancare: nu crea remindere"""


async def _review_extraction(
    llm, original_text: str, doc_type: str, extracted: dict,
) -> dict | None:
    """Second LLM pass: validate extraction and suggest reminders."""
    try:
        # Remove _meta and field_confidences for cleaner review
        clean = {
            k: v for k, v in extracted.items()
            if k not in ("_meta", "field_confidences")
        }

        response = await llm.ainvoke([
            SystemMessage(
                content="Ești un auditor financiar precis. Returnezi DOAR JSON.",
            ),
            HumanMessage(content=REVIEW_PROMPT.format(
                original_text=original_text,
                doc_type=doc_type,
                extracted_json=json.dumps(clean, ensure_ascii=False, indent=2),
            )),
        ])

        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]

        return json.loads(content.strip())
    except Exception:
        logger.warning("Extraction review failed", exc_info=True)
        return None
