# VeritasGuard Railway Deployment Guide

## 1) Create Railway Services

Create three Railway services in one project:

1. `veritasguard-api` (Python backend)
2. `veritasguard-frontend` (Vite frontend)
3. `veritasguard-postgres` (Railway Postgres)

## 2) Backend Service (`veritasguard-api`)

### Build / start
- Root directory: repository root
- Start command:

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port $PORT
```

### Required env vars

```bash
DATABASE_URL=<Railway Postgres URL>
ADMIN_API_KEY=<long-random-secret>
MISTRAL_API_KEY=<...>
TAVILY_API_KEY=<...>
TWILIO_ACCOUNT_SID=<...>
TWILIO_AUTH_TOKEN=<...>
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
WHATSAPP_VALIDATE_SIGNATURE=true
ENABLE_TAVILY_SEARCH_FALLBACK=true
ENABLE_GOOGLE_SEARCH_FALLBACK=false
CORS_ALLOWED_ORIGINS=https://<frontend-domain>,http://localhost:5173
```

Optional tuning envs are already supported in `.env.example` (pipeline budgets, rate limits).

## 3) Frontend Service (`veritasguard-frontend`)

### Build / start
- Root directory: `frontend`
- Build command:

```bash
npm install && npm run build
```

- Start command:

```bash
npm run preview -- --host 0.0.0.0 --port $PORT
```

### Frontend env vars

```bash
VITE_API_BASE_URL=https://<api-domain>
VITE_ADMIN_API_KEY=<same-admin-key-if-debug-ui-needed>
```

## 4) Database Bootstrap and Migration

After first backend deploy:

```bash
python scripts/migrate_sqlite_to_postgres.py
python scripts/db_health_check.py
```

The migration script copies:
- `known_hoaxes`
- `verification_results`

Then reseeds known hoaxes from `server/data/known_hoaxes.json`.

## 5) Twilio Sandbox Webhook

Set inbound webhook URL to:

```text
https://<api-domain>/webhook/whatsapp
```

Method: `POST`

## 6) Runtime Checks

Public checks:
- `GET /healthz`
- `GET /readyz`

Protected checks (header `X-Admin-Key` required):
- `GET /ops/runtime`
- `GET /result/{id}/debug`

## 7) Demo Safety Checklist

1. `readyz` is `ready`.
2. Stable benchmark passes:

```bash
python -m demo.test_cases --profile stable --timeout 60
```

3. WhatsApp receives immediate ack and async final verdict.
4. Debug endpoint fails without admin key and passes with admin key.
