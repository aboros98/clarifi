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

## Exemplu flux
User: "Arată-mi toate facturile emise"
1. Apelezi `query_invoices(direction="issued", status="all")` — OBLIGATORIU
2. Grupezi pe status: Plătite → Restante → Trimise/Neplătite
3. Pentru fiecare: număr, client, sumă, dată
4. Marchezi restantele cu 🔴
