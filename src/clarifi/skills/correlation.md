# Corelare & Reconciliere

## Keywords
corelare, reconciliere, facturat, încasat, status contract, contract status, diferențe, gaps, totul facturat, totul încasat, reconcile

## Tools
- check_contract_status
- reconcile_project
- run_payment_matching
- confirm_match

## Instrucțiuni
When the user asks about the chain Contract → Invoice → Payment:

1. For contract status: call `check_contract_status(contract_number)` — shows what % is invoiced and collected
2. For project reconciliation: call `reconcile_project(project_code)` — full budget vs contract vs invoiced vs collected
3. For payment matching: call `run_payment_matching()` — find unmatched bank transactions
4. To confirm a match: call `confirm_match(transaction_id, invoice_id)`

Key questions this answers:
- "S-a facturat tot conform contractului?" (Was everything invoiced per contract?)
- "S-a încasat tot?" (Was everything collected?)
- "Există întârzieri?" (Are there delays?)
- "Există diferențe?" (Are there discrepancies?)

## Format răspuns
Show the chain clearly:
```
Contract CTR-2025-001: 150.000 lei
├── Facturat: 90.000 lei (60%)
│   ├── Încasat: 75.000 lei (83%)
│   └── Restant: 15.000 lei
└── Nefacturat: 60.000 lei (40%)
```
