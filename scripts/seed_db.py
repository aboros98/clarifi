"""
Seed script: populates the database with realistic test data for
SC Digital Solutions SRL — a Romanian web/software services company.

Run:  python -m scripts.seed_db
Requires: DATABASE_URL in .env or environment
"""

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clarifi.db.session import async_session_factory, engine
from clarifi.models import Base
from clarifi.models.bank_transaction import BankTransaction, TransactionType
from clarifi.models.company import Company, CompanyRole
from clarifi.models.contract import Contract, ContractMilestone, ContractObligation, ContractPenalty, ContractStatus
from clarifi.models.invoice import Invoice, InvoiceDirection, InvoiceStatus
from clarifi.models.project import Project, ProjectStatus
from clarifi.models.scheduled_task import ScheduleType, ScheduledTask

# ---------- deterministic UUIDs for referencing ----------
def _uuid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"

# Companies
OWN_ID      = _uuid(1)
TECHCORP_ID = _uuid(2)
RETAIL_ID   = _uuid(3)
STARTUP_ID  = _uuid(4)
CLOUD_ID    = _uuid(5)
OFFICE_ID   = _uuid(6)
FREELANCER_ID = _uuid(7)

# Projects
PRJ1_ID = _uuid(101)
PRJ2_ID = _uuid(102)
PRJ3_ID = _uuid(103)
PRJ4_ID = _uuid(104)

# Contracts
CTR1_ID = _uuid(201)
CTR2_ID = _uuid(202)
CTR3_ID = _uuid(203)
CTR4_ID = _uuid(204)
CTR5_ID = _uuid(205)
CTR6_ID = _uuid(206)

# Milestones
MS1_ID = _uuid(301)
MS2_ID = _uuid(302)
MS3_ID = _uuid(303)
MS4_ID = _uuid(304)

# Invoices issued
INV1_ID = _uuid(401)
INV2_ID = _uuid(402)
INV3_ID = _uuid(403)
INV4_ID = _uuid(404)
INV5_ID = _uuid(405)
INV6_ID = _uuid(406)
INV7_ID = _uuid(407)
INV8_ID = _uuid(408)
INV9_ID = _uuid(409)

# Invoices received
RINV1_ID = _uuid(501)
RINV2_ID = _uuid(502)
RINV3_ID = _uuid(503)
RINV4_ID = _uuid(504)
RINV5_ID = _uuid(505)
RINV6_ID = _uuid(506)
RINV7_ID = _uuid(507)

# Bank transactions
BTX_START = 601

NOW = datetime.now(timezone.utc)


