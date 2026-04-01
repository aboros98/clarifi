# Clarifi — How It Works

## What Clarifi Does

Clarifi is an AI financial assistant for Romanian services companies. It replaces manual cashflow spreadsheets, invoice reminders, and ad-hoc financial reporting with a conversational agent that has real-time access to your financial data.

You can ask it in Romanian or English:
- "Câți bani am?" → queries your bank balance and projections
- "Cine îmi datorează bani?" → shows aging receivables by client
- "Ce riscuri am?" → comprehensive risk analysis with quantified impact
- "Ce trebuie să fac săptămâna asta?" → prioritized action plan

## Architecture

```mermaid
graph TB
    subgraph "User Interfaces"
        WEB[Next.js Dashboard]
        TG[Telegram Bot]
        API[REST API]
    end

    subgraph "Agent Core (1 LLM call per turn)"
        SL["① Skill Loader<br/>(keyword match, no LLM)"]
        MR["② memU Retrieve<br/>(past context)"]
        RA["③ Gemini ReAct Agent<br/>(tool-calling)"]
        MS["④ memU Save<br/>(learn patterns)"]
    end

    subgraph "Skills (.md files)"
        S1[cashflow.md]
        S2[receivables.md]
        S3[profitability.md]
        S4[alerts.md]
        S5[10 more...]
    end

    subgraph "Tools (Python @tool functions)"
        T1[query_cashflow]
        T2[query_receivables]
        T3[check_contract_status]
        T4[run_payment_matching]
        T5[20 more...]
    end

    subgraph "Data Layer"
        DB[(Supabase<br/>PostgreSQL)]
        MEMU[(memU<br/>pgvector)]
    end

    WEB --> SL
    TG --> SL
    API --> SL

    SL -->|"loads relevant .md"| MR
    MR -->|"injects past context"| RA
    RA -->|"calls tools"| T1 & T2 & T3 & T4
    RA --> MS
    T1 & T2 & T3 & T4 --> DB
    MR --> MEMU
    MS --> MEMU
```

## The Request Flow (step by step)

### 1. User Sends a Message

```
User: "Ce riscuri am?"
```

### 2. Skill Loader (Python keyword matching — NO LLM call)

The skill loader scans the message for keywords and matches against `.md` skill files:

- "riscuri" matches `risk_analysis.md` (keyword: "risc")
- This loads the skill instructions + binds only the relevant tools

**Cost: 0 tokens.** This replaces a traditional LLM routing call.

### 3. memU Retrieve (if enabled)

memU searches its vector database for relevant past context:

```
→ "User worried about StartupVibe last week"
→ "Company has 4 active projects, PRJ-002 is over budget"
→ "User prefers concise summaries"
```

This context is injected into the system prompt. The agent now **remembers** past conversations.

### 4. Gemini ReAct Agent (1 LLM call with tool-calling)

The agent receives:
- **System prompt**: rules, Romanian formatting, response structure
- **Skill instructions**: from `risk_analysis.md` — which tools to call and how
- **memU context**: past patterns and preferences
- **Available tools**: `score_client_risk`, `detect_unissued_invoices`, `project_cashflow_daily`, `query_profitability`, `query_alerts`

The agent reasons and calls tools:

```
Thought: User asks about risks. I'll call all risk tools.
Action: score_client_risk()
Result: {clients: [{name: "StartupVibe", risk_score: 72, overdue: 30000}, ...]}

Action: project_cashflow_daily(days=60)
Result: {first_negative_day: "2026-05-15", risk_level: "warning"}

Action: query_profitability()
Result: {by_project: [{name: "Mobile App", margin_pct: -1.0}, ...]}

Answer: "Nivel general de risc: 🔴 RIDICAT..."
```

### 5. memU Save (async, non-blocking)

After the response, memU stores the conversation:

```
memU learns:
- "StartupVibe risk score is 72/100 as of March 2026"
- "User was concerned about financial risks"
- "Mobile App project is at negative margin"
```

Next time the user asks anything related, memU will surface this context.

### 6. Decision Logged

