"""FastAPI application — REST + SSE endpoints for Job Hunter Agent."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from backend.agent import JobHunterAgent
from backend.config import settings
from backend.database import (
    JobAlert,
    JobListing,
    ResumeProfile,
    SavedSearch,
    SearchPreference,
    SessionLocal,
    get_db,
    init_db,
)
from backend.models import (
    ApplyRequest,
    ChatMessage,
    ExportRequest,
    JobListingOut,
    LLMProviderSwitch,
    PreferencesIn,
    PreferencesOut,
    ResumeProfileOut,
    SavedSearchIn,
    SavedSearchOut,
    SavedSearchUpdate,
    SearchRequest,
)
from backend.tools.auto_apply import (
    AutoApplyEngine,
    get_supported_sites,
    is_auto_apply_supported,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Global instances ─────────────────────────────────────────────────

agent = JobHunterAgent()
apply_engine = AutoApplyEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown."""
    init_db()
    logger.info("Database initialized")

    # Try to start LLM provider (non-blocking — if it fails, we use fallback)
    try:
        await agent.init_claude()
    except Exception as e:
        logger.warning(f"LLM provider not available: {e}")

    yield

    await agent.close()
    await apply_engine.close()


app = FastAPI(
    title="Job Hunter Agent",
    description="AI-powered job hunting agent — Phase 3: Auto-Apply + Multi-LLM",
    version="0.3.0",
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


def _job_to_out(j: JobListing) -> dict:
    return {
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
        "saved_at": j.saved_at.isoformat() if j.saved_at else None,
        "viewed_at": j.viewed_at.isoformat() if j.viewed_at else None,
    }


def _saved_search_to_out(s: SavedSearch) -> dict:
    return {
        "id": s.id,
        "resume_id": s.resume_id,
        "preferences_id": s.preferences_id,
        "name": s.name,
        "keywords": s.get_keywords(),
        "persian_keywords": s.get_persian_keywords(),
        "locations": s.get_locations(),
        "job_type": s.job_type,
        "min_salary": s.min_salary,
        "preferred_sites": s.get_preferred_sites(),
        "is_active": s.is_active,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else "",
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
    return [_job_to_out(j) for j in jobs]


@app.patch("/api/jobs/{job_id}/status")
async def update_job_status(
    job_id: int, status: str = Query(...), db: Session = Depends(get_db)
):
    """Update job status (new/saved/dismissed) with timestamp tracking."""
    job = db.query(JobListing).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    if status not in ("new", "saved", "dismissed", "viewed", "applied"):
        raise HTTPException(400, "Invalid status")

    now = datetime.now(timezone.utc)

    if status == "saved":
        job.status = "saved"
        job.saved_at = now
    elif status == "viewed":
        # "viewed" updates viewed_at but doesn't change status
        job.viewed_at = now
    else:
        job.status = status
        if status == "new":
            job.saved_at = None

    db.commit()
    return {"message": "Status updated", "job_id": job_id, "status": job.status}


@app.post("/api/jobs/{job_id}/view")
async def mark_job_viewed(job_id: int, db: Session = Depends(get_db)):
    """Mark a job as viewed (sets viewed_at timestamp without changing status)."""
    job = db.query(JobListing).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    job.viewed_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Job marked as viewed", "job_id": job_id}


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


# ── Saved Searches Endpoints (Phase 2) ─────────────────────────────

@app.post("/api/saved-searches")
async def create_saved_search(data: SavedSearchIn, db: Session = Depends(get_db)):
    """Save the current search configuration for re-running later."""
    # Verify resume exists
    resume = db.query(ResumeProfile).filter_by(id=data.resume_id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")

    # If preferences_id provided, use its keywords as defaults
    keywords = data.keywords
    persian_keywords = data.persian_keywords
    locations = data.locations
    job_type = data.job_type
    min_salary = data.min_salary
    preferred_sites = data.preferred_sites

    if data.preferences_id and not keywords:
        pref = db.query(SearchPreference).filter_by(id=data.preferences_id).first()
        if pref:
            keywords = keywords or pref.get_keywords()
            persian_keywords = persian_keywords or pref.get_persian_keywords()
            locations = locations or pref.get_locations()
            job_type = job_type or pref.job_type
            min_salary = min_salary or pref.min_salary
            preferred_sites = preferred_sites or pref.get_preferred_sites()

    saved = SavedSearch(
        resume_id=data.resume_id,
        preferences_id=data.preferences_id,
        name=data.name or f"Search {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        keywords=json.dumps(keywords, ensure_ascii=False),
        persian_keywords=json.dumps(persian_keywords, ensure_ascii=False),
        locations=json.dumps(locations, ensure_ascii=False),
        job_type=job_type,
        min_salary=min_salary,
        preferred_sites=json.dumps(preferred_sites, ensure_ascii=False),
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)

    return {
        "message": "جستجو ذخیره شد",
        "saved_search": _saved_search_to_out(saved),
    }


@app.get("/api/saved-searches")
async def list_saved_searches(
    resume_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """List all saved searches, optionally filtered by resume."""
    query = db.query(SavedSearch).order_by(SavedSearch.created_at.desc())
    if resume_id:
        query = query.filter(SavedSearch.resume_id == resume_id)

    searches = query.all()
    return [_saved_search_to_out(s) for s in searches]


@app.get("/api/saved-searches/{search_id}")
async def get_saved_search(search_id: int, db: Session = Depends(get_db)):
    """Get a specific saved search."""
    search = db.query(SavedSearch).filter_by(id=search_id).first()
    if not search:
        raise HTTPException(404, "Saved search not found")
    return _saved_search_to_out(search)


@app.patch("/api/saved-searches/{search_id}")
async def update_saved_search(
    search_id: int, data: SavedSearchUpdate, db: Session = Depends(get_db)
):
    """Update a saved search (name, active status, filters)."""
    search = db.query(SavedSearch).filter_by(id=search_id).first()
    if not search:
        raise HTTPException(404, "Saved search not found")

    if data.name is not None:
        search.name = data.name
    if data.is_active is not None:
        search.is_active = data.is_active
    if data.keywords is not None:
        search.keywords = json.dumps(data.keywords, ensure_ascii=False)
    if data.persian_keywords is not None:
        search.persian_keywords = json.dumps(data.persian_keywords, ensure_ascii=False)
    if data.locations is not None:
        search.locations = json.dumps(data.locations, ensure_ascii=False)
    if data.job_type is not None:
        search.job_type = data.job_type
    if data.min_salary is not None:
        search.min_salary = data.min_salary
    if data.preferred_sites is not None:
        search.preferred_sites = json.dumps(data.preferred_sites, ensure_ascii=False)

    db.commit()
    db.refresh(search)
    return {
        "message": "Saved search updated",
        "saved_search": _saved_search_to_out(search),
    }


@app.delete("/api/saved-searches/{search_id}")
async def delete_saved_search(search_id: int, db: Session = Depends(get_db)):
    """Delete a saved search and its alerts."""
    search = db.query(SavedSearch).filter_by(id=search_id).first()
    if not search:
        raise HTTPException(404, "Saved search not found")

    # Delete related alerts
    db.query(JobAlert).filter(JobAlert.saved_search_id == search_id).delete()
    db.delete(search)
    db.commit()
    return {"message": "Saved search deleted"}


@app.post("/api/saved-searches/{search_id}/run")
async def run_saved_search(search_id: int, db: Session = Depends(get_db)):
    """Re-run a saved search and stream results via SSE.

    Finds new jobs that weren't already discovered, creates alerts for them.
    """
    search = db.query(SavedSearch).filter_by(id=search_id).first()
    if not search:
        raise HTTPException(404, "Saved search not found")

    async def event_stream():
        async for event in agent.run_saved_search(search_id):
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


# ── Alerts Endpoints (Phase 2) ────────────────────────────────────

@app.get("/api/alerts")
async def list_alerts(
    saved_search_id: int | None = Query(None),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """List job alerts, optionally filtered by saved search or read status."""
    query = db.query(JobAlert).order_by(JobAlert.created_at.desc())
    if saved_search_id:
        query = query.filter(JobAlert.saved_search_id == saved_search_id)
    if unread_only:
        query = query.filter(JobAlert.is_read == False)

    alerts = query.limit(200).all()

    result = []
    for alert in alerts:
        job = db.query(JobListing).filter_by(id=alert.job_id).first()
        result.append({
            "id": alert.id,
            "saved_search_id": alert.saved_search_id,
            "job_id": alert.job_id,
            "is_read": alert.is_read,
            "created_at": alert.created_at.isoformat() if alert.created_at else "",
            "job": _job_to_out(job) if job else None,
        })

    return result


@app.get("/api/alerts/count")
async def alert_count(db: Session = Depends(get_db)):
    """Get the count of unread alerts."""
    count = db.query(JobAlert).filter(JobAlert.is_read == False).count()
    return {"unread_count": count}


@app.patch("/api/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    """Mark a single alert as read."""
    alert = db.query(JobAlert).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")

    alert.is_read = True
    db.commit()
    return {"message": "Alert marked as read"}


@app.post("/api/alerts/mark-all-read")
async def mark_all_alerts_read(
    saved_search_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """Mark all alerts (or all for a saved search) as read."""
    query = db.query(JobAlert).filter(JobAlert.is_read == False)
    if saved_search_id:
        query = query.filter(JobAlert.saved_search_id == saved_search_id)

    query.update({"is_read": True})
    db.commit()
    return {"message": "All alerts marked as read"}


# ── CSV Export Endpoint (Phase 2) ─────────────────────────────────

@app.get("/api/export/csv")
async def export_jobs_csv(
    resume_id: int | None = Query(None),
    min_score: int = Query(0),
    source: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Export job listings to CSV file."""
    query = db.query(JobListing)

    if resume_id:
        query = query.filter(JobListing.resume_id == resume_id)
    if min_score > 0:
        query = query.filter(JobListing.match_score >= min_score)
    if source:
        query = query.filter(JobListing.source_site == source)
    if status:
        query = query.filter(JobListing.status == status)

    query = query.order_by(JobListing.match_score.desc())
    jobs = query.all()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Title",
        "Company",
        "Location",
        "Remote",
        "Salary Range",
        "Source Site",
        "Match Score",
        "Match Reason",
        "URL",
        "Status",
        "Found At",
        "Saved At",
        "Viewed At",
    ])

    for j in jobs:
        writer.writerow([
            j.title,
            j.company,
            j.location,
            "Yes" if j.is_remote else "No",
            j.salary_range or "",
            j.source_site,
            j.match_score,
            j.match_reason or "",
            j.url,
            j.status,
            j.found_at.isoformat() if j.found_at else "",
            j.saved_at.isoformat() if j.saved_at else "",
            j.viewed_at.isoformat() if j.viewed_at else "",
        ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=job_listings.csv",
        },
    )


# ── Phase 3: Applications / Auto-Apply ────────────────────────────

@app.post("/api/apply")
async def apply_to_job(data: ApplyRequest):
    """Auto-apply to a job. Requires user confirmation on the frontend."""
    result = await apply_engine.apply(data.job_id, data.resume_id)
    return {
        "success": result.success,
        "method": result.method,
        "screenshot": result.screenshot_path,
        "notes": result.notes,
    }


@app.get("/api/applications")
async def list_applications(
    job_id: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """List application records."""
    from backend.database import Application

    query = db.query(Application).order_by(Application.id.desc())
    if job_id:
        query = query.filter(Application.job_id == job_id)
    if status:
        query = query.filter(Application.status == status)

    apps = query.limit(200).all()
    return [
        {
            "id": a.id,
            "job_id": a.job_id,
            "applied_at": a.applied_at.isoformat() if a.applied_at else None,
            "method": a.method,
            "status": a.status,
            "notes": a.notes,
        }
        for a in apps
    ]


@app.get("/api/apply/supported-sites")
async def supported_sites():
    """Return the list of sites that support auto-apply."""
    return {"sites": get_supported_sites()}


# ── LLM Provider Endpoints ────────────────────────────────────────

@app.get("/api/llm/status")
async def llm_status():
    """Return current LLM provider status."""
    return agent.get_llm_status()


@app.post("/api/llm/switch")
async def switch_llm(data: LLMProviderSwitch):
    """Switch the active LLM provider at runtime."""
    success = await agent.init_llm(data.provider)
    return {
        "message": f"Switched to {data.provider}" if success else f"Failed to switch to {data.provider}",
        "success": success,
        **agent.get_llm_status(),
    }


# ── Health Check ────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    llm = agent.get_llm_status()
    return {
        "status": "ok",
        "claude_available": agent._claude_available,
        "llm_provider": llm["provider"],
        "llm_available": llm["available"],
    }
