# Clarifi — Deployment Guide (Railway + Vercel + Supabase)

## Overview

```
Frontend (Vercel)  →  Backend (Railway)  →  Database (Supabase)
  Next.js app           FastAPI + Agent        PostgreSQL + Auth + Storage
```

---

## Step 1: Supabase Setup

1. Create project at https://supabase.com
2. **Settings → API** — copy these 4 values:
   - `Project URL` → SUPABASE_URL
   - `anon public key` → for frontend
   - `service_role key` → SUPABASE_SERVICE_KEY (backend only)
   - `JWT Secret` → SUPABASE_JWT_SECRET (backend only)

3. **SQL Editor** — run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

4. **Authentication → Providers**:
   - Enable **Email** (on by default)
   - Enable **Google** — paste your Google OAuth Client ID + Secret
   
5. **Authentication → URL Configuration**:
   - Add Site URL: `https://your-app.vercel.app`
   - Add Redirect URL: `https://your-app.vercel.app/auth/callback`

6. **Storage**:
   - Create bucket: `documents` (set to **Private**)

---

## Step 2: Railway Backend

### 2.1 Create Project
1. Go to https://railway.app → **New Project**
2. **Deploy from GitHub repo** → select your repo
3. Railway auto-detects Python via `pyproject.toml`

### 2.2 Set Root Directory
Railway → Settings → **Root Directory**: leave empty (project root)

### 2.3 Environment Variables
Railway → Variables → **Add all**:

```env
# Database (REQUIRED)
DATABASE_URL=postgresql+asyncpg://postgres.YOUR_PROJECT:YOUR_PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres

# LLM (REQUIRED)
GOOGLE_API_KEY=AIzaSy...
LLM_MODEL=gemini-3.1-flash-lite-preview
LLM_EXTRACTION_MODEL=gemini-3.1-flash-lite-preview

# Supabase (REQUIRED)
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGci...
SUPABASE_JWT_SECRET=your-jwt-secret

# CORS (REQUIRED — your Vercel URL)
CORS_ORIGINS=https://your-app.vercel.app

# File watcher
WATCH_DIR=./inbox

# memU — long-term memory (optional)
MEMU_ENABLED=true

# Telegram (optional)
TELEGRAM_BOT_TOKEN=
```

**DATABASE_URL tip**: In Supabase → Settings → Database → Connection String → select **URI** and **Session Mode (port 5432)** or **Transaction Mode (port 6543)**. Prepend `postgresql+asyncpg://` instead of `postgresql://`.

### 2.4 Create Tables (first deploy only)
After deploy, go to Railway → your service → **Shell** tab:

```bash
python -c "
import asyncio
from clarifi.db.session import engine
from clarifi.models import Base
async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables created')
    await engine.dispose()
asyncio.run(create())
"
```

### 2.5 Verify
```bash
curl https://YOUR_RAILWAY_URL/health
# {"status":"ok","service":"clarifi"}
```

---

## Step 3: Vercel Frontend

### 3.1 Create Project
1. Go to https://vercel.com → **Add New Project**
2. Import your GitHub repo
3. Set **Root Directory**: `frontend`
4. Framework: **Next.js** (auto-detected)

### 3.2 Environment Variables
Vercel → Settings → Environment Variables:

```env
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...your-anon-key
NEXT_PUBLIC_API_URL=https://YOUR_RAILWAY_URL
```

### 3.3 Deploy
Click **Deploy**. Vercel builds the Next.js app automatically.

### 3.4 Update Supabase Redirect URLs
After Vercel gives you a URL, go back to Supabase:
- Authentication → URL Configuration → add:
  - `https://your-app.vercel.app/auth/callback`

### 3.5 Update Railway CORS
Railway → Variables → update:
```
CORS_ORIGINS=https://your-app.vercel.app
```

---

## How Cron Jobs Work

**No separate cron service needed.** The scheduler runs inside the Railway web process:

```
Railway starts uvicorn
  → FastAPI lifespan creates 2 background tasks:
    1. Scheduler — polls DB every 60s for due tasks
    2. File watcher — polls inbox/ every 10s for new files
  → Both run forever alongside HTTP handling
```

### Every 60 seconds:
1. Query: `SELECT * FROM scheduled_tasks WHERE is_active AND next_run_at <= NOW()`
2. Execute each via the agent graph (same LLM that handles chat)
3. Save output to `scheduler_runs` table (visible on dashboard)
4. Compute next_run_at from cron expression
5. Send Telegram notification (if configured)

### The agent creates tasks automatically:
- Invoice with due date → reminders at 7 days, 1 day, and on due date
- Contract milestone → reminder 7 days before
- Contract expiry → reminders at 30, 7, 1 day before
- Users can ask in chat: "Aminteste-mi sa verific facturile luni"

### Results visible to users:
- **Dashboard** → "Ce a facut agentul recent" section shows last 5 results
- **Remindere page** → shows all tasks + execution history with agent output

### Railway keeps it running:
- `restartPolicyType = "on_failure"` auto-restarts on crash
- Tasks survive deploys — stored in Supabase DB
- After restart, scheduler picks up on next 60s poll

---

## Architecture on Railway

```
┌─────────────────────────────┐
│  Railway (single process)   │
│                             │
│  uvicorn (FastAPI)          │
│  ├── HTTP/WS endpoints      │
│  ├── Scheduler loop (60s)   │ ← reads scheduled_tasks from DB
│  └── File watcher (10s)     │ ← watches inbox/ directory
│                             │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Supabase                   │
│  ├── PostgreSQL + pgvector  │ ← all data + memU vectors
│  ├── Auth (JWT)             │ ← user sessions
│  └── Storage (documents)    │ ← uploaded files
└─────────────────────────────┘
           ▲
           │
┌─────────────────────────────┐
│  Vercel (static + SSR)      │
│  ├── Next.js frontend       │
│  └── Supabase auth client   │
└─────────────────────────────┘
```

---

## Cost Estimate

| Service | Plan | Monthly |
|---------|------|---------|
| Railway | Starter ($5 credit) | ~$5-10 |
| Supabase | Free tier (500MB DB, 1GB storage) | $0 |
| Vercel | Hobby (free) | $0 |
| Gemini API | Pay-as-you-go | ~$2-5 |
| **Total** | | **~$7-15/month** |

---

## Troubleshooting

**Railway build fails on memU:**
memU requires Rust compiler for `_core` module. If it fails, set `MEMU_ENABLED=false` — the app works without it.

**CORS errors in browser:**
Make sure `CORS_ORIGINS` in Railway matches your Vercel URL exactly (no trailing slash).

**Auth callback loops:**
Check Supabase → Authentication → URL Configuration has your exact Vercel callback URL.

**Scheduler not running:**
Check Railway logs: `[clarifi.scheduler] Scheduler started`. If missing, the app didn't start properly — check for import errors in logs.

**Database connection errors:**
Use Supabase's **Session Mode** connection string (port 5432), not Transaction Mode. Prepend `postgresql+asyncpg://`.
