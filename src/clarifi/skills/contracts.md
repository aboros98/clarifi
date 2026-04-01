# Contracte & Obligații

## Keywords
contract, contracte, obligații, milestone, termen, scadență, penalitate, expirare, reînnoire, renewal

## Tools
- query_contracts
- query_milestones

## Instrucțiuni
When the user asks about contracts, milestones, or obligations:

1. Call `query_contracts()` for overview, or `query_contracts(status="expiring")` for soon-to-expire
2. Call `query_milestones()` for upcoming/overdue deliverables
3. Flag overdue milestones with penalty implications
4. Flag contracts expiring within 30 days

## Format răspuns
- List contracts with status, value, and key dates
- For milestones: show what's due, what's overdue, what's coming
- Mention penalty clauses if relevant
- Use DD.MM.YYYY for dates

## Exemplu
User: "Ce obligații contractuale am?"
Good response: "Ai 4 contracte active. Situație:

📋 **Milestone depășit:**
- Backend Dev (Website TechCorp) — scadent 30.03.2026, nefinalizat!
  ⚠️ Contractul are clauză de penalizare: 0,1%/zi din valoare

📅 **Milestone viitor:**
- Final Delivery (Website TechCorp) — 15.06.2026, 30.000 lei

📆 **Contracte cu expirare apropiată:**
- Mobile App RetailPlus — expiră 31.05.2026 (66 zile)"
