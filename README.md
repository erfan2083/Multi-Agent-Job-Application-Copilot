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

## Core endpoints
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
