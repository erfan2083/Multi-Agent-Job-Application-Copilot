from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from agents.document_tailor import generate_docs
from agents.job_discovery import discover_jobs
from agents.job_normalizer import normalize_jobs
from agents.resume_analyst import extract_candidate_profile
from agents.scoring import score_jobs

router = APIRouter(prefix="/docs", tags=["docs"])


class DocsRequest(BaseModel):
    resume_text: str
    preferences: dict = {}
    top_n: int = 3


@router.post("/generate")
def generate(payload: DocsRequest):
    profile = extract_candidate_profile(payload.resume_text, payload.preferences)
    scored = score_jobs(normalize_jobs(discover_jobs(payload.preferences)), profile)[: payload.top_n]
    return generate_docs(profile, scored)
