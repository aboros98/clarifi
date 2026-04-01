# Clarifi — Architecture

AI financial assistant for Romanian services companies. Provides cashflow visibility, contract tracking, invoice management, alerts, and decision support through a conversational interface.

## High-Level Overview

```mermaid
graph TB
    User([User]) -->|message| API[FastAPI API]
    User -->|drops files| Inbox[📁 Inbox Folder]

    API --> Graph[LangGraph Agent]
    Inbox --> Watcher[File Watcher]
    Watcher -->|auto-ingest| Graph

    Graph --> SL[Skill Loader]
    SL -->|keyword match| Skills[".md Skill Files"]
    SL --> Agent[ReAct Agent]
    Agent -->|tool calls| Tools[Tool Functions]
    Tools -->|SQL queries| DB[(SQLite / PostgreSQL)]
    Agent -->|response| User

    Scheduler[⏰ Scheduler] -->|triggers| Graph

    style Skills fill:#e1f5fe
    style Tools fill:#f3e5f5
    style DB fill:#e8f5e9
```

## Core Architecture: Skills + Tools + ReAct Agent

Clarifi uses a **single LLM call per user turn**, not the traditional router → executor → synthesizer pattern (which costs 2-3 calls).

```mermaid
sequenceDiagram
    participant U as User
    participant SL as Skill Loader
    participant LLM as Gemini (ReAct)
    participant T as Tools
    participant DB as Database

    U->>SL: "Câți bani am?"
    Note over SL: Keyword match (no LLM)<br/>Matches: cashflow.md

    SL->>LLM: System prompt + cashflow.md + tools
    LLM->>T: call query_cashflow()
    T->>DB: SELECT balance, invoices...
    DB-->>T: data
    T-->>LLM: {cash: 24000, inflows: 55000, ...}
    LLM-->>U: "Ai 24.000 lei disponibili..."
```

### Why this design?

| Approach | LLM Calls | Cost | Latency |
|----------|-----------|------|---------|
| Router → Skill → Synthesizer | 2-3 | High | Slow |
| **Clarifi (Skill + ReAct)** | **1** | **Low** | **Fast** |

## Skills (`.md` files)

Skills are markdown files that tell the LLM what tools to use and how to respond. They are loaded into the LLM's context based on keyword matching — **no LLM call needed for routing**.

```mermaid
graph LR
    MSG[User Message] --> KW{Keyword<br/>Matching}
    KW -->|"bani, cash"| CF[cashflow.md]
    KW -->|"datorează, overdue"| RV[receivables.md]
    KW -->|"profit, marjă"| PR[profitability.md]
    KW -->|"contract, milestone"| CT[contracts.md]
    KW -->|"alertă, atenție"| AL[alerts.md]
    KW -->|"dacă, what if"| SC[scenarios.md]
    KW -->|"amintește, remind"| SH[scheduling.md]
    KW -->|"document, factură"| DI[document_ingestion.md]
    KW -->|"săptămâna, plan"| WA[weekly_actions.md]
    KW -->|"corect, verifică"| DV[data_verification.md]

    CF --> CTX[System Prompt + Skill Context]
    RV --> CTX
    CTX --> LLM[Gemini ReAct Agent]

    style CF fill:#e1f5fe
    style RV fill:#e1f5fe
    style PR fill:#e1f5fe
    style CT fill:#e1f5fe
    style AL fill:#e1f5fe
```

Each `.md` file contains:
- **Keywords** — for matching (Romanian + English)
- **Tools** — which tools to bind for this skill
- **Instructions** — what the LLM should do
- **Response format** — how to format the answer
- **Examples** — few-shot examples of good responses

## Tools (Python functions)

Tools are `@tool` decorated async functions that the LLM calls via LangChain tool-calling. They handle all database queries and business logic.

