"""FastAPI application — REST + SSE endpoints for Job Hunter Agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.agent import JobHunterAgent
from backend.config import settings
from backend.database import (
    JobListing,
    ResumeProfile,
    SearchPreference,
    SessionLocal,
    get_db,
    init_db,
)
from backend.models import (
    ChatMessage,
    JobListingOut,
    PreferencesIn,
    PreferencesOut,
    ResumeProfileOut,
    SearchRequest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Global agent instance ───────────────────────────────────────────

agent = JobHunterAgent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    init_db()
    logger.info("Database initialized")

    # Try to start Claude session (non-blocking — if it fails, we use fallback)
    try:
        await agent.init_claude()
    except Exception as e:
        logger.warning(f"Claude session not available: {e}")

    yield

    await agent.close()


app = FastAPI(
    title="Job Hunter Agent",
    description="AI-powered job hunting agent — Phase 1 MVP",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ─────────────────────────────────────────────────────────

def _resume_to_out(r: ResumeProfile) -> dict:
    return {
        "id": r.id,
        "filename": r.filename,
        "skills": r.get_skills(),
        "titles": r.get_titles(),
        "experience_years": r.experience_years,
        "education": r.get_education(),
        "languages": r.get_languages(),
        "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else "",
    }


def _pref_to_out(p: SearchPreference) -> dict:
    return {
        "id": p.id,
        "resume_id": p.resume_id,
        "job_type": p.job_type,
        "locations": p.get_locations(),
        "fields": p.get_fields(),
        "min_salary": p.min_salary,
        "preferred_sites": p.get_preferred_sites(),
        "created_at": p.created_at.isoformat() if p.created_at else "",
    }


# ── Resume Endpoints ───────────────────────────────────────────────

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and analyze a resume (PDF or DOCX)."""
    if not file.filename:
        raise HTTPException(400, "No file provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".docx", ".doc"):
        raise HTTPException(400, "Only PDF and DOCX files are supported")

    # Save uploaded file
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / file.filename

    async with aiofiles.open(str(file_path), "wb") as f:
        content = await file.read()
        await f.write(content)

    try:
        resume_id, profile = await agent.analyze_resume(str(file_path))
    except Exception as e:
        logger.error(f"Resume analysis failed: {e}")
        raise HTTPException(500, f"Resume analysis failed: {e}")

    # Return the profile
    db = SessionLocal()
    try:
        resume = db.query(ResumeProfile).filter_by(id=resume_id).first()
        return {
            "message": "رزومه با موفقیت آنالیز شد",
            "resume": _resume_to_out(resume),
            "profile": profile,
        }
    finally:
        db.close()


@app.get("/api/resumes")
async def list_resumes(db: Session = Depends(get_db)):
    """List all uploaded resumes."""
    resumes = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).all()
    return [_resume_to_out(r) for r in resumes]


