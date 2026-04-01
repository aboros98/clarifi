"""Generate synthetic Romanian financial documents for testing.

Creates realistic invoices, contracts, and bank statements as text files
that can be uploaded to Clarifi for extraction testing.
"""

import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "test_documents"
OUTPUT_DIR.mkdir(exist_ok=True)


def write_doc(filename: str, content: str):
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    print(f"  Created: {path}")


# ─── Invoice 1: Emitted invoice (issued by our company) ─────────────
write_doc("factura_emisa_001.txt", """
FACTURA FISCALA
Nr: CLR-2026-0042
Data emiterii: 15.03.2026
Data scadentei: 14.04.2026

FURNIZOR:
  SC Digital Solutions Pro SRL
  CUI: RO41892356
  J40/5678/2021
  Str. Victoriei nr. 45, Sector 1, Bucuresti
  Cont: RO62BRDE445SV12345678901 - BRD
  Email: office@digitalsolutions.ro

CLIENT:
  SC TechVision Romania SRL
  CUI: RO38745612
  J12/3456/2019
  Bd. Unirii nr. 22, Cluj-Napoca
  Cont: RO89RNCB0082044258710001 - BCR

PRODUSE/SERVICII:
  Nr | Descriere                          | UM   | Cant | Pret unitar | Valoare
  ---+------------------------------------+------+------+-------------+---------
   1 | Dezvoltare aplicatie web - Sprint 3 | ore  |  120 |     250,00  | 30.000,00
   2 | Mentenanta lunara hosting           | luna |    1 |   1.500,00  |  1.500,00
   3 | Consultanta tehnica                 | ore  |   16 |     350,00  |  5.600,00

  Subtotal:                           37.100,00 lei
  TVA (19%):                           7.049,00 lei
  TOTAL DE PLATA:                     44.149,00 lei

Curs BNR: N/A (factura in lei)
Mentiuni: Plata prin transfer bancar in contul indicat.
""")


# ─── Invoice 2: Received invoice (from a supplier) ───────────────────
write_doc("factura_primita_AWS_martie.txt", """
FACTURA / INVOICE
Nr: INV-EU-2026-8834
Data: 01.03.2026
Scadenta: 31.03.2026

FURNIZOR / SUPPLIER:
  Amazon Web Services EMEA SARL
  VAT: LU26888617
  38 Avenue John F. Kennedy, L-1855 Luxembourg

CLIENT / CUSTOMER:
  SC Digital Solutions Pro SRL
  CUI: RO41892356
  Str. Victoriei nr. 45, Sector 1, Bucuresti, Romania

SERVICII:
  Descriere                              | Valoare (EUR)
  ---------------------------------------+-------------
  EC2 On-Demand (eu-central-1) - Martie  |      342,18
  RDS PostgreSQL db.t3.medium            |      128,50
  S3 Storage (120 GB)                    |       12,30
  CloudFront (250 GB transfer)           |       45,00
  Route53 Hosted Zone                     |        2,50

  Subtotal:                   530,48 EUR
  TVA (19% - taxare inversa): 100,79 EUR
  TOTAL:                      631,27 EUR

Observatii: Factura cu TVA in regim de taxare inversa (reverse charge).
Curs BNR la 01.03.2026: 1 EUR = 4,9752 RON
Echivalent RON: 3.140,37 lei
""")


# ─── Invoice 3: Another issued invoice ────────────────────────────────
write_doc("factura_emisa_002_RetailMax.txt", """
FACTURA PROFORMA
Nr: CLR-2026-0043
Data: 25.03.2026
Scadenta: 24.04.2026

FURNIZOR:
  SC Digital Solutions Pro SRL
  CUI: RO41892356
  J40/5678/2021
  Str. Victoriei nr. 45, Bucuresti
  IBAN: RO62BRDE445SV12345678901 - BRD

CATRE:
  SC RetailMax Distribution SRL
  CUI: RO29384756
  J23/7890/2018
  Str. Fabricii nr. 10, Timisoara, Timis
  IBAN: RO15INGB0001008765432109 - ING

DETALII:
  1. Implementare sistem ERP - Faza 1     | 45.000,00 lei
     (Analiza cerinte, design, prototip)
  2. Licente software (12 luni)            | 12.000,00 lei
  3. Training echipa (3 zile x 4 pers)     |  7.200,00 lei

  Subtotal:      64.200,00 lei
  TVA 19%:       12.198,00 lei
  TOTAL:         76.398,00 lei

Mod de plata: 50% avans la semnarea contractului, 50% la livrare.
""")


