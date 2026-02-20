from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agents.executor import plan_applications
from agents.job_normalizer import normalize_jobs
from agents.job_discovery import discover_jobs
from agents.resume_analyst import extract_candidate_profile
from agents.scoring import score_jobs
from services.email import email_service

router = APIRouter(prefix="/applications", tags=["applications"])


class PlanRequest(BaseModel):
    resume_text: str
    preferences: dict = {}
    top_n: int = 5


@router.post("/plan")
def plan(payload: PlanRequest):
    profile = extract_candidate_profile(payload.resume_text, payload.preferences)
    scored = score_jobs(normalize_jobs(discover_jobs(payload.preferences)), profile)[: payload.top_n]
    return plan_applications(scored)


class ConfirmEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str


@router.post("/confirm_email_send")
def confirm_email_send(payload: ConfirmEmailRequest):
    if not payload.to_email:
        raise HTTPException(status_code=400, detail="Missing recipient")
    path = email_service.send_or_dry_run(payload.to_email, payload.subject, payload.body)
    return {"status": "dry-run", "artifact": path}