@app.get("/api/resumes/{resume_id}")
async def get_resume(resume_id: int, db: Session = Depends(get_db)):
    """Get a specific resume profile."""
    resume = db.query(ResumeProfile).filter_by(id=resume_id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")
    return {
        "resume": _resume_to_out(resume),
        "profile": resume.to_profile_dict(),
    }


# ── Preferences Endpoints ──────────────────────────────────────────

@app.post("/api/set-preferences")
async def set_preferences(data: PreferencesIn):
    """Parse and save user preferences from natural language."""
    db = SessionLocal()
    try:
        resume = db.query(ResumeProfile).filter_by(id=data.resume_id).first()
        if not resume:
            raise HTTPException(404, "Resume not found")
    finally:
        db.close()

    pref_id, prefs = await agent.parse_preferences(data.resume_id, data.message)

    db = SessionLocal()
    try:
        pref = db.query(SearchPreference).filter_by(id=pref_id).first()
        return {
            "message": "ترجیحات شغلی ذخیره شد",
            "preferences": _pref_to_out(pref),
            "parsed": prefs,
        }
    finally:
        db.close()


@app.get("/api/preferences/{resume_id}")
async def get_preferences(resume_id: int, db: Session = Depends(get_db)):
    """Get preferences for a resume."""
    prefs = (
        db.query(SearchPreference)
        .filter_by(resume_id=resume_id)
        .order_by(SearchPreference.id.desc())
        .first()
    )
    if not prefs:
        raise HTTPException(404, "No preferences found")
    return _pref_to_out(prefs)


# ── Search Endpoints ───────────────────────────────────────────────

@app.post("/api/search-jobs")
async def search_jobs(data: SearchRequest):
    """Start a job search and stream results via SSE."""

    async def event_stream():
        async for event in agent.search_jobs(data.resume_id, data.preferences_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/jobs")
async def list_jobs(
    resume_id: int | None = Query(None),
    min_score: int = Query(0),
    source: str | None = Query(None),
    status: str | None = Query(None),
    sort_by: str = Query("match_score"),
    db: Session = Depends(get_db),
):
    """List stored job listings with filters."""
    query = db.query(JobListing)

    if resume_id:
        query = query.filter(JobListing.resume_id == resume_id)
    if min_score > 0:
        query = query.filter(JobListing.match_score >= min_score)
    if source:
        query = query.filter(JobListing.source_site == source)
    if status:
        query = query.filter(JobListing.status == status)

    if sort_by == "match_score":
        query = query.order_by(JobListing.match_score.desc())
    elif sort_by == "found_at":
        query = query.order_by(JobListing.found_at.desc())
    else:
        query = query.order_by(JobListing.match_score.desc())

    jobs = query.limit(100).all()
    return [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "is_remote": j.is_remote,
            "salary_range": j.salary_range,
            "description": j.description[:500] if j.description else "",
            "url": j.url,
            "source_site": j.source_site,
            "match_score": j.match_score,
            "match_reason": j.match_reason,
            "found_at": j.found_at.isoformat() if j.found_at else "",
            "status": j.status,
        }
        for j in jobs
    ]


@app.patch("/api/jobs/{job_id}/status")
async def update_job_status(
    job_id: int, status: str = Query(...), db: Session = Depends(get_db)
):
    """Update job status (new/saved/dismissed)."""
    job = db.query(JobListing).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    if status not in ("new", "saved", "dismissed"):
        raise HTTPException(400, "Invalid status")

    job.status = status
    db.commit()
    return {"message": "Status updated", "job_id": job_id, "status": status}


# ── Chat Endpoint ──────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(msg: ChatMessage):
    """Simple chat endpoint — processes user messages and returns agent responses."""
    response_text = ""

    if any(
        w in msg.content.lower()
        for w in ["سلام", "hello", "hi", "hey", "درود"]
    ):
        response_text = (
            "سلام! من دستیار هوشمند جستجوی کار هستم. "
            "لطفاً ابتدا رزومه خود را آپلود کنید، "
            "سپس ترجیحات شغلی خود را بگویید تا جستجو را شروع کنم."
        )
    elif any(
        w in msg.content.lower()
        for w in ["help", "راهنما", "کمک", "چطور"]
    ):
        response_text = (
            "راهنمای استفاده:\n"
            "1. رزومه خود را آپلود کنید (PDF یا DOCX)\n"
            "2. ترجیحات شغلی خود را بنویسید (مثلاً: دنبال کار ریموت بک‌اند با پایتون)\n"
            "3. دکمه جستجو را بزنید\n"
            "4. نتایج با امتیاز تطابق نمایش داده می‌شود"
        )
    else:
        response_text = (
            "پیام شما دریافت شد. "
            "لطفاً از بخش ترجیحات شغلی برای تنظیم جستجوی خود استفاده کنید."
        )

    return ChatMessage(role="assistant", content=response_text)


# ── Health Check ────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "claude_available": agent._claude_available,
    }