```mermaid
graph TB
    subgraph Finance
        QC[query_cashflow]
        QR[query_receivables]
        QP[query_profitability]
    end

    subgraph Contracts
        QCT[query_contracts]
        QM[query_milestones]
    end

    subgraph Documents
        ID[ingest_document]
        SE[save_extracted_data]
    end

    subgraph Feedback
        CD[confirm_data]
        CR[correct_data]
        MS[mark_stale]
        CF[check_freshness]
    end

    subgraph Scheduling
        CRM[create_reminder]
        LR[list_reminders]
        CLR[cancel_reminder]
    end

    subgraph Alerts
        QA[query_alerts]
    end

    Finance --> DB[(Database)]
    Contracts --> DB
    Documents --> DB
    Feedback --> DB
    Scheduling --> DB
    Alerts --> DB
```

## Data Model

```mermaid
erDiagram
    Company ||--o{ Contract : counterparty
    Company ||--o{ Invoice : issuer/recipient
    Project ||--o{ Contract : contains
    Project ||--o{ Invoice : tracks
    Contract ||--o{ ContractMilestone : has
    Contract ||--o{ ContractObligation : has
    Contract ||--o{ ContractPenalty : has
    Contract ||--o{ Invoice : generates
    Contract ||--o{ Estimate : links
    Invoice ||--o{ InvoiceLineItem : contains
    Invoice ||--o{ PaymentInvoiceMatch : matched_to
    BankTransaction ||--o{ PaymentInvoiceMatch : matches
    Document ||--o{ DocumentProcessingLog : logs

    Company {
        string id PK
        string legal_name
        string tax_id UK
        enum role "client/supplier/own"
    }
    Contract {
        string id PK
        string contract_number UK
        decimal total_value
        date start_date
        date end_date
        enum status
    }
    Invoice {
        string id PK
        string invoice_number
        enum direction "issued/received"
        enum status
        decimal total_amount
        decimal amount_remaining
        date due_date
        string freshness_status
    }
    BankTransaction {
        string id PK
        string bank_account_iban
        date transaction_date
        decimal amount
        decimal balance_after
        bool is_matched
    }
    Project {
        string id PK
        string project_code UK
        string name
        decimal budget
        enum status
    }
```

## Data Freshness System

Every key entity tracks whether it has been verified by the user:

```mermaid
stateDiagram-v2
    [*] --> Unverified: Document extracted
    Unverified --> Verified: User confirms
    Unverified --> Stale: 7 days without confirmation
    Verified --> Stale: Data becomes outdated
    Stale --> Verified: User re-confirms
    Stale --> [*]: Data discarded

    note right of Unverified
        Agent mentions: "⚠️ Date neconfirmate"
    end note
    note right of Verified
        Agent uses data with confidence
    end note
    note right of Stale
        Agent warns: "Date posibil depășite"
    end note
```

## Document Ingestion Flow

```mermaid
sequenceDiagram
    participant U as User / Watcher
    participant A as Agent
    participant T as ingest_document
    participant DB as Database

    U->>A: "Am primit o factură nouă" + file
    A->>T: ingest_document(file_path)
    T->>T: Parse (PDF/DOCX/OCR)
    T->>DB: Check duplicate (SHA-256)
    T->>DB: Save Document record
    T-->>A: {text_preview, document_id}

    Note over A: LLM extracts structured<br/>fields from text

    A-->>U: "Am extras:<br/>Nr: INV-2026-010<br/>Sumă: 15.000 lei<br/>Datele sunt corecte?"

    U->>A: "Da, corect"
    A->>T: save_extracted_data(confirmed=true)
    T->>DB: Save Invoice + link to contract
    A-->>U: "Factură salvată ✅"
```

## File Discovery

```mermaid
graph LR
    subgraph File Watcher
        W[watcher.py] -->|polls every 10s| INBOX[📁 inbox/]
    end

    INBOX -->|new file| W
    W -->|ingest_document| DB[(Database)]
    W -->|success| PROC[📁 processed/]
    W -->|error| FAIL[📁 failed/]
```

## Scheduled Tasks

