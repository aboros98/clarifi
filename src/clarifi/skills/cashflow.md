# Cashflow & Lichiditate

## Keywords
cashflow, cash, bani, lichiditate, sold, disponibil, runway, burn, ard, rămân bani, câți bani, cont, money, balance, funds

## Tools
- query_cashflow

## Instrucțiuni
Când utilizatorul întreabă despre cash, bani disponibili sau runway:

1. Apelează `query_cashflow()` — returnează date structurate pe 4 categorii:
   - **actual**: sold bancar real, burn rate, runway (din extrase bancare)
   - **expected**: proiecții intrări/ieșiri (din facturi neplătite)
   - **committed**: valoare contractuală nefacturată, milestone-uri viitoare
   - **risk**: restanțe, prospețimea datelor

2. DISTINGE ÎNTOTDEAUNA datele reale de cele proiectate
3. Dacă datele bancare au > 3 zile, avertizează: "⚠️ Datele bancare au X zile"
4. Dacă runway < 90 zile, avertizează explicit
5. Dacă sunt restanțe mari, menționează-le ca pârghie de îmbunătățire

## Format răspuns
Prezintă pe secțiuni clare — utilizatorul trebuie să vadă ce e REAL vs ce e PROIECTAT.

## Exemplu
Utilizator: "Câți bani am?"
Răspuns bun: "**Situație financiară la 28.03.2026:**

💰 **Real (din cont bancar):**
- Cash disponibil: **24.000 lei**
- Burn rate: 53.000 lei/lună
- Runway: ~13 zile
- ⚠️ Datele bancare au 13 zile — încarcă un extras recent

📥 **De încasat (proiectat):**
- 30 zile: 55.000 lei (din care 30.000 restante!)
- 90 zile: 70.000 lei

📤 **De plătit (proiectat):**
- 30 zile: 8.000 lei

📋 **Angajat prin contracte (nefacturat încă):**
- 60.000 lei valoare contractuală nefacturată
- 30.000 lei milestone scadent luna asta

⚠️ **StartupVibe are 30.000 lei restanți de peste 30 zile.**
Dacă încasezi, runway-ul crește la ~30 zile.

Recomand: sună StartupVibe azi și încarcă un extras bancar recent."