def _companies() -> list[Company]:
    return [
        Company(
            id=OWN_ID,
            legal_name="SC Digital Solutions SRL",
            trade_name="Digital Solutions",
            tax_id="RO12345678",
            registration_number="J40/1234/2020",
            role=CompanyRole.OWN_COMPANY,
            address="Str. Victoriei 120, Sector 1",
            city="București",
            country_code="RO",
            email="office@digitalsolutions.ro",
            phone="+40 21 123 4567",
            bank_accounts=[{"iban": "RO49AAAA1B31007593840000", "bank_name": "BCR", "currency": "RON"}],
            name_variants=["Digital Solutions", "SC Digital Solutions SRL", "Digital Solutions SRL"],
        ),
        Company(
            id=TECHCORP_ID,
            legal_name="SC TechCorp SA",
            trade_name="TechCorp",
            tax_id="RO87654321",
            role=CompanyRole.CLIENT,
            address="Bd. Unirii 45",
            city="București",
            country_code="RO",
            email="contact@techcorp.ro",
            bank_accounts=[{"iban": "RO12BBBB2C42008604950000", "bank_name": "BRD", "currency": "RON"}],
            name_variants=["TechCorp", "SC TechCorp SA", "Tech Corp"],
        ),
        Company(
            id=RETAIL_ID,
            legal_name="SC RetailPlus SRL",
            trade_name="RetailPlus",
            tax_id="RO11223344",
            role=CompanyRole.CLIENT,
            address="Str. Comercului 8",
            city="Cluj-Napoca",
            country_code="RO",
            email="finance@retailplus.ro",
            name_variants=["RetailPlus", "SC RetailPlus SRL", "Retail Plus"],
        ),
        Company(
            id=STARTUP_ID,
            legal_name="SC StartupVibe SRL",
            trade_name="StartupVibe",
            tax_id="RO99887766",
            role=CompanyRole.CLIENT,
            address="Str. Inovației 3",
            city="Timișoara",
            country_code="RO",
            email="admin@startupvibe.ro",
            name_variants=["StartupVibe", "SC StartupVibe SRL", "Startup Vibe"],
        ),
        Company(
            id=CLOUD_ID,
            legal_name="SC CloudHost SRL",
            trade_name="CloudHost",
            tax_id="RO55667788",
            role=CompanyRole.SUPPLIER,
            address="Str. Serverului 1",
            city="București",
            country_code="RO",
            email="billing@cloudhost.ro",
            name_variants=["CloudHost", "SC CloudHost SRL"],
        ),
        Company(
            id=OFFICE_ID,
            legal_name="SC Office Rent SRL",
            trade_name="Office Rent",
            tax_id="RO33445566",
            role=CompanyRole.SUPPLIER,
            address="Str. Birourilor 22",
            city="București",
            country_code="RO",
            name_variants=["Office Rent", "SC Office Rent SRL"],
        ),
        Company(
            id=FREELANCER_ID,
            legal_name="PFA Ionescu Mihai",
            trade_name="Mihai Dev",
            tax_id="RO44556677",
            role=CompanyRole.SUPPLIER,
            address="Str. Programatorilor 5",
            city="Iași",
            country_code="RO",
            name_variants=["Ionescu Mihai", "PFA Ionescu Mihai", "Mihai Dev"],
        ),
    ]


def _projects() -> list[Project]:
    return [
        Project(
            id=PRJ1_ID,
            project_code="PRJ-001",
            name="Website Redesign TechCorp",
            description="Complete redesign of TechCorp corporate website with new CMS",
            client_company_id=TECHCORP_ID,
            status=ProjectStatus.ACTIVE,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 6, 30),
            budget=Decimal("150000.00"),
            currency="RON",
        ),
        Project(
            id=PRJ2_ID,
            project_code="PRJ-002",
            name="Mobile App RetailPlus",
            description="iOS and Android mobile shopping app for RetailPlus",
            client_company_id=RETAIL_ID,
            status=ProjectStatus.ACTIVE,
            start_date=date(2025, 11, 1),
            end_date=date(2026, 5, 31),
            budget=Decimal("80000.00"),
            currency="RON",
        ),
        Project(
            id=PRJ3_ID,
            project_code="PRJ-003",
            name="CRM Integration StartupVibe",
            description="Custom CRM integration with Salesforce for StartupVibe",
            client_company_id=STARTUP_ID,
            status=ProjectStatus.ACTIVE,
            start_date=date(2026, 1, 15),
            end_date=date(2026, 7, 15),
            budget=Decimal("45000.00"),
            currency="RON",
        ),
        Project(
            id=PRJ4_ID,
            project_code="PRJ-004",
            name="SEO & Marketing TechCorp",
            description="6-month SEO and digital marketing campaign for TechCorp",
            client_company_id=TECHCORP_ID,
            status=ProjectStatus.COMPLETED,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
            budget=Decimal("30000.00"),
            currency="RON",
        ),
    ]


