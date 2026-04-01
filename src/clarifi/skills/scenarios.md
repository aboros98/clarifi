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

## Exemplu
User: "Dacă angajez un developer la 8.000 lei brut?"
Good response: "**Situație actuală** (din date reale):
- Cash disponibil: 24.000 lei
- Burn rate: 53.000 lei/lună
- Runway: ~13 zile

**Cost angajare nouă:**
- Salariu brut: 8.000 lei
- CAM (2.25%): 180 lei
- **Cost total lunar: 8.180 lei**

**După angajare:**
- Burn rate nou: 53.000 + 8.180 = **61.180 lei/lună**
- Runway nou: ~11 zile (↓ 2 zile)

⚠️ **Risc ridicat.** Cu runway-ul actual de 13 zile, o angajare ar reduce capacitatea de a acoperi cheltuielile. Recomand să aștepți încasarea de la StartupVibe (30.000 lei) înainte de angajare."
