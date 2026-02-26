"""Job scraper orchestrator — runs all scrapers in parallel.

Uses python-jobspy for major international boards (Indeed, LinkedIn,
Glassdoor, Google) and custom scrapers for Iranian sites + Remotive.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

from backend.scrapers.base import BaseScraper, JobResult
from backend.scrapers.irantalent import IranTalentScraper
from backend.scrapers.jobinja import JobinjaScraper
from backend.scrapers.jobvision import JobVisionScraper
from backend.scrapers.remotive import RemotiveScraper

logger = logging.getLogger(__name__)

# Registry of custom HTML scrapers
ALL_SCRAPERS: dict[str, type[BaseScraper]] = {
    "jobinja": JobinjaScraper,
    "irantalent": IranTalentScraper,
    "jobvision": JobVisionScraper,
    "remotive": RemotiveScraper,
}

# Iranian sites use Persian keywords
IRANIAN_SITES = {"jobinja", "irantalent", "jobvision"}


async def scrape_all(
    keywords: list[str],
    persian_keywords: list[str] | None = None,
    locations: list[str] | None = None,
    preferred_sites: list[str] | None = None,
    on_site_start: Callable[[str], None] | None = None,
    on_site_done: Callable[[str, int], None] | None = None,
    on_site_error: Callable[[str, str], None] | None = None,
) -> list[JobResult]:
    """Run all scrapers in parallel and collect results.

    International boards (Indeed, LinkedIn, Glassdoor, Google) are handled
    by python-jobspy in a single call.  Custom scrapers handle Remotive and
    Iranian job boards.
    """
    persian_keywords = persian_keywords or []
    locations = locations or []
    location_str = ", ".join(locations) if locations else ""

    # ── Custom HTML scrapers ──────────────────────────────────────────
    sites_to_scrape = set(ALL_SCRAPERS.keys())
    if preferred_sites:
        sites_to_scrape = sites_to_scrape & set(preferred_sites)
    if not sites_to_scrape:
        sites_to_scrape = set(ALL_SCRAPERS.keys())

    async def _run_scraper(site_name: str) -> list[JobResult]:
        scraper_cls = ALL_SCRAPERS[site_name]
        scraper = scraper_cls()

        if on_site_start:
            on_site_start(site_name)

        # Choose keywords based on site type
        if site_name in IRANIAN_SITES:
            kws = persian_keywords if persian_keywords else keywords
        else:
            kws = keywords

        try:
            results = await scraper.search_safe(kws, location_str)
            if on_site_done:
                on_site_done(site_name, len(results))
            return results
        except Exception as e:
            if on_site_error:
                on_site_error(site_name, str(e))
            return []

    # ── python-jobspy (Indeed, LinkedIn, Glassdoor, Google) ───────────
    async def _run_jobspy() -> list[JobResult]:
        try:
            from backend.scrapers.jobspy_scraper import JobSpyScraper
        except ImportError:
            logger.warning("python-jobspy not installed — skipping jobspy")
            return []

        if on_site_start:
            on_site_start("jobspy")

        scraper = JobSpyScraper()
        try:
            results = await scraper.search_safe(keywords, location_str)
            if on_site_done:
                on_site_done("jobspy", len(results))
            return results
        except Exception as e:
            if on_site_error:
                on_site_error("jobspy", str(e))
            return []

    # Run everything concurrently
    tasks = [_run_scraper(site) for site in sites_to_scrape]
    tasks.append(_run_jobspy())
    all_results = await asyncio.gather(*tasks)

    # Flatten and deduplicate by URL
    seen_urls: set[str] = set()
    combined: list[JobResult] = []

    for site_results in all_results:
        for job in site_results:
            if job.url and job.url not in seen_urls:
                seen_urls.add(job.url)
                combined.append(job)

    logger.info(f"Total jobs found across all sites: {len(combined)}")
    return combined