def _contracts() -> list[Contract]:
    return [
        Contract(
            id=CTR1_ID,
            contract_number="CTR-2025-001",
            title="Website Redesign TechCorp",
            counterparty_id=TECHCORP_ID,
            project_id=PRJ1_ID,
            total_value=Decimal("150000.00"),
            currency="RON",
            vat_rate=Decimal("19.00"),
            signed_date=date(2025, 8, 25),
            start_date=date(2025, 9, 1),
            end_date=date(2026, 6, 30),
            status=ContractStatus.ACTIVE,
            payment_terms_days=30,
            billing_frequency="milestone",
        ),
        Contract(
            id=CTR2_ID,
            contract_number="CTR-2025-002",
            title="Mobile App Development RetailPlus",
            counterparty_id=RETAIL_ID,
            project_id=PRJ2_ID,
            total_value=Decimal("80000.00"),
            currency="RON",
            vat_rate=Decimal("19.00"),
            signed_date=date(2025, 10, 28),
            start_date=date(2025, 11, 1),
            end_date=date(2026, 5, 31),
            status=ContractStatus.ACTIVE,
            payment_terms_days=30,
            billing_frequency="monthly",
        ),
        Contract(
            id=CTR3_ID,
            contract_number="CTR-2025-003",
            title="CRM Integration StartupVibe",
            counterparty_id=STARTUP_ID,
            project_id=PRJ3_ID,
            total_value=Decimal("45000.00"),
            currency="RON",
            vat_rate=Decimal("19.00"),
            signed_date=date(2026, 1, 10),
            start_date=date(2026, 1, 15),
            end_date=date(2026, 7, 15),
            status=ContractStatus.ACTIVE,
            payment_terms_days=15,
            billing_frequency="monthly",
        ),
        Contract(
            id=CTR4_ID,
            contract_number="CTR-2025-004",
            title="SEO & Marketing Campaign TechCorp",
            counterparty_id=TECHCORP_ID,
            project_id=PRJ4_ID,
            total_value=Decimal("30000.00"),
            currency="RON",
            vat_rate=Decimal("19.00"),
            signed_date=date(2025, 5, 28),
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
            status=ContractStatus.COMPLETED,
            payment_terms_days=30,
            billing_frequency="monthly",
        ),
        # Supplier contracts
        Contract(
            id=CTR5_ID,
            contract_number="CTR-2026-005",
            title="Cloud Hosting Services",
            counterparty_id=CLOUD_ID,
            total_value=Decimal("24000.00"),
            currency="RON",
            signed_date=date(2025, 12, 15),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ContractStatus.ACTIVE,
            payment_terms_days=15,
            billing_frequency="monthly",
        ),
        Contract(
            id=CTR6_ID,
            contract_number="CTR-2026-006",
            title="Office Space Lease",
            counterparty_id=OFFICE_ID,
            total_value=Decimal("72000.00"),
            currency="RON",
            signed_date=date(2025, 12, 20),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ContractStatus.ACTIVE,
            payment_terms_days=5,
            billing_frequency="monthly",
        ),
    ]


def _milestones() -> list[ContractMilestone]:
    return [
        ContractMilestone(
            id=MS1_ID,
            contract_id=CTR1_ID,
            title="Design Phase Complete",
            description="Wireframes, mockups, and design system delivered",
            due_date=date(2025, 10, 15),
            amount=Decimal("30000.00"),
            completed=True,
            completed_date=date(2025, 10, 12),
        ),
        ContractMilestone(
            id=MS2_ID,
            contract_id=CTR1_ID,
            title="Frontend Development Complete",
            description="All frontend pages implemented and responsive",
            due_date=date(2026, 1, 15),
            amount=Decimal("45000.00"),
            completed=True,
            completed_date=date(2026, 1, 14),
        ),
        ContractMilestone(
            id=MS3_ID,
            contract_id=CTR1_ID,
            title="Backend Development Complete",
            description="CMS backend, API, and integrations",
            due_date=date(2026, 3, 30),
            amount=Decimal("45000.00"),
            completed=False,  # OVERDUE!
        ),
        ContractMilestone(
            id=MS4_ID,
            contract_id=CTR1_ID,
            title="Final Delivery & Launch",
            description="Testing, deployment, and go-live",
            due_date=date(2026, 6, 15),
            amount=Decimal("30000.00"),
            completed=False,
        ),
    ]


def _obligations() -> list[ContractObligation]:
    return [
        ContractObligation(
            contract_id=CTR1_ID,
            obligated_party="own",
            description="Deliver monthly progress reports",
            recurring=True,
            recurrence_pattern="monthly",
            fulfilled=False,
        ),
        ContractObligation(
            contract_id=CTR3_ID,
            obligated_party="counterparty",
            description="Provide Salesforce API credentials and access",
            deadline=date(2026, 2, 1),
            fulfilled=True,
        ),
    ]


