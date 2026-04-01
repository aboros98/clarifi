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

## Exemplu
User: "Ce proiecte sunt pe pierdere?"
Good response: "Profitabilitate per proiect (costuri facturate, fără salarii):

🟢 SEO TechCorp: +30.000 lei (marjă 100%)
🟢 Website TechCorp: +55.000 lei (marjă 73%)
🔴 **Mobile RetailPlus: -750 lei (marjă -1%, buget folosit 92%)**
🟡 CRM StartupVibe: +0 lei (marjă 0% — dar facturile nu sunt încasate)

⚠️ Proiectul Mobile App e aproape de pierdere. Verifică costurile suplimentare cu freelancerul."
