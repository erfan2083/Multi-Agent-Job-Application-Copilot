from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ApplyMethod(BaseModel):
    type: str
    email: Optional[str] = None
    apply_url: Optional[str] = None


class JobRaw(BaseModel):
    source: str
    source_job_id: str
    url: str
    raw_json: dict | None = None
    raw_html: str | None = None
    fetched_at: datetime


class JobNormalized(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source: str
    source_job_id: str
    url: str
    title: str
    company: str
    location: str = "Remote"
    remote: bool = True
    employment_type: str = "full-time"
    seniority: str = "unspecified"
    salary_range: Optional[str] = None
    description: str
    requirements: list[str] = []
    nice_to_have: list[str] = []
    technologies: list[str] = []
    apply_method: ApplyMethod
    posted_at: Optional[datetime] = None
    extracted_at: datetime


class Scores(BaseModel):
    fit_score: float = Field(ge=0, le=100)
    win_probability: float = Field(ge=0, le=100)
    reasons: list[str] = []
    missing_skills: list[str] = []
    matched_skills: list[str] = []


class JobWithScores(BaseModel):
    job: JobNormalized
    scores: Scores
