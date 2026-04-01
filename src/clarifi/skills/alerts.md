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

## Exemplu flux
User: "Ce alerte am?"
1. Apelezi `query_alerts()` — OBLIGATORIU
2. Prezinți sumar: "Ai X alerte (Y critice)"
3. Listezi pe severitate: 🔴 critice → 🟡 avertismente → ℹ️ info
4. Grupezi alertele legate (ex: mai multe facturi de la același client)
5. Închei cu "Ce vrei să rezolvăm mai întâi?"