def _penalties() -> list[ContractPenalty]:
    return [
        ContractPenalty(
            contract_id=CTR1_ID,
            trigger_condition="Delay in milestone delivery beyond 15 days",
            penalty_type="percentage_per_day",
            penalty_value=Decimal("0.1"),  # 0.1% per day
            cap_amount=Decimal("15000.00"),
        ),
        ContractPenalty(
            contract_id=CTR2_ID,
            trigger_condition="Failure to meet mobile app performance benchmarks",
            penalty_type="fixed_amount",
            penalty_value=Decimal("5000.00"),
        ),
    ]


def _invoices_issued() -> list[Invoice]:
    """Invoices we sent to clients (accounts receivable)."""
    return [
        # PRJ-001 TechCorp — Design phase (PAID)
        Invoice(
            id=INV1_ID,
            invoice_number="INV-2026-001",
            direction=InvoiceDirection.ISSUED,
            status=InvoiceStatus.PAID,
            issuer_company_id=OWN_ID,
            recipient_company_id=TECHCORP_ID,
            contract_id=CTR1_ID,
            project_id=PRJ1_ID,
            issue_date=date(2025, 10, 20),
            due_date=date(2025, 11, 20),
            subtotal=Decimal("25210.08"),
            vat_amount=Decimal("4789.92"),
            total_amount=Decimal("30000.00"),
            currency="RON",
            amount_paid=Decimal("30000.00"),
            amount_remaining=Decimal("0.00"),
            payment_terms_days=30,
        ),
        # PRJ-001 TechCorp — Frontend (PAID)
        Invoice(
            id=INV2_ID,
            invoice_number="INV-2026-002",
            direction=InvoiceDirection.ISSUED,
            status=InvoiceStatus.PAID,
            issuer_company_id=OWN_ID,
            recipient_company_id=TECHCORP_ID,
            contract_id=CTR1_ID,
            project_id=PRJ1_ID,
            issue_date=date(2026, 1, 20),
            due_date=date(2026, 2, 20),
            subtotal=Decimal("37815.13"),
            vat_amount=Decimal("7184.87"),
            total_amount=Decimal("45000.00"),
            currency="RON",
            amount_paid=Decimal("45000.00"),
            amount_remaining=Decimal("0.00"),
            payment_terms_days=30,
        ),
        # PRJ-002 RetailPlus — month 1 (PAID)
        Invoice(
            id=INV3_ID,
            invoice_number="INV-2026-003",
            direction=InvoiceDirection.ISSUED,
            status=InvoiceStatus.PAID,
            issuer_company_id=OWN_ID,
            recipient_company_id=RETAIL_ID,
            contract_id=CTR2_ID,
            project_id=PRJ2_ID,
            issue_date=date(2025, 12, 1),
            due_date=date(2025, 12, 31),
            subtotal=Decimal("21008.40"),
            vat_amount=Decimal("3991.60"),
            total_amount=Decimal("25000.00"),
            currency="RON",
            amount_paid=Decimal("25000.00"),
            amount_remaining=Decimal("0.00"),
            payment_terms_days=30,
        ),
        # PRJ-002 RetailPlus — month 2 (PAID)
        Invoice(
            id=INV4_ID,
            invoice_number="INV-2026-004",
            direction=InvoiceDirection.ISSUED,
            status=InvoiceStatus.PAID,
            issuer_company_id=OWN_ID,
            recipient_company_id=RETAIL_ID,
            contract_id=CTR2_ID,
            project_id=PRJ2_ID,
            issue_date=date(2026, 1, 15),
            due_date=date(2026, 2, 15),
            subtotal=Decimal("21008.40"),
            vat_amount=Decimal("3991.60"),
            total_amount=Decimal("25000.00"),
            currency="RON",
            amount_paid=Decimal("25000.00"),
            amount_remaining=Decimal("0.00"),
            payment_terms_days=30,
        ),
        # PRJ-002 RetailPlus — month 3 (OVERDUE 4 days)
        Invoice(
            id=INV5_ID,
            invoice_number="INV-2026-005",
            direction=InvoiceDirection.ISSUED,
            status=InvoiceStatus.OVERDUE,
            issuer_company_id=OWN_ID,
            recipient_company_id=RETAIL_ID,
            contract_id=CTR2_ID,
            project_id=PRJ2_ID,
            issue_date=date(2026, 2, 20),
            due_date=date(2026, 3, 22),
            subtotal=Decimal("21008.40"),
            vat_amount=Decimal("3991.60"),
            total_amount=Decimal("25000.00"),
            currency="RON",
            amount_paid=Decimal("0.00"),
            amount_remaining=Decimal("25000.00"),
            payment_terms_days=30,
        ),
        # PRJ-003 StartupVibe — month 1 (OVERDUE 38 days)
        Invoice(
            id=INV6_ID,
            invoice_number="INV-2026-006",
            direction=InvoiceDirection.ISSUED,
            status=InvoiceStatus.OVERDUE,
            issuer_company_id=OWN_ID,
            recipient_company_id=STARTUP_ID,
            contract_id=CTR3_ID,
            project_id=PRJ3_ID,
            issue_date=date(2026, 2, 1),
            due_date=date(2026, 2, 16),
            subtotal=Decimal("12605.04"),
            vat_amount=Decimal("2394.96"),
            total_amount=Decimal("15000.00"),
            currency="RON",
            amount_paid=Decimal("0.00"),
            amount_remaining=Decimal("15000.00"),
            payment_terms_days=15,
        ),
        # PRJ-003 StartupVibe — month 2 (OVERDUE 10 days)
        Invoice(
            id=INV7_ID,
            invoice_number="INV-2026-007",
            direction=InvoiceDirection.ISSUED,
            status=InvoiceStatus.OVERDUE,
            issuer_company_id=OWN_ID,
            recipient_company_id=STARTUP_ID,
            contract_id=CTR3_ID,
            project_id=PRJ3_ID,
            issue_date=date(2026, 3, 1),
            due_date=date(2026, 3, 16),
            subtotal=Decimal("12605.04"),
            vat_amount=Decimal("2394.96"),
            total_amount=Decimal("15000.00"),
            currency="RON",
            amount_paid=Decimal("0.00"),
            amount_remaining=Decimal("15000.00"),
            payment_terms_days=15,
        ),
        # PRJ-001 TechCorp — Backend milestone (SENT, due April 15)
        Invoice(
            id=INV8_ID,
            invoice_number="INV-2026-008",
            direction=InvoiceDirection.ISSUED,
            status=InvoiceStatus.SENT,
            issuer_company_id=OWN_ID,
            recipient_company_id=TECHCORP_ID,
            contract_id=CTR1_ID,
            project_id=PRJ1_ID,
            issue_date=date(2026, 3, 15),
            due_date=date(2026, 4, 15),
            subtotal=Decimal("12605.04"),
            vat_amount=Decimal("2394.96"),
            total_amount=Decimal("15000.00"),
            currency="RON",
            amount_paid=Decimal("0.00"),
            amount_remaining=Decimal("15000.00"),
            payment_terms_days=30,
        ),
        # PRJ-004 TechCorp — SEO (PAID, completed project)
        Invoice(
            id=INV9_ID,
            invoice_number="INV-2025-009",
            direction=InvoiceDirection.ISSUED,
            status=InvoiceStatus.PAID,
            issuer_company_id=OWN_ID,
            recipient_company_id=TECHCORP_ID,
            contract_id=CTR4_ID,
            project_id=PRJ4_ID,
            issue_date=date(2025, 7, 1),
            due_date=date(2025, 7, 31),
            subtotal=Decimal("25210.08"),
            vat_amount=Decimal("4789.92"),
            total_amount=Decimal("30000.00"),
            currency="RON",
            amount_paid=Decimal("30000.00"),
            amount_remaining=Decimal("0.00"),
            payment_terms_days=30,
        ),
    ]


