# Clarifi — Architecture

AI financial assistant for Romanian services companies. Provides cashflow visibility, contract tracking, invoice management, alerts, and decision support through a conversational interface.

---

## How Scheduled Tasks (Cron Jobs) Work

### Where they live
Stored in the `scheduled_tasks` table (SQLite local / Supabase PostgreSQL prod). Each task has: title, cron expression, trigger message (what the agent runs), `user_id`, notification channels.

### When they run
The scheduler is an **embedded asyncio loop** inside the FastAPI process — not a separate service:

```
FastAPI starts → lifespan creates 2 background tasks:
  1. run_scheduler_loop()  — polls DB every 60 seconds
  2. watch_directory()     — polls inbox/ every 10 seconds
```

**Every 60 seconds:**
1. Query: `SELECT * FROM scheduled_tasks WHERE is_active=true AND next_run_at <= NOW()`
2. For each due task:
   - Run the agent graph with `task.trigger_message` as input + `task.user_id`
   - Record result in `scheduler_runs` (success/failed, duration, error)
   - If recurring: compute `next_run_at` from cron expression via `croniter`
   - If one_shot: deactivate
3. Send notifications (Telegram if configured)

### How tasks are created
The agent creates them via `create_reminder` tool during conversations:
```
User: "Aminteste-mi sa verific facturile in fiecare luni"
Agent: create_reminder(title="Verificare facturi", cron="0 9 * * 1", ...)
```

Default seed tasks:
- Verificare zilnica alerte (daily 08:00)
- Raport financiar saptamanal (Monday 09:00)
- Reconciliere plati (daily 10:00)
- Verificare contracte (1st of month 08:00)

### Cron expression format
Standard 5-field: `minute hour day_of_month month day_of_week`
```
0 8 * * *     = daily at 08:00
0 9 * * 1     = every Monday at 09:00
0 10 1 * *    = 1st of month at 10:00
*/30 * * * *  = every 30 minutes
```

### On Railway (production)
Railway runs a single `web` process:
```
Procfile: web: uvicorn clarifi.main:app --host 0.0.0.0 --port $PORT
```

The scheduler runs **inside this same process**:
- No separate worker needed
- Railway keeps the container running 24/7
- Tasks survive deploys (they're in the DB)
- After restart, scheduler picks up due tasks on the next 60s poll
- Tradeoff: if process restarts mid-execution, that run is lost (no retry)

---

## Per-User Isolation

### What's isolated per user

| Data | Column | Notes |
|------|--------|-------|
| Documents | `documents.user_id` | Who uploaded it |
| Scheduled Tasks | `scheduled_tasks.user_id` | Who it runs for |
| Virtual Folders | `virtual_folders.user_id` | Folder ownership |
| Agent Sessions | `agent_sessions.user_id` | Conversation history |
| User Profile | `user_profiles.user_id` | Links to active company |
| Company Links | `user_company_links.user_id` | Multi-company support |

### How user_id flows

```
HTTP Request
  → Supabase JWT in Authorization header
  → clarifi.auth.get_user_id() extracts `sub` claim
  → Passed to graph as AgentState.user_id
  → Used for:
    - Company context (which company is active)
    - memU memory scoping (per-user retrieval/storage)
    - Checkpointer thread prefix ({user_id}:{thread_id})
    - Document ownership
```

### Shared across all users (company-level)
Companies, Invoices, Contracts, Bank Transactions, Alerts, Decision Log — multiple users (owner + accountant) see the same financial data for their company.

---

## Document Storage

### Upload flow
```
User uploads file
  → Temp file on disk
  → Agent processes: extract → organize → create reminders
  → Stored in: ./storage/ (dev) or Supabase Storage (prod)
  → Metadata in `documents` table with user_id
  → Virtual folder entry created
  → Temp file deleted
```

### File watcher (inbox/)
```
File in inbox/ → detected (10s poll) → background agent → file deleted from inbox
```
Supported: `.pdf .docx .doc .txt .png .jpg .jpeg .tiff .csv .xlsx .xls`

---

## Agent Graph

```
START → skill_loader → memory_retriever → react_agent → memory_saver → END
```

1. **skill_loader**: LLM picks 1-3 skills from 17 `.md` files (background mode forces `background_processing.md`)
2. **memory_retriever**: Fetches relevant past conversations from memU (if enabled + PostgreSQL)
3. **react_agent**: Gemini call with filtered tools + skill context + company context + memory
4. **memory_saver**: Fire-and-forget store to memU for future recall

### Tool filtering
The agent only gets tools needed by the selected skill + always-available tools (`ask_user`, `calculate`, `search_documents`, `list_documents`, `get_document`). This keeps Gemini focused instead of overwhelmed by 37 tools.

---

## Database: Local vs Production

| | Local (dev) | Production (Railway) |
|---|---|---|
| Database | SQLite (`clarifi.db`) | Supabase PostgreSQL |
| Checkpointer | SQLite (`memu.db`) | PostgreSQL |
| File storage | `./storage/` | Supabase Storage bucket |
| memU | Disabled (needs pgvector) | Enabled |
| Auth | Skipped (no JWT) | Supabase JWT |

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 15 + React 19 + Tailwind CSS |
| Auth | Supabase Auth (email, Google OAuth) |
| Agent | LangGraph ReAct + Gemini 3.1 Flash Lite |
| API | FastAPI (REST + WebSocket) |
| Database | SQLAlchemy async (SQLite / PostgreSQL) |
| Scheduler | Embedded asyncio + croniter |
| Memory | memU (pgvector, optional) |
| Extraction | Gemini structured output + Pydantic validation |
