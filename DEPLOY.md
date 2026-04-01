# Clarifi — Deploy cu Vercel + Railway + Supabase

## Arhitectura de deployment

```
┌─────────────────────────┐
│   Vercel (Frontend)     │  ← Next.js, static + SSR
│   clarifi.vercel.app    │
└────────┬────────────────┘
         │ API calls
         ▼
┌─────────────────────────┐
│   Railway (Backend)     │  ← FastAPI + Scheduler + Watcher
│   clarifi-api.up.railway│
└────────┬────────────────┘
         │ SQL + pgvector
         ▼
┌─────────────────────────┐
│   Supabase (Database)   │  ← PostgreSQL + Auth + Storage
│   db.xxx.supabase.co    │
└─────────────────────────┘
```

---

## Pas 1: Supabase

### 1.1 Creează proiectul

1. Du-te la https://supabase.com → New Project
2. Alege o regiune apropiată (eu-central-1 pentru România)
3. Setează o parolă pentru baza de date
4. Notează:
   - **Project URL**: `https://xxx.supabase.co`
   - **Anon Key**: din Settings → API
   - **Database Password**: cea setată la creare

### 1.2 Activează pgvector (pentru memU)

În Supabase SQL Editor, rulează:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 1.3 Connection string

Din Settings → Database → Connection string (URI):

```
postgresql://postgres:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres
```

Pentru asyncpg (ce folosește Clarifi):

```
postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres
```

---

## Pas 2: Railway (Backend)

### 2.1 Setup

1. Du-te la https://railway.app → New Project → Deploy from GitHub
2. Conectează repo-ul
3. Railway detectează automat Python

### 2.2 Configurare build

Creează `railway.toml` în root:

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn clarifi.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
restartPolicyType = "on_failure"
```

Creează `Procfile` (backup):

```
web: uvicorn clarifi.main:app --host 0.0.0.0 --port $PORT
```

### 2.3 Environment Variables

În Railway → Variables, setează:

```
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres
GOOGLE_API_KEY=your-google-api-key
LLM_MODEL=gemini-2.5-flash-lite
LLM_EXTRACTION_MODEL=gemini-2.5-flash
CORS_ORIGINS=https://clarifi.vercel.app
```

Opțional:
```
MEMU_ENABLED=true
MEMU_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
MEMU_LLM_MODEL=gemini-2.5-flash-lite
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

### 2.4 Crearea tabelelor

După primul deploy, rulează o singură dată:

```bash
railway run python -c "
import asyncio
from clarifi.db.session import engine
from clarifi.models import Base

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('24 tabele create')
    await engine.dispose()

asyncio.run(create())
"
```

### 2.5 Seed data (opțional, pentru testare)

```bash
railway run python -m scripts.seed_db
```

### 2.6 Verificare

```bash
curl https://clarifi-api.up.railway.app/health
# {"status":"ok","service":"clarifi"}

curl https://clarifi-api.up.railway.app/dashboard/kpis
# {...cashflow, receivables, alerts...}
```

---

## Pas 3: Vercel (Frontend)

### 3.1 Setup

1. Du-te la https://vercel.com → New Project
2. Importă repo-ul, setează **Root Directory** = `frontend`
3. Framework: Next.js (detectat automat)

### 3.2 Environment Variables

În Vercel → Settings → Environment Variables:

```
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=https://clarifi-api.up.railway.app
```

### 3.3 Configurare API proxy

`frontend/next.config.ts` deja are proxy-ul configurat. Pentru producție, actualizează:

```typescript
const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
};
```

### 3.4 Deploy

Push la GitHub → Vercel rebuild automat.

Accesează: `https://clarifi.vercel.app`

---

## Pas 4: Onboarding

La prima accesare, utilizatorul trebuie să-și configureze compania:

```bash
curl -X POST https://clarifi-api.up.railway.app/api/onboarding \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "SC Digital Solutions SRL",
    "trade_name": "Digital Solutions",
    "tax_id": "RO12345678",
    "registration_number": "J40/1234/2020",
    "city": "București",
    "bank_accounts": [{"iban": "RO49AAAA1B31007593840000", "bank_name": "BCR", "currency": "RON"}],
    "user_name": "Sandu Babasan",
    "user_role": "owner"
  }'
```

Sau prin interfața web la Settings → Onboarding.

---

## Pas 5: Telegram Bot (opțional)

