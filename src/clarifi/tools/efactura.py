"""eFactura integration — generate ANAF-compliant XML and submit.

Romanian e-invoicing (eFactura) requires UBL 2.1 XML format
submitted to ANAF's SPV system.
"""

import logging
import xml.etree.ElementTree as ET
from datetime import date

from langchain_core.tools import tool
from sqlalchemy import select

from clarifi.agent.company_scope import get_user_company_ids
from clarifi.db.session import get_async_session
from clarifi.models.company import Company
from clarifi.models.invoice import Invoice, InvoiceLineItem

logger = logging.getLogger(__name__)

# UBL 2.1 namespaces
NS = {
    "": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


def _generate_efactura_xml(
    invoice: Invoice,
    issuer: Company,
    recipient: Company,
    line_items: list[InvoiceLineItem],
) -> str:
    """Generate UBL 2.1 XML for ANAF eFactura."""

    root = ET.Element("Invoice", xmlns=NS[""])
    root.set("xmlns:cac", NS["cac"])
    root.set("xmlns:cbc", NS["cbc"])

    # Header
    ET.SubElement(root, "{%s}CustomizationID" % NS["cbc"]).text = (
        "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"
    )
    ET.SubElement(root, "{%s}ID" % NS["cbc"]).text = invoice.invoice_number or "DRAFT"
    ET.SubElement(root, "{%s}IssueDate" % NS["cbc"]).text = (
        invoice.issue_date.isoformat() if invoice.issue_date else date.today().isoformat()
    )
    if invoice.due_date:
        ET.SubElement(root, "{%s}DueDate" % NS["cbc"]).text = invoice.due_date.isoformat()
    ET.SubElement(root, "{%s}InvoiceTypeCode" % NS["cbc"]).text = "380"  # Commercial invoice
    ET.SubElement(root, "{%s}DocumentCurrencyCode" % NS["cbc"]).text = invoice.currency or "RON"

    # Supplier (issuer)
    supplier = ET.SubElement(root, "{%s}AccountingSupplierParty" % NS["cac"])
    supplier_party = ET.SubElement(supplier, "{%s}Party" % NS["cac"])
    sp_id = ET.SubElement(supplier_party, "{%s}PartyIdentification" % NS["cac"])
    ET.SubElement(sp_id, "{%s}ID" % NS["cbc"]).text = issuer.tax_id or ""
    sp_name = ET.SubElement(supplier_party, "{%s}PartyName" % NS["cac"])
    ET.SubElement(sp_name, "{%s}Name" % NS["cbc"]).text = issuer.legal_name
    if issuer.address:
        sp_addr = ET.SubElement(supplier_party, "{%s}PostalAddress" % NS["cac"])
        ET.SubElement(sp_addr, "{%s}StreetName" % NS["cbc"]).text = issuer.address
        if issuer.city:
            ET.SubElement(sp_addr, "{%s}CityName" % NS["cbc"]).text = issuer.city
        country = ET.SubElement(sp_addr, "{%s}Country" % NS["cac"])
        ET.SubElement(country, "{%s}IdentificationCode" % NS["cbc"]).text = issuer.country_code or "RO"
    sp_tax = ET.SubElement(supplier_party, "{%s}PartyTaxScheme" % NS["cac"])
    ET.SubElement(sp_tax, "{%s}CompanyID" % NS["cbc"]).text = issuer.tax_id or ""
    tax_scheme = ET.SubElement(sp_tax, "{%s}TaxScheme" % NS["cac"])
    ET.SubElement(tax_scheme, "{%s}ID" % NS["cbc"]).text = "VAT"

    # Customer (recipient)
    customer = ET.SubElement(root, "{%s}AccountingCustomerParty" % NS["cac"])
    customer_party = ET.SubElement(customer, "{%s}Party" % NS["cac"])
    cp_id = ET.SubElement(customer_party, "{%s}PartyIdentification" % NS["cac"])
    ET.SubElement(cp_id, "{%s}ID" % NS["cbc"]).text = recipient.tax_id or ""
    cp_name = ET.SubElement(customer_party, "{%s}PartyName" % NS["cac"])
    ET.SubElement(cp_name, "{%s}Name" % NS["cbc"]).text = recipient.legal_name or ""

    # Tax total
    tax_total = ET.SubElement(root, "{%s}TaxTotal" % NS["cac"])
    tax_amount_el = ET.SubElement(tax_total, "{%s}TaxAmount" % NS["cbc"])
    tax_amount_el.set("currencyID", invoice.currency or "RON")
    tax_amount_el.text = str(float(invoice.vat_amount or 0))

    tax_subtotal = ET.SubElement(tax_total, "{%s}TaxSubtotal" % NS["cac"])
    taxable_el = ET.SubElement(tax_subtotal, "{%s}TaxableAmount" % NS["cbc"])
    taxable_el.set("currencyID", invoice.currency or "RON")
    taxable_el.text = str(float(invoice.subtotal or 0))
    sub_tax_el = ET.SubElement(tax_subtotal, "{%s}TaxAmount" % NS["cbc"])
    sub_tax_el.set("currencyID", invoice.currency or "RON")
    sub_tax_el.text = str(float(invoice.vat_amount or 0))
    tax_cat = ET.SubElement(tax_subtotal, "{%s}TaxCategory" % NS["cac"])
    ET.SubElement(tax_cat, "{%s}ID" % NS["cbc"]).text = "S"  # Standard rate
    ET.SubElement(tax_cat, "{%s}Percent" % NS["cbc"]).text = "19"
    cat_scheme = ET.SubElement(tax_cat, "{%s}TaxScheme" % NS["cac"])
    ET.SubElement(cat_scheme, "{%s}ID" % NS["cbc"]).text = "VAT"

    # Monetary totals
    monetary = ET.SubElement(root, "{%s}LegalMonetaryTotal" % NS["cac"])
    line_ext = ET.SubElement(monetary, "{%s}LineExtensionAmount" % NS["cbc"])
    line_ext.set("currencyID", invoice.currency or "RON")
    line_ext.text = str(float(invoice.subtotal or 0))
    tax_excl = ET.SubElement(monetary, "{%s}TaxExclusiveAmount" % NS["cbc"])
    tax_excl.set("currencyID", invoice.currency or "RON")
    tax_excl.text = str(float(invoice.subtotal or 0))
    tax_incl = ET.SubElement(monetary, "{%s}TaxInclusiveAmount" % NS["cbc"])
    tax_incl.set("currencyID", invoice.currency or "RON")
    tax_incl.text = str(float(invoice.total_amount or 0))
    payable = ET.SubElement(monetary, "{%s}PayableAmount" % NS["cbc"])
    payable.set("currencyID", invoice.currency or "RON")
    payable.text = str(float(invoice.total_amount or 0))

    # Line items
    for i, li in enumerate(line_items, 1):
        line = ET.SubElement(root, "{%s}InvoiceLine" % NS["cac"])
        ET.SubElement(line, "{%s}ID" % NS["cbc"]).text = str(i)
        qty_el = ET.SubElement(line, "{%s}InvoicedQuantity" % NS["cbc"])
        qty_el.set("unitCode", "EA")
        qty_el.text = str(float(li.quantity))
        line_amt = ET.SubElement(line, "{%s}LineExtensionAmount" % NS["cbc"])
        line_amt.set("currencyID", invoice.currency or "RON")
        line_amt.text = str(float(li.line_total))

        item = ET.SubElement(line, "{%s}Item" % NS["cac"])
        desc = li.description or "Serviciu"
        ET.SubElement(item, "{%s}Description" % NS["cbc"]).text = desc
        ET.SubElement(item, "{%s}Name" % NS["cbc"]).text = desc[:100]
        item_tax = ET.SubElement(item, "{%s}ClassifiedTaxCategory" % NS["cac"])
        ET.SubElement(item_tax, "{%s}ID" % NS["cbc"]).text = "S"
        ET.SubElement(item_tax, "{%s}Percent" % NS["cbc"]).text = "19"
        item_scheme = ET.SubElement(item_tax, "{%s}TaxScheme" % NS["cac"])
        ET.SubElement(item_scheme, "{%s}ID" % NS["cbc"]).text = "VAT"

        price = ET.SubElement(line, "{%s}Price" % NS["cac"])
        price_amt = ET.SubElement(price, "{%s}PriceAmount" % NS["cbc"])
        price_amt.set("currencyID", invoice.currency or "RON")
        price_amt.text = str(float(li.unit_price))

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


@tool
async def generate_efactura_xml(invoice_id: str) -> dict:
    """Genereaza XML eFactura (UBL 2.1) pentru o factura existenta.

    Args:
        invoice_id — ID-ul facturii

    Returneaza XML-ul generat, gata de trimis la ANAF.
    NOTA: Trimiterea efectiva la ANAF necesita integrare SPV separata.
    """
    company_ids = await get_user_company_ids()

    async with get_async_session() as session:
        inv = await session.get(Invoice, invoice_id)
        if not inv:
            return {"error": "Factura nu a fost gasita"}

        # Verify ownership
        if company_ids and (
            inv.issuer_company_id not in company_ids
            and inv.recipient_company_id not in company_ids
        ):
            return {"error": "Nu ai acces la aceasta factura"}

        issuer = await session.get(Company, inv.issuer_company_id)
        recipient = await session.get(Company, inv.recipient_company_id)

        if not issuer or not recipient:
            return {"error": "Compania emitenta sau destinatara nu a fost gasita"}

        # Get line items
        items = (await session.execute(
            select(InvoiceLineItem)
            .where(InvoiceLineItem.invoice_id == invoice_id)
            .order_by(InvoiceLineItem.line_number)
        )).scalars().all()

    try:
        xml = _generate_efactura_xml(inv, issuer, recipient, items)
    except Exception as e:
        logger.exception("eFactura XML generation failed")
        return {"error": f"Eroare la generare XML: {e}"}

    return {
        "status": "generated",
        "invoice_number": inv.invoice_number,
        "xml_length": len(xml),
        "xml": xml[:5000],  # First 5k chars for preview
        "note": "XML generat. Trimiterea la ANAF SPV necesita integrare separata.",
    }


@tool
async def lookup_anaf(tax_id: str) -> dict:
    """Verifica o companie pe ANAF — status TVA, stare firma.

    Args:
        tax_id — CUI-ul companiei (ex: "RO12345678")
    """
    import re

    # Clean CUI
    digits = re.sub(r"[^0-9]", "", tax_id)
    if not digits:
        return {"error": f"CUI invalid: {tax_id}"}

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://webservicesp.anaf.ro/PlatitorTvaRest/api/v8/ws/tva",
                json=[{"cui": int(digits), "data": date.today().isoformat()}],
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("found") and len(data["found"]) > 0:
                    info = data["found"][0]
                    return {
                        "tax_id": f"RO{digits}",
                        "name": info.get("denumire", ""),
                        "address": info.get("adresa", ""),
                        "vat_payer": info.get("scpTVA", False),
                        "active": not info.get("statusInactivi", False),
                        "split_vat": info.get("TVA_piata", False),
                    }
                return {"tax_id": f"RO{digits}", "error": "CUI negasit in baza ANAF"}
            return {"error": f"ANAF API error: {resp.status_code}"}
    except ImportError:
        return {"error": "httpx nu e instalat"}
    except Exception as e:
        return {"error": f"Eroare ANAF: {e}"}
