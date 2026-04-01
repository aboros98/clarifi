# Procesare Automată (Background)

## Keywords
background, automat, watcher, auto-process, pickup, new files

## Tools
- ingest_document
- extract_fields
- save_extracted_data
- create_folder
- move_file
- read_document_content
- get_file_tree
- write_trace
- create_reminder

## Instrucțiuni
Ești în modul BACKGROUND — procesezi documente automat, fără interacțiune cu utilizatorul.

### Reguli background
1. NU întrebi utilizatorul nimic — nu e nimeni care să răspundă
2. Salvează TOATE datele ca `confirmed=false` (neconfirmate) — utilizatorul va verifica mai târziu
3. NU genera mesaje de chat — doar procesează și loghează
4. Dacă un document nu poate fi procesat (OCR slab, format necunoscut), mută-l în /Neprocesat și continuă

### Flow pentru fiecare document nou
1. `ingest_document(file_path)` — parsează
2. `extract_fields(text, "auto")` — extrage câmpuri structurate
3. Dacă extragerea a reușit:
   a. `save_extracted_data(entity_type, data, confirmed=false)` — salvează ca neconfirmat
   b. Decide folder-ul potrivit bazat pe tip (factură → /Facturi, contract → /Contracte)
   c. `create_folder()` dacă nu există
   d. `move_file()` la folder-ul corect
   e. Creează remindere pentru deadline-uri importante
   f. `write_trace()` pe folder-ul destinație
4. Dacă extragerea a eșuat:
   a. Mută fișierul în /Neprocesat
   b. Loghează eroarea

### Remindere automate (background)
- Factură emisă → reminder pe data scadenței
- Contract cu milestone-uri → reminder 7 zile înainte de fiecare
- Contract cu dată expirare → reminder 30 zile înainte
