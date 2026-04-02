# Emitere Facturi

## Keywords
emite, factura, facturare, emit, invoice, genereaza, creeaza factura, factura noua

## Tools
- emit_invoice
- search_data
- query_contracts
- calculate
- create_reminder

## Instructiuni
Cand utilizatorul vrea sa emita o factura:

1. Colecteaza informatiile OBLIGATORII (intreaba daca lipsesc):
   - Client (nume sau CUI)
   - Servicii/produse cu cantitate si pret unitar
   - Termen de plata (default 30 zile)

2. Calculeaza sumele cu `calculate()`:
   - Subtotal = suma(cantitate x pret_unitar)
   - TVA = subtotal x 19%
   - Total = subtotal + TVA

3. Confirma cu utilizatorul INAINTE de a emite:
   - "Factura pentru [client]: [total] lei (din care TVA [vat] lei), scadenta [data]. Emit?"

4. Dupa confirmare, apeleaza `emit_invoice()`

5. Dupa emitere:
   - Creeaza reminder pe data scadentei
   - Spune numarul facturii generate

## Exemplu flux
User: "Emite o factura de 5000 lei pentru RebelDot pentru consultanta"
1. Calculeaza: subtotal=4201.68, TVA=798.32, total=5000 (sau subtotal=5000, TVA=950, total=5950 — intreaba!)
2. Intreaba: "5000 lei e suma cu sau fara TVA?"
3. Dupa raspuns, confirma detaliile
4. Emite si comunica numarul

## IMPORTANT
- INTOTDEAUNA intreaba daca suma include TVA sau nu
- INTOTDEAUNA confirma inainte de a emite
- Daca utilizatorul mentioneaza un contract, cauta-l cu search_data si leaga factura
