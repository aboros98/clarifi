# Facturi & Plăți

## Keywords
factură, facturi, factura, invoices, invoice, emis, primit, plătit, paid, încasat, neîncasat, lista, list, arată, show

## Tools
- query_invoices
- mark_invoice_paid
- query_transactions

## Instrucțiuni
When the user asks about invoices, payments, or transactions:

1. To list invoices: call `query_invoices(direction, status, limit)`
   - direction: "issued" (emise), "received" (primite), or "all"
   - status: "paid", "unpaid", "overdue", or "all"
2. To mark as paid: call `mark_invoice_paid(invoice_id, amount_paid)`
   - If user says "am încasat factura X", find the invoice first then mark paid
3. To see bank transactions: call `query_transactions(days, limit)`

## Format răspuns
Show invoices as a clean list with key info: number, client, amount, status, date.
Group by status when showing mixed results.

## Exemplu
User: "Arată-mi toate facturile emise"
Good response: "Ai 9 facturi emise:

✅ **Plătite (5):**
- INV-2025-009 TechCorp — 30.000 lei (31.07.2025)
- INV-2026-001 TechCorp — 30.000 lei (20.10.2025)
- INV-2026-002 TechCorp — 45.000 lei (20.01.2026)
- INV-2026-003 RetailPlus — 25.000 lei (01.12.2025)
- INV-2026-004 RetailPlus — 25.000 lei (15.01.2026)

🔴 **Restante (3):**
- INV-2026-005 RetailPlus — 25.000 lei (scadentă 22.03.2026)
- INV-2026-006 StartupVibe — 15.000 lei (scadentă 16.02.2026)
- INV-2026-007 StartupVibe — 15.000 lei (scadentă 16.03.2026)

📤 **Trimise (1):**
- INV-2026-008 TechCorp — 15.000 lei (scadentă 15.04.2026)"
