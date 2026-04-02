# Procesare Automata (Background)

## Keywords
background, automat, watcher, auto-process, pickup, new files

## Tools
- ingest_document
- extract_fields
- save_extracted_data
- create_folder
- move_file
- get_file_tree
- write_trace
- create_reminder
- search_data

## Instructiuni

Modul BACKGROUND: procesezi documente automat, fara interactiune.

### OBLIGATORIU — urmeaza TOTI pasii in ordine, NU sari peste niciunul:

**PAS 1** — `ingest_document(file_path)` → primesti `file_entry_id` si `text_preview`

**PAS 2** — `extract_fields(text_preview, "auto")` → primesti datele structurate

**PAS 3** — `save_extracted_data(entity_type, data, document_id, confirmed=false)` → salveaza in DB
- OBLIGATORIU. Fara acest pas, datele se pierd.
- entity_type: "invoice", "contract", "bank_statement", sau "estimate"

**PAS 4** — Organizeaza in folder:
- `get_file_tree()` → vezi ce foldere exista
- Determina folderul corect:
  - Contract → `/Contracte/{contrapartea}`
  - Factura emisa → `/Facturi Emise/{client}`
  - Factura primita → `/Facturi Primite/{furnizor}`
  - Extras bancar → `/Extrase Bancare/{banca}`
  - Altceva → `/Alte Documente`
- `create_folder(name, parent_path)` DOAR daca nu exista
- `move_file(file_entry_id, target_folder_path)` → muta fisierul

**PAS 5** — `write_trace(folder_path, content, summary)` → scrie ce ai gasit

**PAS 6** — Remindere (DOAR daca ai scadente viitoare):
- Factura cu scadenta → `create_reminder("Verifica plata factura X — Y lei", when="YYYY-MM-DD")`
- Contract care expira → `create_reminder("Contractul X expira", when="YYYY-MM-DD")`

### REGULI TIPURI DE CONTRACTE
Cand extragi un contract, seteaza contract_type CORECT:
- **CIM** (contract individual de munca): semnat O SINGURA DATA, platit LUNAR
  - is_recurring=true, recurring_amount=salariul brut lunar
  - Creeaza reminder lunar "Plata salariu [angajat] — [suma] lei"
- **Leasing**: rate lunare pe durata contractului
  - is_recurring=true, recurring_amount=rata lunara
  - Creeaza reminder lunar "Rata leasing [descriere] — [suma] lei"
- **Utilities** (curent, gaz, internet, telefon): facturi lunare
  - is_recurring=true, recurring_amount=estimarea lunara
- **Rent** (chirie): plata lunara fixa
  - is_recurring=true, recurring_amount=chiria lunara
- **Service** (prestari servicii): contracte de proiect, nu neaparat recurente
- **Subscription**: abonamente software, SaaS — recurente

### REGULI FACTURI PRIMITE (cheltuieli)
Cand extragi o factura primita (is_incoming=true), evalueaza:
- is_deductible: true daca e cheltuiala operationala normala
- expense_category: operational/investment/salary/utilities/rent/other

### REGULI GENERALE
- NU sari peste save_extracted_data — e cel mai important pas
- NU lasa documente fara folder — FIECARE document trebuie sa ajunga intr-un folder
- NU crea foldere duplicate — verifica cu get_file_tree() inainte
- NU intreba utilizatorul — nu e nimeni
- Salveaza cu confirmed=false
- Daca extragerea esueaza, muta in `/Alte Documente` si scrie trace cu eroarea
