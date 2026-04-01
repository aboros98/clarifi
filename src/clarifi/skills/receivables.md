# Facturi de Încasat (Receivables)

## Keywords
datorează, restanță, restante, neîncasat, neîncasate, overdue, receivable, facturi, plată, întârziere, cine, who owes, unpaid, aging

## Tools
- query_receivables

## Instrucțiuni
Când utilizatorul întreabă despre bani datorați, facturi neîncasate sau plăți întârziate:

1. Apelează `query_receivables()` — returnează totalul, facturile pe intervale de întârziere
2. Prezintă suma totală restantă
3. Grupează pe intervale: la termen, 1-30 zile, 31-60 zile, 60+ zile
4. Pentru facturile 60+ zile, sugerează acțiuni concrete
5. Dacă utilizatorul întreabă de un client specific, filtrează în răspuns

## Format răspuns
- Începe cu totalul: "Ai **X lei** de încasat"
- Grupează pe client dacă sunt mai multe facturi de la același client
- Marchează elementele critice (>30 zile) cu ⚠️
- Sugerează acțiuni: sună clientul, trimite reminder, escaladează

## Exemplu
Utilizator: "Cine îmi datorează bani?"
Răspuns bun: "Total de încasat: **70.000 lei** din 4 facturi.

🔴 **Restanțe critice:**
- StartupVibe: 30.000 lei (2 facturi, 10-38 zile întârziere)
- RetailPlus: 25.000 lei (1 factură, 4 zile întârziere)

🟢 **La termen:**
- TechCorp: 15.000 lei (scadentă 15.04.2026)

Recomand: sună StartupVibe azi — au pattern de întârziere."
