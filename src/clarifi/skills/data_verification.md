# Verificare & Corecție Date

## Keywords
corect, corectează, greșit, wrong, modifică, change, update, confirmă, confirm, verifică, stale, vechi, outdated

## Tools
- confirm_data
- correct_data
- mark_stale
- check_freshness

## Instrucțiuni
Când utilizatorul vrea să verifice, corecteze sau actualizeze date:

1. Dacă confirmă: apelează `confirm_data(entity_type, entity_id)`
2. Dacă corectează: apelează `correct_data(entity_type, entity_id, corrections)`
3. Dacă spune că datele sunt vechi: apelează `mark_stale(entity_type, entity_id, reason)`
4. Dacă vrea o trecere în revistă: apelează `check_freshness()`

## Ton
- Confirmă scurt și natural — nu repeta tot ce a zis utilizatorul
- Dacă datele au fost marcate ca depășite, sugerează să încarce un document actualizat
- Nu folosi texte fixe — formulează în funcție de context