```mermaid
graph TB
    subgraph Pre-configured Recurring
        D[Daily Alert Check<br/>07:00]
        WK[Weekly Digest<br/>Monday 08:00]
        MO[Monthly P&L<br/>1st of month]
        WD[Cashflow Projection<br/>Wednesday 10:00]
    end

    subgraph Auto-created by Agent
        MR[Milestone Reminders<br/>7 days before due]
        IR[Invoice Follow-ups<br/>on due date]
        CR[Contract Expiry<br/>30 days before]
    end

    D --> S[⏰ Scheduler Worker]
    WK --> S
    MO --> S
    MR --> S
    IR --> S

    S -->|triggers| Agent[ReAct Agent]
    Agent -->|notification| User([User])
```

## Project Structure

```
clarifi/
├── src/clarifi/
│   ├── config.py              # Settings (pydantic-settings, .env)
│   ├── llm.py                 # LLM factory (cached singleton)
│   ├── main.py                # FastAPI application
│   ├── agent/
│   │   ├── graph.py           # LangGraph: skill_loader → agent → END
│   │   └── prompts.py         # System prompt (Romanian context)
│   ├── skills/                # .md files loaded into LLM context
│   │   ├── loader.py          # Keyword-based skill selector
│   │   ├── cashflow.md
│   │   ├── receivables.md
│   │   ├── profitability.md
│   │   ├── contracts.md
│   │   ├── alerts.md
│   │   ├── risk_analysis.md
│   │   ├── scenarios.md
│   │   ├── scheduling.md
│   │   ├── document_ingestion.md
│   │   ├── weekly_actions.md
│   │   └── data_verification.md
│   ├── tools/                 # @tool functions (DB queries)
│   │   ├── finance.py         # cashflow, receivables, profitability
│   │   ├── contracts.py       # contracts, milestones
│   │   ├── alerts.py          # alerts
│   │   ├── documents.py       # ingest, save
│   │   ├── feedback.py        # confirm, correct, mark_stale
│   │   └── scheduling.py      # reminders
│   ├── models/                # SQLAlchemy ORM (18 tables)
│   ├── db/session.py          # Async session factory
│   ├── ingestion/             # Document parsers (PDF, DOCX, OCR)
│   ├── discovery/watcher.py   # Folder watcher
│   └── api/                   # FastAPI endpoints
├── scripts/
│   ├── seed_db.py             # Test data (SC Digital Solutions SRL)
│   ├── run_scheduler.py       # Background scheduler worker
│   └── run_watcher.py         # File watcher daemon
└── tests/                     # 25 tests (skill loader + tools)
```

## Frontend (Next.js)

```mermaid
graph TB
    subgraph "Next.js App (n8n-style)"
        HOME[Dashboard<br/>KPI Cards + Alerts]
        CHAT[Agent Chat<br/>Streaming + Tool Calls]
        JOBS[Jobs & Scheduler<br/>Tasks + Run History]
        FOLDERS[Folder Manager<br/>Drive + Local]
        ALERTS[Alert Center<br/>Severity Groups]
        DECISIONS[Decision Log<br/>Audit Timeline]
        SETTINGS[Settings<br/>Integrations]
    end

    HOME --> API[FastAPI Backend]
    CHAT --> API
    JOBS --> API
    FOLDERS --> API
    ALERTS --> API
    DECISIONS --> API

    subgraph Auth
        LOGIN[Supabase Auth]
    end

    LOGIN --> HOME
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 15 + React 19 + Tailwind CSS 4 |
| Auth | Supabase Auth (email, Google OAuth) |
| Agent Framework | LangGraph (ReAct prebuilt agent) |
| LLM | Google Gemini (via langchain-google-genai) |
| API | FastAPI (REST + WebSocket) |
| Database | SQLAlchemy async (SQLite dev / PostgreSQL prod) |
| Document Parsing | pypdf, python-docx, pytesseract (OCR) |
| Task Scheduling | croniter + custom scheduler worker |
| File Discovery | watchfiles + custom watcher |
| Planned | Google Drive API, Telegram Bot API |