# ─── Contract ─────────────────────────────────────────────────────────
write_doc("contract_mentenanta_TechVision.txt", """
CONTRACT DE PRESTARI SERVICII
Nr. DSP/2026/015
Data: 01.02.2026

PARTILE CONTRACTANTE:

1. PRESTATORUL:
   SC Digital Solutions Pro SRL
   CUI: RO41892356, J40/5678/2021
   Sediu: Str. Victoriei nr. 45, Sector 1, Bucuresti
   Cont: RO62BRDE445SV12345678901, BRD
   Reprezentant: Dan Ionescu, Administrator

2. BENEFICIARUL:
   SC TechVision Romania SRL
   CUI: RO38745612, J12/3456/2019
   Sediu: Bd. Unirii nr. 22, Cluj-Napoca
   Reprezentant: Maria Popescu, Director General

Art. 1 - OBIECTUL CONTRACTULUI
Prestatorul se obliga sa furnizeze servicii de mentenanta si dezvoltare
software pentru platforma web a Beneficiarului, conform specificatiilor
din Anexa 1.

Art. 2 - VALOAREA CONTRACTULUI
Valoarea totala: 180.000 lei (una suta optzeci mii lei) + TVA
Plata se face lunar, in rate egale de 15.000 lei + TVA / luna.

Art. 3 - DURATA
Contractul este valabil pe o perioada de 12 luni, de la 01.02.2026
pana la 31.01.2027, cu posibilitate de prelungire prin act aditional.

Art. 4 - OBLIGATIILE PRESTATORULUI
a) Sa asigure mentenanta preventiva si corectiva a platformei
b) Sa rezolve bugurile critice in maxim 4 ore lucratoare
c) Sa livreze update-uri de securitate in maxim 24 ore
d) Sa asigure disponibilitate 99.5% (uptime SLA)

Art. 5 - MILESTONE-URI
  M1: Audit tehnic initial - 28.02.2026 - 10.000 lei
  M2: Migare infrastructure cloud - 30.04.2026 - 25.000 lei
  M3: Redesign modul raportare - 30.06.2026 - 20.000 lei
  M4: Implementare API v2 - 30.09.2026 - 30.000 lei

Art. 6 - PENALITATI
In cazul nerespectarii termenelor de livrare, Prestatorul va plati
penalitati de 0,05% din valoarea milestone-ului pentru fiecare zi
calendaristica de intarziere, dar nu mai mult de 10% din valoare.

Art. 7 - CONFIDENTIALITATE
Partile se obliga sa pastreze confidentialitatea informatiilor
obtinute in cadrul executarii contractului pe o perioada de 2 ani
de la incetarea acestuia.

Art. 8 - REZILIEREA
Contractul poate fi reziliat de oricare parte cu un preaviz de
30 de zile calendaristice, transmis in scris.

PRESTATOR:                         BENEFICIAR:
SC Digital Solutions Pro SRL       SC TechVision Romania SRL
Dan Ionescu                       Maria Popescu
Administrator                      Director General
""")


