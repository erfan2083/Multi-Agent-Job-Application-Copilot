"""Job scraper orchestrator — runs all scrapers in parallel."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

from backend.scrapers.base import BaseScraper, JobResult
from backend.scrapers.indeed import IndeedScraper
from backend.scrapers.irantalent import IranTalentScraper
from backend.scrapers.jobinja import JobinjaScraper
from backend.scrapers.jobvision import JobVisionScraper
from backend.scrapers.linkedin import LinkedInScraper
from backend.scrapers.remotive import RemotiveScraper
from backend.scrapers.wellfound import WellfoundScraper
from backend.scrapers.weworkremotely import WeWorkRemotelyScraper

logger = logging.getLogger(__name__)

# Registry of all available scrapers
ALL_SCRAPERS: dict[str, type[BaseScraper]] = {
    "jobinja": JobinjaScraper,
    "irantalent": IranTalentScraper,
    "jobvision": JobVisionScraper,
    "linkedin": LinkedInScraper,
    "indeed": IndeedScraper,
    "remotive": RemotiveScraper,
    "weworkremotely": WeWorkRemotelyScraper,
    "wellfound": WellfoundScraper,
}

# Iranian sites use Persian keywords, international sites use English
IRANIAN_SITES = {"jobinja", "irantalent", "jobvision"}
INTERNATIONAL_SITES = {"linkedin", "indeed", "remotive", "weworkremotely", "wellfound"}


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

    Args:
        keywords: English keywords for international sites.
        persian_keywords: Persian keywords for Iranian sites.
        locations: Location filters.
        preferred_sites: Limit to these sites only (empty = all).
        on_site_start: Callback when a site starts scraping.
        on_site_done: Callback when a site finishes (site_name, job_count).
        on_site_error: Callback when a site fails (site_name, error_msg).

    Returns:
        Combined list of job results from all sites.
    """
    persian_keywords = persian_keywords or []
    locations = locations or []
    location_str = ", ".join(locations) if locations else ""

    # Determine which sites to scrape
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

    # Run all scrapers concurrently
    tasks = [_run_scraper(site) for site in sites_to_scrape]
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
