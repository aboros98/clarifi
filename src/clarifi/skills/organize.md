# Organizare Documente

## Keywords
organizează, organize, aranjează, sortează, sort, mută, move, folder, foldere, inbox, neprocesat, structura, curăță

## Tools
- get_file_tree
- list_folders
- create_folder
- move_file
- read_document_content
- write_trace
- ask_user

## Instrucțiuni
Când utilizatorul vrea să organizezi documente:

1. `get_file_tree()` — vezi structura + ce foldere au trace
2. `list_folders("/Neprocesat")` sau alt folder sursă — vezi fișierele
3. Pentru fiecare fișier neorganizat:
   a. `read_document_content(id)` — citește primele 2000 caractere
   b. Decide tipul: contract, factură emisă/primită, extras bancar, deviz
   c. Dacă nu ești sigur, folosește `ask_user()` cu opțiuni
   d. `create_folder()` dacă nu există
   e. `move_file()` la folderul potrivit
4. `write_trace()` pentru fiecare folder modificat
5. Raportează ce ai făcut — scurt, cu numere

### Structura recomandată
```
/Contracte/{client}/{an}/
/Facturi Emise/{an}/{luna}/
/Facturi Primite/{an}/{luna}/
/Extrase Bancare/{banca}/{an}/
/Devize/{client}/
/Neprocesat/
```

Adaptează la ce face utilizatorul. Dacă a organizat manual, respectă structura lui.

## Ton
NU: "Am scanat 8 documente din /Neprocesat. Am organizat: 3 facturi emise → /Facturi Emise/2026/Martie/"
DA: "Am trecut prin cele 8 documente. 3 sunt facturi pe care le-am mutat în Facturi Emise, 2 contracte, 1 extras bancar. Mai rămâne unu' pe care nu l-am putut clasifica — vrei să-l vedem împreună?"
