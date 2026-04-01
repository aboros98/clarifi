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

## Exemplu flux
User: "Ce obligații contractuale am?"
1. Apelezi `query_contracts()` + `query_milestones()` — OBLIGATORIU
2. Prezinți milestone-uri depășite (cu penalități dacă există)
3. Apoi milestone-uri viitoare
4. Apoi contracte care expiră curând
