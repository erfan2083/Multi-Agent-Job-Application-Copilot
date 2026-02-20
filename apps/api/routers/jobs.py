from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from agents.job_discovery import discover_jobs
from agents.job_normalizer import normalize_jobs
from agents.resume_analyst import extract_candidate_profile
from agents.scoring import score_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobSearchRequest(BaseModel):
    resume_text: str
    preferences: dict = {}


@router.post("/search")
def search_jobs(payload: JobSearchRequest):
    profile = extract_candidate_profile(payload.resume_text, payload.preferences)
    raw = discover_jobs(payload.preferences)
    normalized = normalize_jobs(raw)
    return score_jobs(normalized, profile)
