"""SQLAlchemy models and database setup."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    pass


class ResumeProfile(Base):
    __tablename__ = "resume_profiles"

    id = Column(Integer, primary_key=True)
    filename = Column(Text, nullable=False)
    raw_text = Column(Text, default="")
    full_name = Column(Text, default="")
    email = Column(Text, default="")
    phone = Column(Text, default="")
    skills = Column(Text, default="[]")  # JSON array
    titles = Column(Text, default="[]")  # JSON array
    experience_years = Column(Integer, default=0)
    education = Column(Text, default="{}")  # JSON
    languages = Column(Text, default="[]")  # JSON array
    summary = Column(Text, default="")
    uploaded_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def get_skills(self) -> list[str]:
        return json.loads(self.skills or "[]")

    def get_titles(self) -> list[str]:
        return json.loads(self.titles or "[]")

    def get_education(self) -> dict:
        return json.loads(self.education or "{}")

    def get_languages(self) -> list[str]:
        return json.loads(self.languages or "[]")

    def to_profile_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.get_skills(),
            "job_titles": self.get_titles(),
            "total_experience_years": self.experience_years,
            "education": self.get_education(),
            "languages": self.get_languages(),
            "summary": self.summary,
        }


class SearchPreference(Base):
    __tablename__ = "search_preferences"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, nullable=False)
    job_type = Column(Text, default="")
    locations = Column(Text, default="[]")
    fields = Column(Text, default="[]")
    min_salary = Column(Integer, nullable=True)
    preferred_sites = Column(Text, default="[]")
    keywords = Column(Text, default="[]")
    persian_keywords = Column(Text, default="[]")
    raw_message = Column(Text, default="")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def get_locations(self) -> list[str]:
        return json.loads(self.locations or "[]")

    def get_fields(self) -> list[str]:
        return json.loads(self.fields or "[]")

    def get_preferred_sites(self) -> list[str]:
        return json.loads(self.preferred_sites or "[]")

    def get_keywords(self) -> list[str]:
        return json.loads(self.keywords or "[]")

    def get_persian_keywords(self) -> list[str]:
        return json.loads(self.persian_keywords or "[]")


class JobListing(Base):
    __tablename__ = "job_listings"

    id = Column(Integer, primary_key=True)
    title = Column(Text, default="")
    company = Column(Text, default="")
    location = Column(Text, default="")
    is_remote = Column(Boolean, default=False)
    salary_range = Column(Text, default="")
    description = Column(Text, default="")
    url = Column(Text, unique=True, nullable=False)
    source_site = Column(Text, default="")
    match_score = Column(Integer, default=0)
    match_reason = Column(Text, default="")
    resume_id = Column(Integer, nullable=True)
    found_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    status = Column(String(20), default="new")
    saved_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, nullable=False)
    applied_at = Column(DateTime, nullable=True)
    method = Column(Text, default="manual")
    status = Column(Text, default="pending")
    notes = Column(Text, default="")


class SavedSearch(Base):
    """Persisted search configuration that can be re-run and checked for new matches."""

    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, nullable=False)
    preferences_id = Column(Integer, nullable=True)
    name = Column(Text, default="")
    keywords = Column(Text, default="[]")  # JSON array
    persian_keywords = Column(Text, default="[]")  # JSON array
    locations = Column(Text, default="[]")  # JSON array
    job_type = Column(Text, default="")
    min_salary = Column(Integer, nullable=True)
    preferred_sites = Column(Text, default="[]")  # JSON array
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def get_keywords(self) -> list[str]:
        return json.loads(self.keywords or "[]")

    def get_persian_keywords(self) -> list[str]:
        return json.loads(self.persian_keywords or "[]")

    def get_locations(self) -> list[str]:
        return json.loads(self.locations or "[]")

    def get_preferred_sites(self) -> list[str]:
        return json.loads(self.preferred_sites or "[]")


class JobAlert(Base):
    """Tracks new job matches found since the last time a saved search was checked."""

    __tablename__ = "job_alerts"

    id = Column(Integer, primary_key=True)
    saved_search_id = Column(Integer, nullable=False)
    job_id = Column(Integer, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


# ── Engine & session factory ────────────────────────────────────────

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