def _invoices_received() -> list[Invoice]:
    """Invoices we received from suppliers (accounts payable)."""
    invoices = []
    # CloudHost — Jan (PAID)
    invoices.append(Invoice(
        id=RINV1_ID, invoice_number="CH-2026-001",
        direction=InvoiceDirection.RECEIVED, status=InvoiceStatus.PAID,
        issuer_company_id=CLOUD_ID, recipient_company_id=OWN_ID,
        contract_id=CTR5_ID,
        issue_date=date(2026, 1, 1), due_date=date(2026, 1, 15),
        subtotal=Decimal("1680.67"), vat_amount=Decimal("319.33"),
        total_amount=Decimal("2000.00"), currency="RON",
        amount_paid=Decimal("2000.00"), amount_remaining=Decimal("0.00"),
    ))
    # CloudHost — Feb (PAID)
    invoices.append(Invoice(
        id=RINV2_ID, invoice_number="CH-2026-002",
        direction=InvoiceDirection.RECEIVED, status=InvoiceStatus.PAID,
        issuer_company_id=CLOUD_ID, recipient_company_id=OWN_ID,
        contract_id=CTR5_ID,
        issue_date=date(2026, 2, 1), due_date=date(2026, 2, 15),
        subtotal=Decimal("1680.67"), vat_amount=Decimal("319.33"),
        total_amount=Decimal("2000.00"), currency="RON",
        amount_paid=Decimal("2000.00"), amount_remaining=Decimal("0.00"),
    ))
    # CloudHost — Mar (DUE, not yet paid)
    invoices.append(Invoice(
        id=RINV3_ID, invoice_number="CH-2026-003",
        direction=InvoiceDirection.RECEIVED, status=InvoiceStatus.RECEIVED,
        issuer_company_id=CLOUD_ID, recipient_company_id=OWN_ID,
        contract_id=CTR5_ID,
        issue_date=date(2026, 3, 1), due_date=date(2026, 3, 15),
        subtotal=Decimal("1680.67"), vat_amount=Decimal("319.33"),
        total_amount=Decimal("2000.00"), currency="RON",
        amount_paid=Decimal("0.00"), amount_remaining=Decimal("2000.00"),
    ))
    # OfficeRent — Jan (PAID)
    invoices.append(Invoice(
        id=RINV4_ID, invoice_number="OR-2026-001",
        direction=InvoiceDirection.RECEIVED, status=InvoiceStatus.PAID,
        issuer_company_id=OFFICE_ID, recipient_company_id=OWN_ID,
        contract_id=CTR6_ID,
        issue_date=date(2026, 1, 1), due_date=date(2026, 1, 5),
        subtotal=Decimal("5042.02"), vat_amount=Decimal("957.98"),
        total_amount=Decimal("6000.00"), currency="RON",
        amount_paid=Decimal("6000.00"), amount_remaining=Decimal("0.00"),
    ))
    # OfficeRent — Feb (PAID)
    invoices.append(Invoice(
        id=RINV5_ID, invoice_number="OR-2026-002",
        direction=InvoiceDirection.RECEIVED, status=InvoiceStatus.PAID,
        issuer_company_id=OFFICE_ID, recipient_company_id=OWN_ID,
        contract_id=CTR6_ID,
        issue_date=date(2026, 2, 1), due_date=date(2026, 2, 5),
        subtotal=Decimal("5042.02"), vat_amount=Decimal("957.98"),
        total_amount=Decimal("6000.00"), currency="RON",
        amount_paid=Decimal("6000.00"), amount_remaining=Decimal("0.00"),
    ))
    # OfficeRent — Mar (DUE)
    invoices.append(Invoice(
        id=RINV6_ID, invoice_number="OR-2026-003",
        direction=InvoiceDirection.RECEIVED, status=InvoiceStatus.RECEIVED,
        issuer_company_id=OFFICE_ID, recipient_company_id=OWN_ID,
        contract_id=CTR6_ID,
        issue_date=date(2026, 3, 1), due_date=date(2026, 3, 5),
        subtotal=Decimal("5042.02"), vat_amount=Decimal("957.98"),
        total_amount=Decimal("6000.00"), currency="RON",
        amount_paid=Decimal("0.00"), amount_remaining=Decimal("6000.00"),
    ))
    # Freelancer — PRJ-002 dev work (PAID)
    invoices.append(Invoice(
        id=RINV7_ID, invoice_number="MI-2026-001",
        direction=InvoiceDirection.RECEIVED, status=InvoiceStatus.PAID,
        issuer_company_id=FREELANCER_ID, recipient_company_id=OWN_ID,
        project_id=PRJ2_ID,
        issue_date=date(2026, 2, 15), due_date=date(2026, 2, 28),
        subtotal=Decimal("29411.76"), vat_amount=Decimal("5588.24"),
        total_amount=Decimal("35000.00"), currency="RON",
        amount_paid=Decimal("35000.00"), amount_remaining=Decimal("0.00"),
    ))
    return invoices


