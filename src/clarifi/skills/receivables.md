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

## Exemplu flux
Utilizator: "Cine îmi datorează bani?"
1. Apelezi `query_receivables()` — OBLIGATORIU
2. Prezinți totalul de încasat
3. Grupezi pe intervale de întârziere: critice (>30 zile) → avertismente → la termen
4. Grupezi facturile per client dacă au mai multe
5. Sugerezi acțiuni concrete pentru restanțe
