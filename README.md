# MJAC — Multi-Agent Job Application Copilot

MVP-first, production-minded system for parsing resumes, finding remote jobs, scoring fit/win, generating tailored docs, and preparing human-approved application plans.

## Safety
- No CAPTCHA bypass.
- Respect robots.txt and ToS; blocked flows become `manual_required`.
- No plaintext passwords; env vars only.
- Human-in-the-loop before any submission.
- No fabricated resume claims.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

## Run DB (optional postgres)
```bash
docker compose up -d postgres
```

## Run API
```bash
uvicorn apps.api.main:app --reload --port 8000
```

## Run UI
```bash
streamlit run apps/ui/streamlit_app.py
```

## Auth + LLM Access
- Login is required for `/llm/generate`.
- Use env vars `APP_LOGIN_USERNAME` and `APP_LOGIN_PASSWORD_HASH` (sha256) for local credentials.

Example login:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

Then call LLM with bearer token:
```bash
TOKEN=<token from login>
curl -X POST http://localhost:8000/llm/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Return a short summary\"}"
```

## Core endpoints
- `POST /auth/login`
- `POST /llm/generate` (requires login)
- `POST /profile/parse_resume`
- `POST /jobs/search`
- `POST /docs/generate` (scaffolded via agents)
- `POST /applications/plan`
- `POST /applications/confirm_email_send`
- `POST /reports/run`
- `GET /reports/{run_id}`

## Example
```bash
curl -X POST http://localhost:8000/reports/run \
  -H 'Content-Type: application/json' \
  -d '{"resume_text":"Jane Doe\nPython Engineer\npython fastapi sql", "preferences":{"remote_only":true}}'
```
