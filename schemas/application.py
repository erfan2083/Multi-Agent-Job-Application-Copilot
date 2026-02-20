from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class SubmissionEvidence(BaseModel):
    emailsent_id: Optional[str] = None
    screenshot_paths: list[str] = []
    notes: str = ""


class ApplicationRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    status: str = "draft"
    tailored_resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    message_to_recruiter: Optional[str] = None
    submission_evidence: SubmissionEvidence = SubmissionEvidence()
    created_at: datetime
    updated_at: datetime
