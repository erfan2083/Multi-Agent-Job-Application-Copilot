from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class HardSkill(BaseModel):
    name: str
    level: int = Field(ge=1, le=5)
    evidence: list[str] = []


class SoftSkill(BaseModel):
    name: str
    evidence: list[str] = []


class Experience(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: list[str] = []
    technologies: list[str] = []


class Project(BaseModel):
    name: str
    description: str
    tech: list[str] = []
    links: list[str] = []


class Education(BaseModel):
    school: str
    degree: str
    field: str
    start: Optional[str] = None
    end: Optional[str] = None


class Preferences(BaseModel):
    remote_only: bool = True
    regions_allowed: list[str] = []
    timezone_overlap: str = ""
    salary_min: Optional[int] = None
    contract_type: list[str] = ["full-time"]
    exclude_keywords: list[str] = []
    include_keywords: list[str] = []


class CandidateSkills(BaseModel):
    hard: list[HardSkill] = []
    soft: list[SoftSkill] = []


class CandidateProfile(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = "Unknown"
    email: Optional[str] = None
    phone: Optional[str] = None
    headline: str = ""
    location: str = ""
    languages: list[str] = []
    years_experience: float = 0.0
    roles_target: list[str] = []
    skills: CandidateSkills = CandidateSkills()
    experience: list[Experience] = []
    projects: list[Project] = []
    education: list[Education] = []
    preferences: Preferences = Preferences()
