"""Pydantic schemas for request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Resume ──────────────────────────────────────────────────────────

class ParsedResume(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = []
    technical_skills: list[str] = []
    soft_skills: list[str] = []
    job_titles: list[str] = []
    total_experience_years: int = 0
    education: dict = {}
    languages: list[str] = []
    summary: str = ""


class ResumeProfileOut(BaseModel):
    id: int
    filename: str
    skills: list[str]
    titles: list[str]
    experience_years: int
    education: dict
    languages: list[str]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# ── Preferences ─────────────────────────────────────────────────────

class PreferencesIn(BaseModel):
    resume_id: int
    message: str  # Natural language preferences (Persian/English)


class PreferencesStructured(BaseModel):
    job_type: str = ""  # remote / onsite / hybrid
    locations: list[str] = []
    fields: list[str] = []
    min_salary: Optional[int] = None
    preferred_sites: list[str] = []
    keywords: list[str] = []
    persian_keywords: list[str] = []


class PreferencesOut(BaseModel):
    id: int
    resume_id: int
    job_type: str
    locations: list[str]
    fields: list[str]
    min_salary: Optional[int]
    preferred_sites: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Jobs ────────────────────────────────────────────────────────────

class JobListingOut(BaseModel):
    id: int
    title: str
    company: str
    location: str
    is_remote: bool
    salary_range: str
    description: str
    url: str
    source_site: str
    match_score: int
    match_reason: str
    found_at: datetime
    status: str

    model_config = {"from_attributes": True}


class JobScoreResult(BaseModel):
    score: int = 0
    reason: str = ""
    pros: list[str] = []
    cons: list[str] = []


class SearchQueries(BaseModel):
    keywords: list[str] = []
    persian_keywords: list[str] = []
    locations: list[str] = []
    filters: dict = {}


# ── Chat ────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None


class SearchRequest(BaseModel):
    resume_id: int
    preferences_id: Optional[int] = None


# ── Phase 2: Saved Searches & Alerts ──────────────────────────────

class SavedSearchIn(BaseModel):
    resume_id: int
    preferences_id: Optional[int] = None
    name: str = ""
    keywords: list[str] = []
    persian_keywords: list[str] = []
    locations: list[str] = []
    job_type: str = ""
    min_salary: Optional[int] = None
    preferred_sites: list[str] = []


class SavedSearchOut(BaseModel):
    id: int
    resume_id: int
    preferences_id: Optional[int]
    name: str
    keywords: list[str]
    persian_keywords: list[str]
    locations: list[str]
    job_type: str
    min_salary: Optional[int]
    preferred_sites: list[str]
    is_active: bool
    last_run_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class SavedSearchUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    keywords: Optional[list[str]] = None
    persian_keywords: Optional[list[str]] = None
    locations: Optional[list[str]] = None
    job_type: Optional[str] = None
    min_salary: Optional[int] = None
    preferred_sites: Optional[list[str]] = None


class JobAlertOut(BaseModel):
    id: int
    saved_search_id: int
    job_id: int
    is_read: bool
    created_at: datetime
    job: Optional[JobListingOut] = None

    model_config = {"from_attributes": True}


class ExportRequest(BaseModel):
    resume_id: Optional[int] = None
    min_score: int = 0
    source: Optional[str] = None
    status: Optional[str] = None
