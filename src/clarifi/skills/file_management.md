# Gestiune Fișiere

## Keywords
folder, fișier, mută, move, structura, tree, upload, drive, sync, sincronizare, documente, files, citește, read, conținut

## Tools
- create_folder
- list_folders
- move_file
- read_document_content
- get_file_tree
- read_trace
- write_trace
- upload_to_storage
- sync_google_drive

## Instrucțiuni
Tool-uri de bază pentru gestionarea fișierelor:

- `get_file_tree()` — vezi toată structura (include trace-uri pe foldere)
- `list_folders(path)` — vezi conținutul unui folder
- `create_folder(name, parent_path)` — creează folder nou
- `move_file(file_id, target_path)` — mută un fișier
- `read_document_content(doc_id)` — citește textul unui document
- `read_trace(path)` / `write_trace(path, ...)` — citește/scrie notele agentului pe folder
- `upload_to_storage(path)` — încarcă fișier în Supabase Storage
- `sync_google_drive()` — sincronizează cu Google Drive

## Ton
- Fii practic — arată structura clar, cu numere
- Dacă utilizatorul cere să vezi ce e într-un folder, arată fișierele + rezumatul trace-ului dacă există
- Nu repeta comenzi executate — arată doar rezultatul