### 5.1 Creează botul

Mesaj către @BotFather pe Telegram → `/newbot` → nume "Clarifi"

### 5.2 Setează webhook-ul

```bash
curl -X POST https://clarifi-api.up.railway.app/api/integrations/telegram/setup \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://clarifi-api.up.railway.app"}'
```

### 5.3 Testează

Trimite un mesaj botului: "Câți bani am?"

---

## Cum funcționează scheduler-ul (cron/remindere)

Scheduler-ul pornește **automat** cu serverul (în `main.py` lifespan).

### Flow-ul complet:

```
1. Agentul procesează un contract → extrage milestone-uri
   → creează remindere automate (7 zile înainte de fiecare deadline)

2. Reminder-ul se salvează în tabela scheduled_tasks:
   {title: "Milestone: Backend Dev", next_run_at: "2026-03-23",
    trigger_message: "Milestone-ul Backend Dev scadent pe 30.03.2026..."}

3. Scheduler-ul (loop intern, la fiecare 60s) verifică:
   SELECT * FROM scheduled_tasks WHERE is_active=true AND next_run_at <= NOW()

4. Când găsește un task scadent:
   → Trimite trigger_message ca HumanMessage la agent
   → Agentul rulează tool-uri, obține date proaspete
   → Compune un răspuns natural
   → Răspunsul se salvează în scheduler_runs
   → Se trimite pe Telegram (dacă e configurat)

5. Task-ul se actualizează:
   - ONE_SHOT: se dezactivează (is_active=false)
   - RECURRING: se calculează next_run_at din cron expression
```

### Remindere pre-configurate (din seed):

| Reminder | Frecvență | Ce face |
|----------|-----------|---------|
| Verificare alerte | Zilnic 07:00 | Evaluează toate alertele |
| Raport săptămânal | Luni 08:00 | Cashflow + restanțe + acțiuni |
| Raport profitabilitate | 1 a lunii | P&L pe proiecte |
| Proiecție cashflow | Miercuri 10:00 | Proiecție 90 zile |

### Remindere create automat de agent:

| Trigger | Reminder creat |
|---------|---------------|
| Contract salvat cu milestone-uri | 7 zile înainte de fiecare milestone |
| Contract salvat cu end_date | 30 zile înainte de expirare |
| Factură emisă salvată | Pe data scadenței |

---

## Monitorizare

### Logs (Railway)

Railway → Deployments → Logs. Caută:
- `Scheduler started (polling every 60s)` — scheduler pornit
- `Checkpointer: Supabase PostgreSQL` — memorie conectată
- `Executing: ...` — task programat rulat
- `Telegram notification sent` — notificare trimisă

### Dashboard API

- `GET /api/scheduler/tasks` — toate task-urile programate
- `GET /api/scheduler/runs` — istoricul execuțiilor
- `GET /api/decisions` — logul tuturor deciziilor agentului
- `GET /api/settings` — configurare curentă

### Health check

```bash
curl https://clarifi-api.up.railway.app/health
```

---

## Costuri estimate

| Serviciu | Plan | Cost/lună |
|----------|------|-----------|
| Supabase | Free (500MB) | **$0** |
| Railway | Starter ($5 credit) | **~$5-10** |
| Vercel | Hobby (free) | **$0** |
| Gemini API | Flash Lite | **~$2-5** (depinde de utilizare) |
| **Total** | | **~$7-15/lună** |

---

## Troubleshooting

**Railway: "Module not found"**
→ Asigură-te că `pyproject.toml` este în root și Railway detectează Python.

**Vercel: "API call failed"**
→ Verifică `NEXT_PUBLIC_API_URL` în Vercel env vars. Trebuie să fie URL-ul Railway.

**Supabase: "connection refused"**
→ Verifică `DATABASE_URL` în Railway. Format: `postgresql+asyncpg://postgres:PASS@db.XXX.supabase.co:5432/postgres`

**Scheduler nu pornește**
→ Verifică logurile Railway pentru "Scheduler started". Dacă lipsește, serverul nu a pornit corect.

**Telegram nu trimite**
→ Verifică `TELEGRAM_BOT_TOKEN` și că webhook-ul e setat cu URL-ul Railway.

**"API key not valid"**
→ Verifică `GOOGLE_API_KEY` în Railway env vars. Trebuie să aibă Generative AI API activat.
