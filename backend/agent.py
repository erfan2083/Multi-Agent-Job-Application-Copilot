"""Main agent orchestration — coordinates resume analysis, search, and scoring."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from datetime import datetime, timezone

from backend.claude_session import ClaudeSession, fallback_parse_resume
from backend.config import settings
from backend.database import (
    JobAlert,
    JobListing,
    ResumeProfile,
    SavedSearch,
    SearchPreference,
    SessionLocal,
)
from backend.models import ParsedResume, SearchQueries
from backend.tools.job_scorer import score_job
from backend.tools.job_scraper import scrape_all
from backend.tools.query_builder import build_search_queries
from backend.tools.report_generator import generate_report
from backend.tools.resume_parser import parse_resume

logger = logging.getLogger(__name__)

RESUME_ANALYSIS_PROMPT = """You are a resume parser. Extract the following from this resume and return ONLY valid JSON, no extra text:

{{
  "full_name": "",
  "email": "",
  "phone": "",
  "skills": ["skill1", "skill2"],
  "technical_skills": ["Python", "React"],
  "soft_skills": ["communication"],
  "job_titles": ["Senior Backend Developer"],
  "total_experience_years": 5,
  "education": {{
    "degree": "Bachelor",
    "field": "Computer Science",
    "university": ""
  }},
  "languages": ["Persian", "English"],
  "summary": "brief profile summary"
}}

Resume text:
{resume_text}"""

PREFERENCES_PROMPT = """The user described their job preferences in natural language. Parse them and return ONLY valid JSON:

{{
  "job_type": "remote",
  "locations": ["Tehran", "remote"],
  "fields": ["backend", "python"],
  "min_salary": 2000,
  "preferred_sites": [],
  "keywords": ["Python developer", "backend engineer"],
  "persian_keywords": ["برنامه‌نویس پایتون"]
}}

