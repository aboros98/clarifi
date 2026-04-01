# Planificare Analiză

## Keywords
plan, planifică, analizează tot, analyze, bulk, toate documentele, toate facturile, procesează tot, overview

## Tools
- get_file_tree
- list_folders
- read_trace
- read_document_content

## Instrucțiuni
Când utilizatorul vrea să analizezi mai multe documente sau să faci o trecere completă:

1. Apelează `get_file_tree()` — vezi structura curentă + trace_summary pe fiecare folder
2. Apelează `read_trace()` pentru folder-ele care au fost analizate înainte — vezi ce s-a făcut deja
3. Identifică:
   - Câte documente noi/neprocesate sunt?
   - Ce foldere NU au trace (neanalizate)?
   - Ce trace-uri sunt vechi (>7 zile)?
4. Fă un plan în ordine logică:
   a. Mai întâi organizare (mută din /Neprocesat)
   b. Apoi contracte (sunt baza pentru facturi)
   c. Apoi facturi (se leagă de contracte)
   d. Apoi extrase bancare (se leagă de facturi)
   e. La final, cross-referință și alerting
5. Prezintă planul utilizatorului
6. Cere confirmare înainte de a începe
7. Execută pas cu pas, scriind trace după fiecare folder

### IMPORTANT
- NU începe analiza fără confirmare
- Arată progresul: "Pas 2/5: Analizez contracte..."
- Dacă găsești probleme (date lipsă, documente ilizibile), raportează-le

## Format răspuns
📋 **Plan de analiză:**

**Structura curentă:**
- /Contracte: 3 fișiere (ultimul trace: 15.03.2026)
- /Facturi Emise: 6 fișiere (neanalizat)
- /Neprocesat: 4 fișiere noi

**Pași propuși:**
1. Organizare 4 documente noi din /Neprocesat
2. Analiză contracte noi (dacă există)
3. Extragere date din 6 facturi din /Facturi Emise
4. Cross-referință facturi ↔ contracte
5. Generare raport și trace-uri

Durează vreo 3-5 minute. Merg?
