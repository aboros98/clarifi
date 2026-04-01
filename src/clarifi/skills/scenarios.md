# Scenarii & Simulări (What-If)

## Keywords
dacă, what if, simulare, scenario, angajez, hire, cresc, grow, scad, reduce, impact, proiecție

## Tools
- query_cashflow
- query_profitability

## Instrucțiuni
When the user asks "what if" questions:

1. Call `query_cashflow()` to get the current financial baseline
2. Based on the scenario described, calculate the impact:
   - "Dacă angajez" → ask for gross salary if not given ("Care e salariul brut propus?"), then calculate total cost
   - "Dacă client X nu plătește" → subtract their outstanding amount from inflows
   - "Dacă accept proiect nou" → ask for estimated value and costs if not given
3. Present the before/after comparison with EXPLICIT math

IMPORTANT:
- Show your calculation step by step
- Use ONLY tool data as the baseline — never invent current figures
- If the user doesn't provide a key number (salary, project value), ASK instead of estimating
- Round to whole lei (no decimals)

## Romanian Salary Context
- Gross salary = Net + Income Tax (10%) + CAS (25%) + CASS (10%)
- For employer: total cost ≈ gross × 1.0225 (2.25% CAM contribution)
- Example: 5.000 lei net → ~7.200 lei brut → ~7.362 lei cost total companie

## Exemplu flux
User: "Dacă angajez un developer la 8.000 lei brut?"
1. Apelezi `query_cashflow()` pentru baseline real — OBLIGATORIU, nu inventa cifre
2. Calculezi costul angajării (brut × 1.0225 CAM)
3. Prezinți: Situație actuală → Cost nou → Impact pe burn rate/runway
4. Arată matematica pas cu pas
5. Dacă lipsește salariul brut, ÎNTREABĂ (nu estima)