# ─── Bank Statement ──────────────────────────────────────────────────
write_doc("extras_cont_BRD_martie_2026.txt", """
EXTRAS DE CONT
Banca: BRD - Groupe Societe Generale
Cont: RO62BRDE445SV12345678901
Titular: SC Digital Solutions Pro SRL
CUI: RO41892356
Perioada: 01.03.2026 - 31.03.2026

Sold initial la 01.03.2026: 47.250,00 lei

DATA       | DESCRIERE                                    |    DEBIT   |   CREDIT   | SOLD
-----------+----------------------------------------------+------------+------------+-----------
03.03.2026 | Incasare factura CLR-2025-039 TechVision     |            |  35.700,00 |  82.950,00
05.03.2026 | Plata salarii februarie 2026                 |  28.450,00 |            |  54.500,00
05.03.2026 | Contributii sociale februarie                |  12.680,00 |            |  41.820,00
07.03.2026 | Plata chirie birou martie                     |   4.500,00 |            |  37.320,00
10.03.2026 | Incasare factura CLR-2026-0040 RetailMax     |            |  23.800,00 |  61.120,00
12.03.2026 | Plata factura Vodafone nr. VDF-445566        |     389,00 |            |  60.731,00
15.03.2026 | Plata factura AWS INV-EU-2026-7721 (feb)     |   2.890,50 |            |  57.840,50
15.03.2026 | Plata factura hosting Hetzner                |     450,00 |            |  57.390,50
18.03.2026 | Transfer intern catre cont EUR               |   5.000,00 |            |  52.390,50
20.03.2026 | Incasare avans proiect ERP RetailMax         |            |  38.199,00 |  90.589,50
22.03.2026 | Plata freelancer design - Ionescu Alexandru  |   6.500,00 |            |  84.089,50
25.03.2026 | Plata asigurare profesionala                 |   1.200,00 |            |  82.889,50
28.03.2026 | Comision bancar lunar                        |     125,00 |            |  82.764,50
31.03.2026 | Dobanda cont curent                          |            |      12,30 |  82.776,80

Sold final la 31.03.2026: 82.776,80 lei

Total intrari:   97.711,30 lei
Total iesiri:    62.184,50 lei
Nr. operatiuni: 14

Acest extras a fost generat automat si nu necesita semnatura.
""")


# ─── Invoice 4: Overdue invoice ──────────────────────────────────────
write_doc("factura_restanta_MobileApps.txt", """
FACTURA FISCALA
Nr: CLR-2026-0038
Data emiterii: 10.01.2026
Data scadentei: 09.02.2026
STATUS: RESTANTA - NEINCASATA

FURNIZOR:
  SC Digital Solutions Pro SRL
  CUI: RO41892356
  J40/5678/2021
  Str. Victoriei nr. 45, Bucuresti
  IBAN: RO62BRDE445SV12345678901 - BRD

CLIENT:
  SC MobileApps Innovation SRL
  CUI: RO44123789
  J40/9012/2022
  Calea Mosilor nr. 128, Sector 3, Bucuresti

SERVICII:
  1. Dezvoltare aplicatie mobile iOS - Sprint 1  |  25.000,00 lei
  2. Design UI/UX (15 ecrane)                     |   8.000,00 lei
  3. Testare QA si bug fixing                     |   4.500,00 lei

  Subtotal:      37.500,00 lei
  TVA 19%:        7.125,00 lei
  TOTAL:         44.625,00 lei

NOTA: Factura este restanta de peste 50 de zile. S-au trimis 3 notificari
de plata (15.02, 01.03, 15.03). Clientul a confirmat verbal ca va plati
pana la sfarsitul lunii aprilie 2026.
""")


print(f"\nGenerated {len(list(OUTPUT_DIR.glob('*')))} test documents in {OUTPUT_DIR}")
print("\nTo test with Clarifi:")
print("  1. Start the backend: uvicorn clarifi.main:app --port 8001")
print("  2. Upload via API:")
print('     curl -X POST http://localhost:8001/documents/upload \\')
print('       -H "Authorization: Bearer <token>" \\')
print('       -F "file=@test_documents/factura_emisa_001.txt"')
print("  3. Or copy to inbox/ for auto-processing:")
print("     cp test_documents/*.txt inbox/")