User message (may be in Persian or English):
{message}"""


class JobHunterAgent:
    """Main agent that orchestrates the entire job hunting workflow."""

    def __init__(self) -> None:
        self.claude: ClaudeSession | None = None
        self._claude_available = False

    async def init_claude(self) -> bool:
        """Initialize the Claude browser session."""
        try:
            self.claude = ClaudeSession()
            await self.claude.start()

            if not self.claude.is_ready:
                success = await self.claude.login()
                if not success:
                    logger.warning("Claude login failed; will use fallback scoring")
                    self._claude_available = False
                    return False

            self._claude_available = True
            return True
        except Exception as e:
            logger.warning(f"Could not initialize Claude session: {e}")
            self._claude_available = False
            return False

    async def close(self) -> None:
        if self.claude:
            await self.claude.close()

    # ── Resume Analysis ─────────────────────────────────────────────

    async def analyze_resume(self, file_path: str) -> tuple[int, dict]:
        """Parse a resume file and analyze it.

        Returns (resume_id, profile_dict).
        """
        # Extract raw text
        raw_text = parse_resume(file_path)
        filename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path

        # Analyze with Claude or fallback
        profile_data = await self._analyze_resume_text(raw_text)

        # Save to database
        db = SessionLocal()
        try:
            resume = ResumeProfile(
                filename=filename,
                raw_text=raw_text,
                full_name=profile_data.get("full_name", ""),
                email=profile_data.get("email", ""),
                phone=profile_data.get("phone", ""),
                skills=json.dumps(
                    profile_data.get("skills", [])
                    or profile_data.get("technical_skills", []),
                    ensure_ascii=False,
                ),
                titles=json.dumps(
                    profile_data.get("job_titles", []), ensure_ascii=False
                ),
                experience_years=profile_data.get("total_experience_years", 0),
                education=json.dumps(
                    profile_data.get("education", {}), ensure_ascii=False
                ),
                languages=json.dumps(
                    profile_data.get("languages", []), ensure_ascii=False
                ),
                summary=profile_data.get("summary", ""),
            )
            db.add(resume)
            db.commit()
            db.refresh(resume)
            return resume.id, resume.to_profile_dict()
        finally:
            db.close()

    async def _analyze_resume_text(self, raw_text: str) -> dict:
        """Analyze resume text using Claude or fallback."""
        if self.claude and self.claude.is_ready:
            try:
                prompt = RESUME_ANALYSIS_PROMPT.format(
                    resume_text=raw_text[:8000]
                )
                result = await self.claude.ask_for_json(prompt)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Claude resume analysis failed: {e}")

        return fallback_parse_resume(raw_text)

    # ── Preferences ─────────────────────────────────────────────────

    async def parse_preferences(
        self, resume_id: int, message: str
    ) -> tuple[int, dict]:
        """Parse user preferences from natural language.

        Returns (preferences_id, structured_preferences).
        """
        prefs_data = await self._parse_preferences_text(message)

        db = SessionLocal()
        try:
            pref = SearchPreference(
                resume_id=resume_id,
                job_type=prefs_data.get("job_type", ""),
                locations=json.dumps(
                    prefs_data.get("locations", []), ensure_ascii=False
                ),
                fields=json.dumps(
                    prefs_data.get("fields", []), ensure_ascii=False
                ),
                min_salary=prefs_data.get("min_salary"),
                preferred_sites=json.dumps(
                    prefs_data.get("preferred_sites", []), ensure_ascii=False
                ),
                keywords=json.dumps(
                    prefs_data.get("keywords", []), ensure_ascii=False
                ),
                persian_keywords=json.dumps(
                    prefs_data.get("persian_keywords", []), ensure_ascii=False
                ),
                raw_message=message,
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)
            return pref.id, prefs_data
        finally:
            db.close()

    async def _parse_preferences_text(self, message: str) -> dict:
        """Parse preferences using Claude or fallback."""
        if self.claude and self.claude.is_ready:
            try:
                prompt = PREFERENCES_PROMPT.format(message=message)
                result = await self.claude.ask_for_json(prompt)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Claude preferences parsing failed: {e}")

        # Fallback: extract basic info from text
        return self._fallback_parse_preferences(message)

    def _fallback_parse_preferences(self, message: str) -> dict:
        """Basic rule-based preference parsing."""
        msg_lower = message.lower()

        job_type = ""
        if "remote" in msg_lower or "ریموت" in message or "دورکاری" in message:
            job_type = "remote"
        elif "onsite" in msg_lower or "حضوری" in message:
            job_type = "onsite"
        elif "hybrid" in msg_lower or "هیبرید" in message:
            job_type = "hybrid"

        locations = []
        if "remote" in msg_lower or "ریموت" in message:
            locations.append("remote")
        if "tehran" in msg_lower or "تهران" in message:
            locations.append("Tehran")
        if "isfahan" in msg_lower or "اصفهان" in message:
            locations.append("Isfahan")

        # Detect fields/skills
        fields = []
        field_map = {
            "backend": "backend",
            "بک‌اند": "backend",
            "frontend": "frontend",
            "فرانت‌اند": "frontend",
            "fullstack": "fullstack",
            "فول‌استک": "fullstack",
            "devops": "devops",
            "data": "data",
            "machine learning": "ml",
            "mobile": "mobile",
        }
        for key, val in field_map.items():
            if key in msg_lower or key in message:
                fields.append(val)

        # Detect keywords
        keywords = []
        tech_in_msg = [
            "python", "javascript", "react", "node", "java", "go",
            "rust", "c++", "typescript", "django", "flask", "fastapi",
            "docker", "kubernetes", "aws",
        ]
        for tech in tech_in_msg:
            if tech in msg_lower:
                keywords.append(f"{tech} developer")

        if not keywords and fields:
            keywords = [f"{f} developer" for f in fields]
        if not keywords:
            keywords = ["software developer"]

        # Detect salary
        min_salary = None
        import re

        salary_match = re.search(r"(\d+)\s*(?:دلار|dollar|\$|usd)", msg_lower)
        if salary_match:
            min_salary = int(salary_match.group(1))

        return {
            "job_type": job_type,
            "locations": locations,
            "fields": fields,
            "min_salary": min_salary,
            "preferred_sites": [],
            "keywords": keywords,
            "persian_keywords": [],
        }

    # ── Job Search ──────────────────────────────────────────────────

    async def search_jobs(
        self, resume_id: int, preferences_id: int | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Run the full job search pipeline, yielding status updates.

        Yields dicts like:
            {"type": "status", "message": "..."}
            {"type": "job", "data": {...}}
            {"type": "done", "total": N, "report": "..."}
            {"type": "error", "message": "..."}
        """
        db = SessionLocal()
        try:
            # Load resume profile
            resume = db.query(ResumeProfile).filter_by(id=resume_id).first()
            if not resume:
                yield {"type": "error", "message": "Resume not found"}
                return

            profile = resume.to_profile_dict()

            yield {
                "type": "status",
                "message": "رزومه بارگذاری شد. در حال آماده‌سازی جستجو...",
            }

            # Load or create preferences
            preferences_text = ""
            pref_keywords: list[str] = []
            pref_persian: list[str] = []
            pref_locations: list[str] = []
            pref_sites: list[str] = []

            if preferences_id:
                pref = (
                    db.query(SearchPreference)
                    .filter_by(id=preferences_id)
                    .first()
                )
                if pref:
                    preferences_text = pref.raw_message
                    pref_keywords = pref.get_keywords()
                    pref_persian = pref.get_persian_keywords()
                    pref_locations = pref.get_locations()
                    pref_sites = pref.get_preferred_sites()

            # Build search queries
            yield {
                "type": "status",
                "message": "در حال ساخت کوئری‌های جستجو...",
            }

            if not pref_keywords:
                queries = await build_search_queries(
                    self.claude, profile, preferences_text
                )
                pref_keywords = queries.keywords
                pref_persian = queries.persian_keywords
                pref_locations = queries.locations

            if not pref_keywords:
                # Use profile skills/titles as fallback
                pref_keywords = profile.get("job_titles", [])[:3]
                if not pref_keywords:
                    skills = profile.get("skills", [])[:3]
                    pref_keywords = [f"{s} developer" for s in skills]

            yield {
                "type": "status",
                "message": f"در حال جستجو با کلمات کلیدی: {', '.join(pref_keywords[:3])}...",
            }

            # Track scraping progress
            site_status: dict[str, str] = {}

            def on_start(site: str) -> None:
                site_status[site] = "searching"

            def on_done(site: str, count: int) -> None:
                site_status[site] = f"found {count}"

            def on_error(site: str, msg: str) -> None:
                site_status[site] = f"failed: {msg}"

            yield {
                "type": "status",
                "message": "در حال جستجو در سایت‌های کاریابی...",
            }

            # Run scrapers
            raw_jobs = await scrape_all(
                keywords=pref_keywords,
                persian_keywords=pref_persian,
                locations=pref_locations,
                preferred_sites=pref_sites or None,
                on_site_start=on_start,
                on_site_done=on_done,
                on_site_error=on_error,
            )

            # Report scraping results
            total_found = len(raw_jobs)
            yield {
                "type": "status",
                "message": f"{total_found} موقعیت شغلی پیدا شد. در حال بررسی تطابق...",
            }

            # Score each job
            scored_jobs: list[dict] = []

            for i, job_result in enumerate(raw_jobs):
                job_dict = job_result.to_dict()

                score_result = await score_job(self.claude, profile, job_dict)

                job_dict["match_score"] = score_result.score
                job_dict["match_reason"] = score_result.reason

                # Only keep jobs above minimum score
                if score_result.score >= settings.min_match_score:
                    scored_jobs.append(job_dict)

                    # Save to database
                    existing = (
                        db.query(JobListing)
                        .filter_by(url=job_dict["url"])
                        .first()
                    )
                    if not existing:
                        listing = JobListing(
                            title=job_dict["title"],
                            company=job_dict["company"],
                            location=job_dict["location"],
                            is_remote=job_dict.get("is_remote", False),
                            salary_range=job_dict.get("salary_range", ""),
                            description=job_dict.get("description", ""),
                            url=job_dict["url"],
                            source_site=job_dict["source_site"],
                            match_score=score_result.score,
                            match_reason=score_result.reason,
                            resume_id=resume_id,
                        )
                        db.add(listing)

                    # Stream each qualifying job to frontend
                    yield {"type": "job", "data": job_dict}

                # Progress update every 5 jobs
                if (i + 1) % 5 == 0:
                    yield {
                        "type": "status",
                        "message": f"بررسی شد: {i + 1}/{total_found}...",
                    }

            db.commit()

            # Sort by score
            scored_jobs.sort(key=lambda j: j["match_score"], reverse=True)

            # Generate report
            report = await generate_report(self.claude, profile, scored_jobs)

            yield {
                "type": "done",
                "total": len(scored_jobs),
                "report": report,
                "site_status": site_status,
            }

        except Exception as e:
            logger.error(f"Search pipeline error: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}
        finally:
            db.close()

    # ── Saved Search Re-run (Phase 2) ────────────────────────────────

    async def run_saved_search(
        self, saved_search_id: int
    ) -> AsyncIterator[dict[str, Any]]:
        """Re-run a saved search, finding only NEW jobs not already in the DB.

        Creates JobAlert entries for each new match found.
        Yields the same event format as search_jobs().
        """
        db = SessionLocal()
        try:
            search = db.query(SavedSearch).filter_by(id=saved_search_id).first()
            if not search:
                yield {"type": "error", "message": "Saved search not found"}
                return

            resume = db.query(ResumeProfile).filter_by(id=search.resume_id).first()
            if not resume:
                yield {"type": "error", "message": "Resume not found"}
                return

            profile = resume.to_profile_dict()
            keywords = search.get_keywords()
            persian_keywords = search.get_persian_keywords()
            locations = search.get_locations()
            preferred_sites = search.get_preferred_sites()

            yield {
                "type": "status",
                "message": f"اجرای مجدد جستجوی ذخیره‌شده: {search.name}...",
            }

            # Collect existing URLs to detect truly new jobs
            existing_urls = set(
                row[0] for row in db.query(JobListing.url).all()
            )

            # Run scrapers
            site_status: dict[str, str] = {}

            def on_start(site: str) -> None:
                site_status[site] = "searching"

            def on_done(site: str, count: int) -> None:
                site_status[site] = f"found {count}"

            def on_error(site: str, msg: str) -> None:
                site_status[site] = f"failed: {msg}"

            yield {
                "type": "status",
                "message": "در حال جستجو در سایت‌های کاریابی...",
            }

            raw_jobs = await scrape_all(
                keywords=keywords,
                persian_keywords=persian_keywords,
                locations=locations,
                preferred_sites=preferred_sites or None,
                on_site_start=on_start,
                on_site_done=on_done,
                on_site_error=on_error,
            )

            total_found = len(raw_jobs)
            yield {
                "type": "status",
                "message": f"{total_found} موقعیت شغلی پیدا شد. در حال بررسی تطابق...",
            }

            new_jobs: list[dict] = []
            new_alert_count = 0

            for i, job_result in enumerate(raw_jobs):
                job_dict = job_result.to_dict()

                score_result = await score_job(self.claude, profile, job_dict)
                job_dict["match_score"] = score_result.score
                job_dict["match_reason"] = score_result.reason

                if score_result.score >= settings.min_match_score:
                    is_new = job_dict["url"] not in existing_urls

                    if is_new:
                        # Save the new job listing
                        listing = JobListing(
                            title=job_dict["title"],
                            company=job_dict["company"],
                            location=job_dict["location"],
                            is_remote=job_dict.get("is_remote", False),
                            salary_range=job_dict.get("salary_range", ""),
                            description=job_dict.get("description", ""),
                            url=job_dict["url"],
                            source_site=job_dict["source_site"],
                            match_score=score_result.score,
                            match_reason=score_result.reason,
                            resume_id=search.resume_id,
                        )
                        db.add(listing)
                        db.flush()  # Get the id

                        # Create an alert
                        alert = JobAlert(
                            saved_search_id=saved_search_id,
                            job_id=listing.id,
                        )
                        db.add(alert)
                        new_alert_count += 1

                        existing_urls.add(job_dict["url"])

                    new_jobs.append(job_dict)
                    job_dict["is_new"] = is_new
                    yield {"type": "job", "data": job_dict}

                if (i + 1) % 5 == 0:
                    yield {
                        "type": "status",
                        "message": f"بررسی شد: {i + 1}/{total_found}...",
                    }

            # Update last_run_at
            search.last_run_at = datetime.now(timezone.utc)
            db.commit()

            new_jobs.sort(key=lambda j: j["match_score"], reverse=True)
            report = await generate_report(self.claude, profile, new_jobs)

            yield {
                "type": "done",
                "total": len(new_jobs),
                "new_alerts": new_alert_count,
                "report": report,
                "site_status": site_status,
            }

        except Exception as e:
            logger.error(f"Saved search re-run error: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}
        finally:
            db.close()
