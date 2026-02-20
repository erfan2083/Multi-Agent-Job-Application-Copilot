"""Scraper for LinkedIn.com — uses public job search (no login required for search)."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from backend.scrapers.base import BaseScraper, JobResult

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    site_name = "linkedin"
    base_url = "https://www.linkedin.com"

    async def search(self, keywords: list[str], location: str = "") -> list[JobResult]:
        """Search LinkedIn's public job listings (no auth required)."""
        results: list[JobResult] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for keyword in keywords:
                if len(results) >= self.max_jobs:
                    break

                encoded = quote_plus(keyword)
                # LinkedIn's public job search URL
                url = (
                    f"{self.base_url}/jobs/search"
                    f"?keywords={encoded}&position=1&pageNum=0"
                )
                if location:
                    url += f"&location={quote_plus(location)}"

                # Also try the guest job search API
                api_url = (
                    f"{self.base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search"
                    f"?keywords={encoded}&start=0"
                )
                if location:
                    api_url += f"&location={quote_plus(location)}"

                html = await self._fetch(api_url, client)
                if not html:
                    html = await self._fetch(url, client)
                if not html:
                    await self._delay()
                    continue

                soup = BeautifulSoup(html, "html.parser")
                job_cards = soup.select(
                    ".base-card, .job-search-card, li"
                )

                for card in job_cards:
                    if len(results) >= self.max_jobs:
                        break

                    try:
                        title_el = card.select_one(
                            ".base-search-card__title, "
                            "h3.base-search-card__title, "
                            "h3"
                        )
                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        if not title or len(title) < 3:
                            continue

                        link_el = card.select_one("a.base-card__full-link, a[href*='/jobs/']")
                        link = ""
                        if link_el:
                            link = link_el.get("href", "").split("?")[0]

                        company_el = card.select_one(
                            ".base-search-card__subtitle, "
                            "h4.base-search-card__subtitle, "
                            "h4"
                        )
                        company = company_el.get_text(strip=True) if company_el else ""

                        location_el = card.select_one(
                            ".job-search-card__location, "
                            ".base-search-card__metadata"
                        )
                        loc = location_el.get_text(strip=True) if location_el else ""

                        is_remote = "remote" in (title + loc).lower()

                        if title and link:
                            results.append(
                                JobResult(
                                    title=title,
                                    company=company,
                                    location=loc,
                                    url=link,
                                    source_site=self.site_name,
                                    is_remote=is_remote,
                                )
                            )
                    except Exception as e:
                        logger.debug(f"[linkedin] Error parsing card: {e}")
                        continue

                await self._delay()

        return results