def _bank_transactions() -> list[BankTransaction]:
    """Bank transactions for the last ~3 months. Builds a realistic cash history."""
    iban = "RO49AAAA1B31007593840000"
    txns = []
    n = BTX_START

    # Starting balance implicit: 120,000 RON at start of January
    # We'll track balance_after to make it consistent.

    bal = Decimal("120000.00")

    def _add(dt, typ, amt, desc, ref=None, cpty=None, cpty_iban=None, matched=False):
        nonlocal bal, n
        if typ == TransactionType.CREDIT:
            bal += amt
        else:
            bal -= amt
        txns.append(BankTransaction(
            id=_uuid(n),
            bank_account_iban=iban,
            transaction_date=dt,
            transaction_type=typ,
            amount=amt,
            currency="RON",
            description=desc,
            reference=ref,
            counterparty_name=cpty,
            counterparty_iban=cpty_iban,
            balance_after=bal,
            is_matched=matched,
        ))
        n += 1

    C, D = TransactionType.CREDIT, TransactionType.DEBIT

    # --- January 2026 ---
    _add(date(2026, 1, 3), D, Decimal("6000.00"), "Chirie birou ianuarie", cpty="SC Office Rent SRL", matched=True)
    _add(date(2026, 1, 5), D, Decimal("2000.00"), "Hosting ianuarie", cpty="SC CloudHost SRL", matched=True)
    _add(date(2026, 1, 10), D, Decimal("45000.00"), "Salarii ianuarie", ref="SALARII-2026-01")
    _add(date(2026, 1, 15), C, Decimal("25000.00"), "Plata factura INV-2026-003", ref="INV-2026-003", cpty="SC RetailPlus SRL", matched=True)
    _add(date(2026, 1, 20), C, Decimal("45000.00"), "Plata factura INV-2026-002", ref="INV-2026-002", cpty="SC TechCorp SA", matched=True)

    # --- February 2026 ---
    _add(date(2026, 2, 2), D, Decimal("6000.00"), "Chirie birou februarie", cpty="SC Office Rent SRL", matched=True)
    _add(date(2026, 2, 3), D, Decimal("2000.00"), "Hosting februarie", cpty="SC CloudHost SRL", matched=True)
    _add(date(2026, 2, 10), D, Decimal("45000.00"), "Salarii februarie", ref="SALARII-2026-02")
    _add(date(2026, 2, 18), C, Decimal("25000.00"), "Plata factura INV-2026-004", ref="INV-2026-004", cpty="SC RetailPlus SRL", matched=True)
    _add(date(2026, 2, 25), D, Decimal("35000.00"), "Plata freelancer Ionescu", ref="MI-2026-001", cpty="PFA Ionescu Mihai", matched=True)
    _add(date(2026, 2, 28), C, Decimal("3000.00"), "Plata consultanta necunoscuta", cpty="SC Unknown Consulting SRL")  # unmatched!

    # --- March 2026 ---
    _add(date(2026, 3, 2), D, Decimal("6000.00"), "Chirie birou martie", cpty="SC Office Rent SRL")  # not yet matched
    _add(date(2026, 3, 3), D, Decimal("2000.00"), "Hosting martie", cpty="SC CloudHost SRL")
    _add(date(2026, 3, 10), D, Decimal("45000.00"), "Salarii martie", ref="SALARII-2026-03")
    _add(date(2026, 3, 15), C, Decimal("5000.00"), "Transfer intern", ref="TRANSFER-INT")  # unmatched

    return txns