Every tool call is automatically recorded in `decision_log`:

```json
{
  "tool_name": "score_client_risk",
  "tool_input": {},
  "tool_output": {"clients": [...]},
  "duration_ms": 45,
  "timestamp": "2026-03-28T10:30:00Z"
}
```

Visible in the dashboard at `/decisions`.

## How the Cron/Scheduler Works

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant DB as scheduled_tasks
    participant S as Scheduler Loop
    participant N as Notification

    Note over U,A: 1. User uploads a contract

    U->>A: "Am un contract nou: CTR-2025-001"
    A->>A: extract_fields() → milestones found
    A->>U: "Am extras 4 milestone-uri. Corect?"
    U->>A: "Da"
    A->>A: save_extracted_data()
    A->>DB: create_reminder("Backend Dev due", 2026-03-23)
    A->>DB: create_reminder("Final Delivery due", 2026-06-08)
    A->>DB: create_reminder("Contract expires", 2026-05-31)
    A->>U: "Salvat ✅ + 3 remindere programate"

    Note over S,DB: 2. Scheduler polls every 60s (inside FastAPI)

    loop Every 60 seconds
        S->>DB: SELECT WHERE is_active=true AND next_run_at <= NOW()
    end

    Note over S: 2026-03-23 arrives...

    S->>DB: Found: "Backend Dev due"
    S->>A: HumanMessage("Milestone Backend Dev scadent azi...")
    A->>A: Runs tools, generates response
    S->>DB: INSERT INTO scheduler_runs (status=success)
    S->>N: Send notification
    S->>DB: UPDATE scheduled_task SET is_active=false (one-shot)
```

### Task Types

| Type | Schedule | Example |
|------|----------|---------|
| **ONE_SHOT** | Fires once at `next_run_at`, then deactivates | Invoice due-date follow-up |
| **RECURRING** | Fires at `next_run_at`, then computes next from `cron_expression` | Weekly digest (Mon 8am) |

### Pre-configured Recurring Tasks

| Task | Cron | What it does |
|------|------|-------------|
| Daily Alert Check | `0 7 * * *` | Evaluates all alert rules |
| Weekly Digest | `0 8 * * 1` | Cashflow + receivables + actions summary |
| Monthly P&L | `0 9 1 * *` | Profitability report by project |
| Cashflow Projection | `0 10 * * 3` | 90-day forward projection |

### Agent Auto-Created Tasks (after document ingestion)

| Trigger | Reminder |
|---------|----------|
| Contract saved with milestones | 7 days before each milestone due date |
| Contract saved with end_date | 30 days before expiry |
| Invoice (issued) saved with due_date | On the due date |

## How memU Works (Self-Hosted)

```mermaid
graph LR
    subgraph "memU (cloned from GitHub)"
        ML[MemUService]
        VEC[pgvector embeddings]
        CAT[Auto-categories]
    end

    subgraph "Supabase PostgreSQL"
        PG[(PostgreSQL + pgvector)]
    end

    subgraph "Gemini"
        LLM[gemini-2.5-flash-lite]
    end

    ML -->|stores memories| PG
    ML -->|vector search| VEC
    VEC --> PG
    ML -->|extraction & embedding| LLM
    CAT -->|auto-organized topics| PG
```

### Setup

```bash
# 1. Clone memU
git clone https://github.com/NevaMind-AI/memU.git
pip install -e './memU[postgres]'

# 2. Point DATABASE_URL to Supabase
DATABASE_URL=postgresql+asyncpg://postgres:pass@db.xxx.supabase.co:5432/postgres

