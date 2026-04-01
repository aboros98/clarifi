# Clarifi — Setup, Build, Test, Operationalize

## Quick Numbers

| Metric | Count |
|--------|-------|
| Tools | 36 |
| Skills | 17 |
| DB Tables | 26 |
| API Routes | 33 |
| Tests | 51 pass, 5 skip |

---

## 1. Prerequisites

- **Python 3.12+** (3.12 or 3.13 recommended)
- **Node.js 20+** (for frontend)
- **Google API Key** with Generative AI API enabled
- Optional: Supabase project (production DB + storage)
- Optional: memU clone (long-term agent memory)

---

## 2. Local Development Setup

### 2.1 Install Backend

```bash
git clone <repo> clarifi && cd clarifi
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2.2 Configure

```bash
cp .env.example .env
# Edit .env — minimum required:
# GOOGLE_API_KEY=your-key
```

### 2.3 Create Database + Seed Test Data

```bash
python -m scripts.seed_db
```

Creates `clarifi.db` (SQLite) with:
- 7 companies, 4 projects, 6 contracts, 16 invoices, 15 bank transactions, 4 scheduled tasks

### 2.4 Run Tests

```bash
# Unit + integration tests (no API key needed)
pytest tests/ -v

# With API key — runs e2e agent tests
pytest tests/test_agent_e2e.py -v -s
```

### 2.5 Start Backend

```bash
uvicorn clarifi.main:app --reload --port 8000
```

On startup you'll see:
```
INFO: Clarifi
INFO: Scheduler started (polling every 60s)
INFO: Watcher started: ./inbox (poll every 10s)
```

Three background systems start automatically:
- **Scheduler** — polls `scheduled_tasks` every 60s, fires due reminders
- **Watcher** — polls `inbox/` every 10s, triggers background agent for new files

### 2.6 Start Frontend

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:3000

### 2.7 Test the Agent

Chat: http://localhost:3000/chat
```
"Câți bani am?"
"Cine îmi datorează bani?"
"Ce riscuri am?"
"Ce trebuie să fac săptămâna asta?"
```

API docs: http://localhost:8000/docs

---

## 3. How It Works

### Two Agent Modes

```
BACKGROUND AGENT (silent, automatic)
  Triggers: file watcher, upload endpoint, cron scheduler
  Behavior: processes silently, saves as unverified, never asks user
  Enforced by: mode="background" in AgentState →
    - Forces background_processing skill (skips LLM routing)
    - Removes ask_user tool (cannot ask questions)
    - Adds "MOD BACKGROUND" to system prompt

FACING AGENT (conversational)
  Triggers: user chat (WebSocket or POST)
  Behavior: talks naturally in Romanian, asks for confirmation
  Enforced by: mode="interactive" (default) →
    - LLM selects skills based on intent
    - All 36 tools available including ask_user
    - Natural conversation with company context
```

### Document Flow

```
User drops file into inbox/ (or uploads via UI)
  ↓
Watcher detects → triggers background agent (mode="background")
  ↓
Agent: ingest_document → extract_fields → save_extracted_data(confirmed=false)
  ↓
Agent: create_folder → move_file (organizes into virtual folder tree)
  ↓
Agent: create_reminder (for deadlines found in document)
  ↓
Agent: write_trace (leaves analysis notes on the folder)
  ↓
Original file deleted from inbox/ (data safe in DB + storage/)
  ↓
User opens dashboard → sees organized files, unverified data, traces
  ↓
User confirms/corrects data via chat → agent updates records
```

### Virtual Folder Tree

Documents are organized in a virtual tree in the database, not filesystem:

```
/Contracte/TechCorp/2026/
/Facturi Emise/2026/Martie/
/Facturi Primite/2026/
/Extrase Bancare/BCR/
/Neprocesat/
```

Each folder can have a **trace** — the agent's analysis notes from last time it processed the folder.

### Scheduler / Reminders

Three sources of reminders:
1. **User creates directly**: "Amintește-mi să sun TechCorp vineri"
2. **Agent creates after document analysis**: extracts due dates → auto-creates reminders
3. **Agent creates when detecting risks**: overdue invoices → suggests follow-up

When a reminder fires:
1. Scheduler feeds `trigger_message` to the agent
2. Agent calls tools, gets fresh data
3. Agent composes a natural notification
4. Sends via Telegram (if configured)

---

## 4. Production Deploy (Vercel + Railway + Supabase)

### 4.1 Supabase

1. Create project at https://supabase.com
2. Enable pgvector: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Note connection string: `postgresql+asyncpg://postgres:PASS@db.XXX.supabase.co:5432/postgres`

