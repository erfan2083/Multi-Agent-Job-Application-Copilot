"""Scraper for Indeed.com — international job board."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from backend.scrapers.base import BaseScraper, JobResult

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    site_name = "indeed"
    base_url = "https://www.indeed.com"

    def _get_headers(self) -> dict:
        headers = super()._get_headers()
        headers["Referer"] = "https://www.google.com/"
        return headers

    async def search(self, keywords: list[str], location: str = "") -> list[JobResult]:
        results: list[JobResult] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for keyword in keywords:
                if len(results) >= self.max_jobs:
                    break

                encoded = quote_plus(keyword)
                url = f"{self.base_url}/jobs?q={encoded}"
                if location:
                    url += f"&l={quote_plus(location)}"

                html = await self._fetch(url, client)
                if not html:
                    await self._delay()
                    continue

                soup = BeautifulSoup(html, "html.parser")
                job_cards = soup.select(
                    ".job_seen_beacon, .jobsearch-ResultsList > li, "
                    ".result, .tapItem"
                )

                for card in job_cards:
                    if len(results) >= self.max_jobs:
                        break

                    try:
                        title_el = card.select_one(
                            "h2.jobTitle a, .jobTitle > a, "
                            "a[data-jk], h2 a"
                        )
                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        job_id = title_el.get("data-jk", "")
                        href = title_el.get("href", "")

                        if href and not href.startswith("http"):
                            link = self.base_url + href
                        elif job_id:
                            link = f"{self.base_url}/viewjob?jk={job_id}"
                        else:
                            link = href

                        company_el = card.select_one(
                            ".companyName, [data-testid='company-name'], "
                            ".company"
                        )
                        company = company_el.get_text(strip=True) if company_el else ""

                        location_el = card.select_one(
                            ".companyLocation, [data-testid='text-location'], "
                            ".location"
                        )
                        loc = location_el.get_text(strip=True) if location_el else ""

                        snippet_el = card.select_one(
                            ".job-snippet, .summary, "
                            "[class*='snippet']"
                        )
                        description = (
                            snippet_el.get_text(strip=True)[:1000] if snippet_el else ""
                        )

                        salary_el = card.select_one(
                            ".salary-snippet-container, "
                            "[class*='salary'], .metadata"
                        )
                        salary = salary_el.get_text(strip=True) if salary_el else ""

                        is_remote = "remote" in (title + loc).lower()

                        if title and link:
                            results.append(
                                JobResult(
                                    title=title,
                                    company=company,
                                    location=loc,
                                    url=link,
                                    source_site=self.site_name,
                                    description=description,
                                    is_remote=is_remote,
                                    salary_range=salary,
                                )
                            )
                    except Exception as e:
                        logger.debug(f"[indeed] Error parsing card: {e}")
                        continue

                await self._delay()

        return results
