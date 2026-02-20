from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from schemas.application import ApplicationRecord
from schemas.job import JobWithScores


class FailedJob(BaseModel):
    job: str
    error: str


class Report(BaseModel):
    run_id: UUID
    timestamp: datetime
    top_jobs: list[JobWithScores]
    applied: list[ApplicationRecord]
    failed: list[FailedJob]
    notes: str = ""
