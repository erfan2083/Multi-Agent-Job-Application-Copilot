from __future__ import annotations

from core.utils.dates import utcnow
from schemas.application import ApplicationRecord
from schemas.job import JobWithScores


def plan_applications(jobs: list[JobWithScores]) -> list[ApplicationRecord]:
    plans = []
    for j in jobs:
        status = "ready" if j.job.apply_method.type == "email" else "manual_required"
        plans.append(ApplicationRecord(job_id=j.job.id, status=status, created_at=utcnow(), updated_at=utcnow()))
    return plans
