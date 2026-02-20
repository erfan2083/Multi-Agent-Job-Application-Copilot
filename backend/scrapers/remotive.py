"""Scraper for Remotive.com — remote jobs via their public API."""

from __future__ import annotations

import logging

import httpx

from backend.scrapers.base import BaseScraper, JobResult

logger = logging.getLogger(__name__)


class RemotiveScraper(BaseScraper):
    site_name = "remotive"
    base_url = "https://remotive.com"
    api_url = "https://remotive.com/api/remote-jobs"

    async def search(self, keywords: list[str], location: str = "") -> list[JobResult]:
        """Search Remotive using their public JSON API."""
        results: list[JobResult] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for keyword in keywords:
                if len(results) >= self.max_jobs:
                    break

                params = {"search": keyword, "limit": self.max_jobs}

                try:
                    resp = await client.get(
                        self.api_url,
                        params=params,
                        headers=self._get_headers(),
                        timeout=20.0,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.warning(f"[remotive] API request failed: {e}")
                    await self._delay()
                    continue

                jobs = data.get("jobs", [])

                for job in jobs:
                    if len(results) >= self.max_jobs:
                        break

                    title = job.get("title", "")
                    company = job.get("company_name", "")
                    loc = job.get("candidate_required_location", "Worldwide")
                    url = job.get("url", "")
                    description = job.get("description", "")[:2000]
                    salary = job.get("salary", "")
                    job_type = job.get("job_type", "")

                    # Clean HTML from description
                    if "<" in description:
                        from bs4 import BeautifulSoup

                        description = BeautifulSoup(
                            description, "html.parser"
                        ).get_text(strip=True)[:2000]

                    if title and url:
                        results.append(
                            JobResult(
                                title=title,
                                company=company,
                                location=loc,
                                url=url,
                                source_site=self.site_name,
                                description=description,
                                is_remote=True,
                                salary_range=salary or "",
                            )
                        )

                await self._delay()

        return results