# 3. Enable in .env
MEMU_ENABLED=true
# Uses same GOOGLE_API_KEY — no extra key needed
```

### What memU Stores

| Layer | Content | Example |
|-------|---------|---------|
| **Resource** | Raw conversations | "User asked about cashflow, agent responded with 24.000 lei" |
| **Item** | Extracted facts | "StartupVibe has a pattern of 15-30 day late payments" |
| **Category** | Auto-topics | "Client Risks", "Cash Management", "Project PRJ-002" |

### How It Makes the Agent Smarter

**Week 1:** Agent answers factually from tools only.
**Week 4:** memU has learned:
- "User always checks cashflow on Monday mornings"
- "StartupVibe consistently pays 20+ days late"
- "User worries most about PRJ-002 budget"
- "User prefers summaries with action items, not raw numbers"

**Week 8:** Agent proactively mentions:
- "StartupVibe are din nou factură restantă — pattern consistent"
- "Săptămâna trecută ai menționat că vrei să reduci costurile pe PRJ-002"

## Skills Architecture

Skills are `.md` files — editable without code changes:

```
src/clarifi/skills/
├── cashflow.md            # "Câți bani am?"
├── receivables.md         # "Cine îmi datorează?"
├── profitability.md       # "Care e profitul?"
├── contracts.md           # "Ce contracte am?"
├── alerts.md              # "Ce alerte am?"
├── risk_analysis.md       # "Ce riscuri am?"
├── scenarios.md           # "Dacă angajez pe cineva?"
├── scheduling.md          # "Amintește-mi în 7 zile"
├── document_ingestion.md  # "Procesează acest document"
├── weekly_actions.md      # "Ce trebuie să fac?"
├── data_verification.md   # "Corectează datele"
└── correlation.md         # "S-a facturat tot?"
```

Each skill has:
- **Keywords** — for automatic selection (no LLM needed)
- **Tools** — which Python tools to bind
- **Instructions** — step-by-step guide for the LLM
- **Response Format** — how to structure the answer
- **Examples** — few-shot examples the LLM follows

### Why .md Files Instead of Code?

1. **Non-developers can edit** — the business owner can tweak instructions
2. **No deploy needed** — change a file, restart server
3. **LLM-native** — the instructions ARE the prompt, no translation layer
4. **Testable** — keyword matching has unit tests
5. **Cheap** — injecting 500 tokens of skill context costs nothing vs a separate LLM routing call

## Tools Inventory (23 total)

| Category | Tool | What it queries |
|----------|------|----------------|
| **Finance** | `query_cashflow` | Bank balance, 30/90-day projections |
| | `query_receivables` | Unpaid invoices with aging |
| | `query_profitability` | Revenue vs costs per project |
| **Contracts** | `query_contracts` | Active/expiring contracts |
| | `query_milestones` | Upcoming/overdue milestones |
| **Correlation** | `check_contract_status` | Contract → Invoice → Payment chain |
| | `reconcile_project` | Budget vs invoiced vs collected |
| **Matching** | `run_payment_matching` | Match bank transactions to invoices |
| | `confirm_match` | Confirm a match, update statuses |
| **Alerts** | `query_alerts` | Real-time overdue/expiring alerts |
| | `detect_unissued_invoices` | Milestones completed but not invoiced |
| | `project_cashflow_daily` | Day-by-day cashflow projection |
| | `score_client_risk` | Risk score 0-100 per client |
| **Documents** | `ingest_document` | Parse PDF/DOCX/image/CSV |
| | `extract_fields` | LLM extraction with confidence scores |
| | `save_extracted_data` | Save to DB after user confirmation |
| **Feedback** | `confirm_data` | Mark as verified |
| | `correct_data` | Apply corrections |
| | `mark_stale` | Flag as outdated |
| | `check_freshness` | Find unverified data |
| **Scheduling** | `create_reminder` | One-shot or recurring |
| | `list_reminders` | Show upcoming tasks |
| | `cancel_reminder` | Deactivate a task |

## Data Freshness

Every extracted data point has a freshness status:

| Status | Meaning | Agent Behavior |
|--------|---------|---------------|
| `unverified` | Extracted by AI, not confirmed | Shows ⚠️ warning |
| `verified` | User confirmed | Uses with confidence |
| `stale` | Marked as outdated | Warns + suggests re-upload |

The agent proactively checks freshness and prompts the user:
- "Aceste date au fost extrase acum 10 zile și nu au fost confirmate. Vrei să le verifici?"