### 4.2 Railway (Backend)

1. Deploy from GitHub at https://railway.app
2. Set environment variables:
```
DATABASE_URL=postgresql+asyncpg://postgres:PASS@db.XXX.supabase.co:5432/postgres
GOOGLE_API_KEY=your-key
LLM_MODEL=gemini-2.5-flash-lite
LLM_EXTRACTION_MODEL=gemini-2.5-flash
CORS_ORIGINS=https://your-app.vercel.app
SUPABASE_URL=https://XXX.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
```

3. Create tables:
```bash
railway run python -c "
import asyncio
from clarifi.db.session import engine
from clarifi.models import Base
async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(create())
"
```

### 4.3 Vercel (Frontend)

1. Import repo, set Root Directory = `frontend`
2. Set environment variables:
```
NEXT_PUBLIC_API_URL=https://your-api.up.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://XXX.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 4.4 Onboarding (First Use)

```bash
curl -X POST https://your-api/api/onboarding \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "SC Digital Solutions SRL",
    "tax_id": "RO12345678",
    "city": "București",
    "user_name": "Sandu Babasan",
    "user_role": "owner"
  }'
```

---

## 5. Testing Guide

### Unit Tests (no API key needed)

```bash
pytest tests/test_validators.py -v      # 18 tests — Romanian format validation
pytest tests/test_skill_loader.py -v    # 8 tests — skill infrastructure
pytest tests/test_tools.py -v           # 11 tests — original tools against seed data
pytest tests/test_new_tools.py -v       # 13 tests — new tools, save, auto-create
```

### Structural Tests

```bash
# Verify all imports work
python -c "from clarifi.main import app; print('OK')"

# Verify background mode is structurally enforced
python -c "
import asyncio
from clarifi.agent.graph import skill_loader
result = asyncio.run(skill_loader({'messages': [], 'mode': 'background'}))
assert 'background' in result['skill_context'].lower()
print('Background mode: OK')
"
```

### E2E Tests (requires API key)

```bash
# Set real API key in .env first
pytest tests/test_agent_e2e.py -v -s
```

Tests: cashflow query, receivables query, alerts, weekly plan, profitability.

### Manual Test Checklist

1. **Chat**: Ask "Câți bani am?" → should return actual/expected/committed cashflow
2. **Upload**: Drop a PDF invoice in `inbox/` → watcher processes it → check `/api/files/tree`
3. **Reminders**: Ask "Amintește-mi mâine să verific facturile" → check `/api/scheduler/tasks`
4. **Organize**: Ask "Organizează-mi documentele" → agent creates folders + moves files
5. **Traces**: Ask "Ce ai analizat în /Facturi?" → agent reads trace from folder

---

## 6. Monitoring

### Logs

```bash
# Scheduler
grep "Scheduler" logs  # "Scheduler started", "Executing:", "Processed"

# Watcher
grep "Watcher" logs    # "Watcher started", "New file:", "Done:"

# Background agent
grep "BACKGROUND" logs  # Background processing events
```

### API Endpoints for Monitoring

```
GET /health                     # Service health
GET /api/scheduler/tasks        # All scheduled tasks
GET /api/scheduler/runs         # Execution history
GET /api/decisions              # Agent decision log (all tool calls)
GET /api/files/tree             # Virtual folder structure
GET /api/settings               # Current configuration
GET /dashboard/kpis             # Real-time financial KPIs
```

---

## 7. Cost Estimate

| Service | Plan | Cost/month |
|---------|------|------------|
| Supabase | Free (500MB) | $0 |
| Railway | Starter | ~$5-10 |
| Vercel | Hobby | $0 |
| Gemini API | Flash Lite | ~$2-5 |
| **Total** | | **~$7-15** |

---

## 8. Architecture Summary

```
36 tools | 17 skills | 26 tables | 33 routes | 51 tests

Background Agent (silent)          Facing Agent (conversational)
├── File watcher (inbox/)          ├── WebSocket chat
├── Upload auto-process            ├── POST /chat
├── Scheduler (cron)               ├── POST /documents/upload
│                                  │
├── mode="background"              ├── mode="interactive"
├── Forces background skill        ├── LLM selects skills
├── ask_user REMOVED               ├── All 36 tools
├── Saves as unverified            ├── Asks for confirmation
├── 5min timeout                   ├── Natural Romanian
└── No conversation                └── Company context injected
```
