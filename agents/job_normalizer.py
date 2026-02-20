from __future__ import annotations

from core.utils.dates import utcnow
from schemas.job import ApplyMethod, JobNormalized, JobRaw


def normalize_jobs(raw_jobs: list[JobRaw]) -> list[JobNormalized]:
    normalized = []
    for raw in raw_jobs:
        payload = raw.raw_json or {}
        desc = payload.get("description") or payload.get("summary", "")
        title = payload.get("position") or payload.get("title", "Untitled")
        company = payload.get("company") or payload.get("company_name", "Unknown")
        apply_email = payload.get("email")
        apply_type = "email" if apply_email else "link"
        normalized.append(
            JobNormalized(
                source=raw.source,
                source_job_id=raw.source_job_id,
                url=raw.url,
                title=title,
                company=company,
                description=desc,
                requirements=[title],
                technologies=[t for t in ["Python", "FastAPI", "SQL"] if t.lower() in desc.lower()],
                apply_method=ApplyMethod(type=apply_type, email=apply_email, apply_url=raw.url),
                extracted_at=utcnow(),
            )
        )
    return normalized
