from __future__ import annotations

from typing import TypedDict
from agents.document_tailor import generate_docs
from agents.executor import plan_applications
from agents.job_discovery import discover_jobs
from agents.job_normalizer import normalize_jobs
from agents.reporter import build_report
from agents.resume_analyst import extract_candidate_profile
from agents.scoring import score_jobs


class PipelineState(TypedDict, total=False):
    resume_text: str
    preferences: dict
    candidate_profile: dict
    raw_jobs: list
    normalized_jobs: list
    scored_jobs: list
    documents: dict
    applications: list
    report: dict


def run_pipeline(resume_text: str, preferences: dict, top_n: int = 10) -> PipelineState:
    profile = extract_candidate_profile(resume_text, preferences)
    raw = discover_jobs(preferences)
    normalized = normalize_jobs(raw)
    scored = score_jobs(normalized, profile)
    selected = scored[:top_n]
    docs = generate_docs(profile, selected)
    applications = plan_applications(selected)
    report = build_report(selected, applications)
    return {
        "resume_text": resume_text,
        "preferences": preferences,
        "candidate_profile": profile,
        "raw_jobs": raw,
        "normalized_jobs": normalized,
        "scored_jobs": scored,
        "documents": docs,
        "applications": applications,
        "report": report,
    }
