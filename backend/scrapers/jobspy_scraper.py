"""JobSpy scraper — wraps python-jobspy to query multiple job boards at once."""

from __future__ import annotations

import asyncio
import logging

from backend.config import settings
from backend.scrapers.base import JobResult

logger = logging.getLogger(__name__)

# Sites that python-jobspy supports.
JOBSPY_SITES = ["indeed", "linkedin", "glassdoor", "google"]

# Cap the number of keywords we iterate over to avoid excessive API calls.
MAX_KEYWORDS = 3


def _build_salary_range(row: dict) -> str:
    """Build a human-readable salary string from DataFrame row fields."""
    min_amt = row.get("min_amount")
    max_amt = row.get("max_amount")
    currency = row.get("currency", "USD")

    if min_amt is not None and max_amt is not None:
        return f"{currency} {min_amt:,.0f} - {max_amt:,.0f}"
    if min_amt is not None:
        return f"{currency} {min_amt:,.0f}+"
    if max_amt is not None:
        return f"Up to {currency} {max_amt:,.0f}"
    return ""


def _row_to_job_result(row: dict) -> JobResult:
    """Convert a single pandas row (as dict) to a JobResult."""
    location = row.get("location") or str(row.get("city", ""))

    return JobResult(
        title=row.get("title", ""),
        company=row.get("company", ""),
        location=location,
        url=row.get("job_url", ""),
        source_site=f"jobspy-{row.get('site', 'unknown')}",
        description=str(row.get("description", ""))[:2000],
        is_remote=bool(row.get("is_remote", False)),
        salary_range=_build_salary_range(row),
    )


class JobSpyScraper:
    """Multi-site scraper powered by python-jobspy.

    This class does NOT extend BaseScraper because jobspy handles multiple
    job boards in a single call.
    """

    site_name: str = "jobspy"

    def __init__(self) -> None:
        self.max_jobs: int = settings.max_jobs_per_site

    async def search(
        self, keywords: list[str], location: str = ""
    ) -> list[JobResult]:
        """Search multiple job boards via jobspy for the given keywords."""
        from jobspy import scrape_jobs

        effective_location = location or "Remote"
        results: list[JobResult] = []
        seen_urls: set[str] = set()

        for keyword in keywords[:MAX_KEYWORDS]:
            try:
                df = await asyncio.to_thread(
                    scrape_jobs,
                    site_name=JOBSPY_SITES,
                    search_term=keyword,
                    location=effective_location,
                    results_wanted=self.max_jobs,
                    hours_old=72,
                    country_indeed="USA",
                )
            except Exception:
                logger.exception(
                    "[%s] scrape_jobs failed for keyword=%r, location=%r",
                    self.site_name,
                    keyword,
                    effective_location,
                )
                continue

            if df is None or df.empty:
                logger.info(
                    "[%s] No results for keyword=%r", self.site_name, keyword
                )
                continue

            for _, row in df.iterrows():
                row_dict = row.to_dict()
                url = row_dict.get("job_url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                results.append(_row_to_job_result(row_dict))

        logger.info("[%s] Collected %d jobs (deduplicated)", self.site_name, len(results))
        return results[: self.max_jobs]

    async def search_safe(
        self, keywords: list[str], location: str = ""
    ) -> list[JobResult]:
        """Search with error handling -- never raises."""
        try:
            results = await self.search(keywords, location)
            logger.info("[%s] Found %d jobs", self.site_name, len(results))
            return results
        except Exception:
            logger.exception("[%s] Scraper failed", self.site_name)
            return []
