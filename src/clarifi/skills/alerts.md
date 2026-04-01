# Alerte & Notificări

## Keywords
alertă, alerte, atenție, warning, problemă, urgență, ce trebuie, what needs, attention, issues

## Tools
- query_alerts
- detect_unissued_invoices
- project_cashflow_daily
- score_client_risk

## Instrucțiuni
When the user asks about alerts, problems, or what needs attention:

1. Call `query_alerts()` — returns all active alerts sorted by severity
2. Present critical items first, then warnings, then info
3. For each alert, suggest a concrete action
4. Group related alerts (e.g., multiple overdue invoices from same client)

## Format răspuns
- Start with summary: "Ai X alerte (Y critice)"
- Use 🔴 for critical, 🟡 for warning, ℹ️ for info
- End with "Ce vrei să rezolvăm mai întâi?"

## Exemplu
User: "Ce alerte am?"
Good response: "Ai **5 alerte** (2 critice, 3 avertismente):

🔴 Factura StartupVibe #INV-2026-006 — restantă 38 zile (15.000 lei)
🔴 Factura StartupVibe #INV-2026-007 — restantă 10 zile (15.000 lei)
🟡 Milestone 'Backend Dev' — depășit cu 4 zile (contract TechCorp)
🟡 Factura RetailPlus #INV-2026-005 — restantă 4 zile (25.000 lei)
🟡 Contract RetailPlus expiră în 66 zile

Ce vrei să rezolvăm mai întâi?"
