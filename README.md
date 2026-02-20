# Job Hunter Agent

AI-powered job hunting agent that analyzes your resume, understands your preferences (Persian/English), searches Iranian and international job boards, and ranks matches by fit probability.

## Phase 1 — MVP Features

- **Resume Upload**: Upload PDF/DOCX resumes for automatic parsing and skill extraction
- **Natural Language Preferences**: Set job preferences in Persian or English via chat
- **Multi-Site Job Search**: Searches across 8 job boards simultaneously
  - Iranian: Jobinja, IranTalent, JobVision
  - International: LinkedIn, Indeed, Remotive, WeWorkRemotely, Wellfound
- **Match Scoring**: Each job scored 0-100 against your profile with explanation
- **Job Dashboard**: Card grid with filters, sorting, save/dismiss actions
- **Real-Time Updates**: SSE streaming for live search progress
- **RTL Support**: Full Persian/Farsi interface with Vazirmatn font

## Architecture

```
Frontend (React + TailwindCSS)
  ↕ HTTP / SSE
Backend (FastAPI)
  ├── Resume Parser (PyMuPDF + python-docx)
  ├── Claude Session (Playwright browser OAuth)
  ├── Job Scrapers (httpx + BeautifulSoup)
  ├── Match Scorer (Claude or rule-based fallback)
  └── SQLite Database (SQLAlchemy)
```

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
pip install -r ../requirements.txt
playwright install chromium
```

### Frontend

```bash
cd frontend
npm install
```

### Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

## Running

### Start Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

### Start Frontend

```bash
cd frontend
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API requests to the backend.

## Usage

1. Open `http://localhost:5173`
2. Upload your resume (PDF or DOCX)
3. Type your job preferences in the chat (Persian or English):
   - "دنبال کار ریموت بک‌اند با پایتون، حقوق بالای ۲۰۰۰ دلار"
   - "Looking for a frontend React developer role, remote"
4. Click "شروع جستجوی مشاغل" (Start Job Search)
5. View ranked results in the dashboard

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI |
| LLM | Claude via browser session (Playwright) |
| Scraping | httpx + BeautifulSoup4 |
| Resume Parsing | PyMuPDF (PDF) + python-docx (DOCX) |
| Frontend | React 19 + TailwindCSS |
| Database | SQLite via SQLAlchemy |
| Build Tool | Vite |

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app + API endpoints
│   ├── agent.py             # Main orchestration loop
│   ├── claude_session.py    # Claude browser session handler
│   ├── database.py          # SQLAlchemy models + DB setup
│   ├── models.py            # Pydantic schemas
│   ├── config.py            # Settings via pydantic-settings
│   ├── tools/
│   │   ├── resume_parser.py # PDF/DOCX text extraction
│   │   ├── job_scraper.py   # Multi-site scraper orchestrator
│   │   ├── job_scorer.py    # Match scoring (Claude + fallback)
│   │   ├── query_builder.py # Search query generation
│   │   └── report_generator.py
│   └── scrapers/
│       ├── base.py          # Base scraper class
│       ├── jobinja.py
│       ├── irantalent.py
│       ├── jobvision.py
│       ├── linkedin.py
│       ├── indeed.py
│       ├── remotive.py
│       ├── weworkremotely.py
│       └── wellfound.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js           # API client
│   │   └── components/
│   │       ├── ChatInterface.jsx
│   │       ├── ResumeUpload.jsx
│   │       ├── JobDashboard.jsx
│   │       ├── JobCard.jsx
│   │       └── StatusStream.jsx
│   ├── package.json
│   └── vite.config.js
├── requirements.txt
└── .env.example
```
