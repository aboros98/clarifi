# Analiză de Risc

## Keywords
risc, riscuri, riscant, risk, pericol, danger, probleme, issues, late, întârziere, buget depășit, over budget, client risk

## Tools
- score_client_risk
- detect_unissued_invoices
- project_cashflow_daily
- query_profitability
- query_alerts

## Instrucțiuni
When the user asks about risks:

1. Call `score_client_risk()` — which clients are risky (late payers)
2. Call `detect_unissued_invoices()` — invoices that should exist but don't
3. Call `project_cashflow_daily(days=60)` — check if cash goes negative
4. Call `query_profitability()` — find loss-making projects
5. Call `query_alerts()` — any critical alerts

Combine into a comprehensive risk assessment. If a tool returns no data for a category, skip that category — do NOT invent risks.

## Format răspuns
Start with overall risk level, then group by category with quantified impact.

## Exemplu flux
User: "Ce riscuri am?"
1. Apelezi TOATE tool-urile de risc în paralel: `score_client_risk()`, `detect_unissued_invoices()`, `project_cashflow_daily(days=60)`, `query_profitability()`, `query_alerts()`
2. Sintetizezi pe categorii: Financiar → Clienți → Contractual → Proiecte
3. Omite categoriile fără date (nu inventa riscuri)
4. Încheie cu 2-3 acțiuni concrete ordonate pe prioritate
