# Clarifi — Ghid Pas cu Pas: Setup Complet

## Ce vei avea la final
- **Frontend** pe Vercel (https://clarifi.vercel.app)
- **Backend** pe Railway (https://clarifi-api.up.railway.app)
- **Database + Auth + Storage** pe Supabase
- **Agent AI** cu Gemini, scheduler, file watcher

---

## Pas 1: Supabase (10 minute)

### 1.1 Creează proiectul

1. Du-te la https://supabase.com → **New Project**
2. Nume: `clarifi`
3. Parolă database: alege una puternică și noteaz-o
4. Regiune: **eu-central-1** (cel mai aproape de România)
5. Apasă **Create new project** — așteaptă ~2 minute

### 1.2 Notează credențialele

Du-te la **Settings → API** și notează:

| Ce | Unde îl găsești | Exemplu |
|----|-----------------|---------|
| **Project URL** | Settings → API → URL | `https://abc123.supabase.co` |
| **anon key** | Settings → API → anon public | `eyJhbGci...` (lung) |
| **service_role key** | Settings → API → service_role | `eyJhbGci...` (lung) |
| **JWT Secret** | Settings → API → JWT Secret | `super-secret-jwt-token-...` |

Du-te la **Settings → Database** și notează:

| Ce | Unde | Exemplu |
|----|------|---------|
| **Connection string** | Settings → Database → URI | `postgresql://postgres:PAROLA@db.abc123.supabase.co:5432/postgres` |

### 1.3 Activează pgvector

Du-te la **SQL Editor** și rulează:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 1.4 Configurează Auth

Du-te la **Authentication → Providers**:

1. **Email** — deja activat (default)
2. **Google** (opțional):
   - Du-te la https://console.cloud.google.com
   - APIs & Services → Credentials → Create OAuth Client ID
   - Application type: Web application
   - Authorized redirect URI: `https://abc123.supabase.co/auth/v1/callback`
   - Copiază Client ID și Client Secret
   - Pune-le în Supabase → Authentication → Providers → Google

### 1.5 Creează bucket-ul de Storage

Du-te la **Storage** → **New bucket**:
- Nume: `documents`
- Public: **No** (privat)

---

## Pas 2: Railway — Backend (10 minute)

### 2.1 Creează proiectul

1. Du-te la https://railway.app → **New Project**
2. **Deploy from GitHub repo** → conectează repo-ul tău
3. Railway detectează Python automat

### 2.2 Setează variabilele de mediu

Du-te la proiect → **Variables** → Add:

```
# Database — Supabase PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:PAROLA@db.abc123.supabase.co:5432/postgres

# LLM
GOOGLE_API_KEY=AIza... (cheia ta de la Google AI Studio)
LLM_MODEL=gemini-2.5-flash-lite
LLM_EXTRACTION_MODEL=gemini-2.5-flash

# Supabase
SUPABASE_URL=https://abc123.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGci... (service_role key)
SUPABASE_JWT_SECRET=super-secret-jwt-token-... (JWT Secret)

# CORS — adresa frontend-ului de pe Vercel
CORS_ORIGINS=https://clarifi.vercel.app

# Watch dir
WATCH_DIR=./inbox
```

### 2.3 Deploy

Railway build-uiește automat din `pyproject.toml` + `Procfile`:
```
web: uvicorn clarifi.main:app --host 0.0.0.0 --port $PORT
```

Așteaptă deploy-ul (~3-5 minute). Notează URL-ul:
```
https://clarifi-api.up.railway.app
```

### 2.4 Creează tabelele

În Railway → **Settings → Environment → Railway CLI**, sau local:

```bash
railway run python -c "
import asyncio
from clarifi.db.session import engine
from clarifi.models import Base

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Done: 26 tabele create')
    await engine.dispose()

asyncio.run(create())
"
```

### 2.5 Verifică

```bash
curl https://clarifi-api.up.railway.app/health
# {"status":"ok","service":"clarifi"}

curl https://clarifi-api.up.railway.app/api/settings
# {"llm_model":"gemini-2.5-flash-lite",...}
```

---

## Pas 3: Vercel — Frontend (5 minute)

### 3.1 Creează proiectul

1. Du-te la https://vercel.com → **Add New → Project**
2. Importă repo-ul GitHub
3. **Root Directory**: `frontend`
4. Framework: **Next.js** (detectat automat)

### 3.2 Setează variabilele de mediu

În Vercel → **Settings → Environment Variables**:

```
NEXT_PUBLIC_SUPABASE_URL=https://abc123.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci... (anon key, NU service_role!)
NEXT_PUBLIC_API_URL=https://clarifi-api.up.railway.app
```

### 3.3 Deploy

Push la GitHub → Vercel rebuild automat.

URL: `https://clarifi.vercel.app` (sau custom domain)

### 3.4 Verifică

Deschide `https://clarifi.vercel.app`:
- Ar trebui să vezi pagina de login
- Login cu email + parolă → redirect la dashboard
- Dashboard arată "Niciun dat disponibil" (normal, nu ai încărcat documente)

---

## Pas 4: Onboarding — Prima configurare (2 minute)

După ce te-ai logat, compania trebuie configurată.

### Prin API:

```bash
# Obține token-ul din browser (Developer Tools → Application → Supabase → access_token)
TOKEN="eyJhbGci..."

curl -X POST https://clarifi-api.up.railway.app/api/onboarding \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "company_name": "SC Compania Ta SRL",
    "trade_name": "Compania Ta",
    "tax_id": "RO12345678",
    "registration_number": "J40/1234/2020",
    "city": "București",
    "bank_accounts": [{"iban": "RO49AAAA1B31007593840000", "bank_name": "BCR", "currency": "RON"}],
    "user_name": "Numele Tău",
    "user_role": "owner"
  }'
```

### Prin chat:

Du-te la **Chat** și scrie:
```
Salut, sunt [numele tău] de la [compania ta].
```

Agentul te va ghida prin configurare.

---

## Pas 5: Testare (5 minute)

### Test 1: Dashboard

Deschide `https://clarifi.vercel.app` — ar trebui să vezi dashboard-ul gol.

### Test 2: Chat

Du-te la **Chat** și întreabă:
```
Câți bani am?
```

Agentul va răspunde pe baza datelor din DB (inițial gol, deci "N-am date").

### Test 3: Upload document

Du-te la **Chat** și trimite:
```
Am o factură de procesat.
```

Sau upload via API:
```bash
curl -X POST https://clarifi-api.up.railway.app/api/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@factura.pdf"
```

### Test 4: Verifică scheduler

```bash
curl https://clarifi-api.up.railway.app/api/scheduler/tasks \
  -H "Authorization: Bearer $TOKEN"
```

### Test 5: File watcher

Creează folder-ul inbox:
```bash
# Pe Railway (sau local)
mkdir -p inbox
cp factura.pdf inbox/
# Watcher-ul detectează fișierul în max 10 secunde
```

---

## Pas 6: Google Drive (opțional, 10 minute)

### 6.1 Creează OAuth Credentials

1. Du-te la https://console.cloud.google.com
2. **APIs & Services → Library** → activează **Google Drive API**
3. **APIs & Services → Credentials → Create Credentials → OAuth Client ID**
4. Application type: **Web application**
5. Authorized redirect URIs:
   - `https://clarifi.vercel.app/auth/callback`
   - `http://localhost:3001/auth/callback` (pentru dev)
6. Notează **Client ID** și **Client Secret**

### 6.2 Configurează

Adaugă în Railway → Variables:
```
GOOGLE_DRIVE_CLIENT_ID=123456789.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=GOCSPX-...
GOOGLE_DRIVE_REDIRECT_URI=https://clarifi.vercel.app/auth/callback
```

### 6.3 Conectează

Din aplicație → **Settings** → Google Drive → "Conectează" (va fi implementat în UI).

Sau manual via API:
```bash
# 1. Obține auth URL
curl https://clarifi-api.up.railway.app/api/integrations/drive/auth

# 2. Deschide URL-ul în browser, autorizează
# 3. Copiază codul din URL-ul de redirect

# 4. Trimite codul
curl -X POST https://clarifi-api.up.railway.app/api/integrations/drive/callback \
  -H "Content-Type: application/json" \
  -d '{"code": "4/0AX4XfWi..."}'
```

---

## Pas 7: Telegram Bot (opțional, 5 minute)

### 7.1 Creează botul

1. Deschide Telegram, caută **@BotFather**
2. Trimite `/newbot`
3. Nume: `Clarifi`
4. Username: `clarifi_finance_bot` (sau altceva unic)
5. Notează **token-ul** (ex: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 7.2 Configurează

Adaugă în Railway → Variables:
```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

### 7.3 Setează webhook

```bash
curl -X POST https://clarifi-api.up.railway.app/api/integrations/telegram/setup \
  -H "Content-Type: application/json" \
  -d '{"webhook_url": "https://clarifi-api.up.railway.app"}'
```

### 7.4 Testează

Deschide Telegram, caută botul tău, și trimite:
```
Câți bani am?
```

---

## Troubleshooting

### "Application startup failed"
→ Verifică `DATABASE_URL` în Railway. Trebuie format `postgresql+asyncpg://...`

### "API key not valid"
→ Verifică `GOOGLE_API_KEY` — trebuie să aibă Generative AI API activat în Google Cloud Console

### "no such table"
→ Rulează scriptul de creare tabele (Pas 2.4)

### Frontend nu se conectează la backend
→ Verifică `NEXT_PUBLIC_API_URL` în Vercel — trebuie să fie URL-ul Railway
→ Verifică `CORS_ORIGINS` în Railway — trebuie să includă URL-ul Vercel

### Login nu funcționează
→ Verifică `NEXT_PUBLIC_SUPABASE_URL` și `NEXT_PUBLIC_SUPABASE_ANON_KEY` în Vercel
→ Verifică că ai activat Email provider în Supabase → Authentication → Providers

### Chat nu răspunde
→ Verifică logs în Railway → Deployments → Logs
→ Caută "Agent error" sau "API key not valid"

---

## Costuri

| Serviciu | Plan | Cost/lună |
|----------|------|-----------|
| Supabase | Free (500MB, 50k auth) | **$0** |
| Railway | Starter ($5 credit) | **~$5-10** |
| Vercel | Hobby (free) | **$0** |
| Gemini API | Pay-as-you-go | **~$2-5** |
| **Total** | | **~$7-15/lună** |
