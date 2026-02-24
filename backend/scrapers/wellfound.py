"""Scraper for Wellfound.com (formerly AngelList) — startup job board."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from backend.scrapers.base import BaseScraper, JobResult

logger = logging.getLogger(__name__)


class WellfoundScraper(BaseScraper):
    site_name = "wellfound"
    base_url = "https://wellfound.com"

    def _get_headers(self) -> dict:
        headers = super()._get_headers()
        headers["Referer"] = "https://wellfound.com/"
        return headers

    async def search(self, keywords: list[str], location: str = "") -> list[JobResult]:
        results: list[JobResult] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for keyword in keywords:
                if len(results) >= self.max_jobs:
                    break

                encoded = quote_plus(keyword)
                url = f"{self.base_url}/jobs?query={encoded}"
                if location:
                    url += f"&location={quote_plus(location)}"

                html = await self._fetch(url, client)
                if not html:
                    await self._delay()
                    continue

                soup = BeautifulSoup(html, "html.parser")
                job_cards = soup.select(
                    "[class*='styles_jobCard'], "
                    "[class*='JobCard'], "
                    ".job-listing, "
                    "div[data-test='job-card']"
                )

                for card in job_cards:
                    if len(results) >= self.max_jobs:
                        break

                    try:
                        title_el = card.select_one(
                            "h2, h3, a[href*='/jobs/'], "
                            "[class*='title']"
                        )
                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)

                        link_el = card.select_one("a[href*='/jobs/']")
                        link = ""
                        if link_el:
                            link = link_el.get("href", "")
                            if not link.startswith("http"):
                                link = self.base_url + link

                        company_el = card.select_one(
                            "[class*='company'], h4, "
                            "a[href*='/company/']"
                        )
                        company = company_el.get_text(strip=True) if company_el else ""

                        location_el = card.select_one(
                            "[class*='location'], "
                            "span:has-text('Remote')"
                        )
                        loc = location_el.get_text(strip=True) if location_el else ""

                        salary_el = card.select_one("[class*='salary']")
                        salary = salary_el.get_text(strip=True) if salary_el else ""

                        is_remote = "remote" in (title + loc).lower()

                        if title:
                            results.append(
                                JobResult(
                                    title=title,
                                    company=company,
                                    location=loc,
                                    url=link,
                                    source_site=self.site_name,
                                    is_remote=is_remote,
                                    salary_range=salary,
                                )
                            )
                    except Exception as e:
                        logger.debug(f"[wellfound] Error parsing card: {e}")
                        continue

                await self._delay()

        return results
