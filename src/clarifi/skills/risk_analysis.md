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

## Exemplu
User: "Ce riscuri am?"
Good response: "Nivel general de risc: 🔴 **RIDICAT**

**Risc Financiar:**
- Cashflow devine negativ pe 15.05.2026 dacă nu se încasează facturile restante
- Impact: -12.000 lei proiectat

**Risc Clienți:**
- StartupVibe: scor risc 72/100 — 30.000 lei restanți, medie 24 zile întârziere
- RetailPlus: scor risc 35/100 — 25.000 lei restanți, 4 zile întârziere

**Risc Contractual:**
- Milestone 'Backend Dev' depășit cu 4 zile (contract TechCorp, risc penalizare 0.1%/zi)
- 1 factură neemisă pentru milestone finalizat

**Risc Proiecte:**
- Mobile App RetailPlus: marjă -1%, buget folosit 92%

**Acțiuni recomandate:**
1. Contactează StartupVibe azi pentru un plan de plată
2. Finalizează milestone Backend Dev (risc penalizare)
3. Emite factura pentru milestone-ul completat dar nefacturat"