async def seed(session: AsyncSession) -> None:
    """Insert all test data."""
    # Clear existing data (in reverse dependency order)
    for table in reversed(Base.metadata.sorted_tables):
        await session.execute(text(f'DELETE FROM "{table.name}"'))

    # Companies
    for c in _companies():
        session.add(c)
    await session.flush()

    # Projects
    for p in _projects():
        session.add(p)
    await session.flush()

    # Contracts
    for c in _contracts():
        session.add(c)
    await session.flush()

    # Milestones, obligations, penalties
    for m in _milestones():
        session.add(m)
    for o in _obligations():
        session.add(o)
    for p in _penalties():
        session.add(p)
    await session.flush()

    # Invoices (issued + received)
    for inv in _invoices_issued():
        session.add(inv)
    for inv in _invoices_received():
        session.add(inv)
    await session.flush()

    # Bank transactions
    for tx in _bank_transactions():
        session.add(tx)
    await session.flush()

    # Default recurring scheduled tasks
    default_tasks = [
        ScheduledTask(
            task_type="digest",
            title="Raport financiar săptămânal",
            description="Sumar săptămânal: cashflow, facturi restante, alerte active",
            schedule_type=ScheduleType.RECURRING,
            cron_expression="0 8 * * 1",  # Monday 8am
            next_run_at=datetime(2026, 3, 30, 8, 0, tzinfo=timezone.utc),
            is_active=True,
            created_by_agent=False,
            trigger_flow_type="conversation",
            trigger_message=(
                "Generează raportul financiar săptămânal: cashflow actual, facturi restante, "
                "proiecte la risc, alerte active, și acțiuni recomandate pentru săptămâna asta."
            ),
            notification_channels=["app", "email"],
        ),
        ScheduledTask(
            task_type="alert_eval",
            title="Verificare zilnică alerte",
            description="Evaluează toate regulile de alertare zilnic",
            schedule_type=ScheduleType.RECURRING,
            cron_expression="0 7 * * *",  # Daily 7am
            next_run_at=datetime(2026, 3, 27, 7, 0, tzinfo=timezone.utc),
            is_active=True,
            created_by_agent=False,
            trigger_flow_type="alert_check",
            trigger_message="Evaluează toate alertele: facturi restante, contracte expirante, milestone-uri, buget.",
            notification_channels=["app"],
        ),
        ScheduledTask(
            task_type="digest",
            title="Raport profitabilitate lunar",
            description="Analiză lunară P&L pe proiecte și global",
            schedule_type=ScheduleType.RECURRING,
            cron_expression="0 9 1 * *",  # 1st of month 9am
            next_run_at=datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc),
            is_active=True,
            created_by_agent=False,
            trigger_flow_type="conversation",
            trigger_message=(
                "Generează raportul lunar de profitabilitate: venituri, costuri, profit global, "
                "marjă pe fiecare proiect, și comparație cu luna anterioară."
            ),
            notification_channels=["app", "email"],
        ),
        ScheduledTask(
            task_type="check",
            title="Proiecție cashflow săptămânală",
            description="Actualizare proiecție cashflow pe 90 zile",
            schedule_type=ScheduleType.RECURRING,
            cron_expression="0 10 * * 3",  # Wednesday 10am
            next_run_at=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc),
            is_active=True,
            created_by_agent=False,
            trigger_flow_type="conversation",
            trigger_message=(
                "Analizează cashflow-ul: cash disponibil, proiecție 30/60/90 zile, "
                "burn rate, și identifică riscuri de lichiditate."
            ),
            notification_channels=["app"],
        ),
    ]
    for task in default_tasks:
        session.add(task)
    await session.flush()

    await session.commit()

    # Print summary
    print("=== Seed Complete ===")
    print("Companies: 7")
    print("Projects: 4")
    print("Contracts: 6 (4 client + 2 supplier)")
    print("Milestones: 4 (2 completed, 1 overdue, 1 future)")
    print("Invoices issued: 9 (5 paid, 3 overdue, 1 sent)")
    print("Invoices received: 7 (5 paid, 2 due)")
    print(f"Bank transactions: {len(_bank_transactions())}")
    print(f"Scheduled tasks: {len(default_tasks)} (recurring)")

    # Expected financials
    txns = _bank_transactions()
    final_bal = txns[-1].balance_after
    print("\n--- Expected Financials (as of 2026-03-26) ---")
    print(f"Bank balance: {final_bal:,.2f} RON")
    print("Receivables (overdue): 55,000 RON (RetailPlus 25k + StartupVibe 30k)")
    print("Receivables (not due): 15,000 RON (TechCorp due Apr 15)")
    print("Payables (due): 8,000 RON (CloudHost 2k + OfficeRent 6k)")


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
