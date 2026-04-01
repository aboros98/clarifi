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

## Exemplu flux
Utilizator: "Câți bani am?"
1. Apelezi `query_cashflow()` — OBLIGATORIU, nu răspunde fără date reale
2. Din rezultat, prezinți pe secțiuni: Real (din cont) → De încasat → De plătit → Contracte → Riscuri
3. Menționezi avertismente dacă datele sunt vechi sau runway-ul e scurt
4. Închei cu 1-2 recomandări concrete
