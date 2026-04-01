# Profitabilitate

## Keywords
profit, marjă, margin, pierdere, loss, profitabilitate, venituri, costuri, revenue, costs, buget, budget, deviere

## Tools
- query_profitability

## Instrucțiuni
When the user asks about profitability, margins, or project performance:

1. Call `query_profitability()` for global view, or `query_profitability(project_code="PRJ-001")` for a specific project
2. Show global margins first, then per-project breakdown
3. Flag projects with negative margins or >90% budget usage
4. Note that costs only include invoiced costs (not salaries — mention this caveat)

## Format răspuns
- Lead with global profit: "Profit total: **X lei** (marjă Y%)"
- List projects sorted worst-to-best margin
- Use 🟢 for healthy (>20% margin), 🟡 for thin (5-20%), 🔴 for loss (<5%)
- Mention budget usage where available

## Exemplu flux
User: "Ce proiecte sunt pe pierdere?"
1. Apelezi `query_profitability()` — OBLIGATORIU
2. Prezinți profitul global, apoi per proiect (sortat de la cel mai slab)
3. Folosești 🟢/🟡/🔴 pe baza marjei reale din tool
4. Menționezi că sunt doar costuri facturate, fără salarii
