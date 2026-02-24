"""Scraper for JobVision.ir — Iranian job board with JSON API."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx

from backend.scrapers.base import BaseScraper, JobResult

logger = logging.getLogger(__name__)


class JobVisionScraper(BaseScraper):
    site_name = "jobvision"
    base_url = "https://jobvision.ir"
    api_url = "https://api.jobvision.ir/api/v1"

    async def search(self, keywords: list[str], location: str = "") -> list[JobResult]:
        results: list[JobResult] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for keyword in keywords:
                if len(results) >= self.max_jobs:
                    break

                # Try the JSON API first
                try:
                    api_results = await self._search_api(client, keyword, location)
                    results.extend(api_results)
                except Exception:
                    # Fall back to HTML scraping
                    html_results = await self._search_html(client, keyword, location)
                    results.extend(html_results)

                await self._delay()

        return results[: self.max_jobs]

    def _get_api_headers(self) -> dict:
        """Lightweight headers for the JSON API."""
        import random
        from backend.scrapers.base import USER_AGENTS

        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
            "Connection": "keep-alive",
            "Referer": self.base_url,
            "Origin": self.base_url,
        }

    async def _search_api(
        self, client: httpx.AsyncClient, keyword: str, location: str
    ) -> list[JobResult]:
        """Search using JobVision's JSON API."""
        results: list[JobResult] = []

        url = f"{self.api_url}/jobs"
        params = {"q": keyword, "page": 1, "size": self.max_jobs}
        if location:
            params["location"] = location

        resp = await client.get(
            url, params=params, headers=self._get_api_headers(), timeout=20.0
        )
        resp.raise_for_status()
        data = resp.json()

        # Navigate various response shapes the API might return
        jobs = data.get("data", data.get("items", data.get("results", [])))
        if isinstance(jobs, dict):
            jobs = jobs.get("items", jobs.get("jobs", []))

        for job in jobs:
            if len(results) >= self.max_jobs:
                break

            title = job.get("title", job.get("jobTitle", ""))
            company = job.get("companyName", job.get("company", {}).get("name", ""))
            loc = job.get("location", job.get("city", ""))
            job_id = job.get("id", job.get("jobId", ""))
            link = f"{self.base_url}/jobs/{job_id}" if job_id else ""
            description = job.get("description", job.get("summary", ""))[:2000]
            is_remote = job.get("isRemote", False) or "remote" in title.lower()
            salary = job.get("salary", job.get("salaryRange", ""))
            if isinstance(salary, dict):
                salary = f"{salary.get('min', '')}-{salary.get('max', '')}"

            if title:
                results.append(
                    JobResult(
                        title=title,
                        company=company,
                        location=str(loc),
                        url=link,
                        source_site=self.site_name,
                        description=description,
                        is_remote=is_remote,
                        salary_range=str(salary),
                    )
                )

        return results

    async def _search_html(
        self, client: httpx.AsyncClient, keyword: str, location: str
    ) -> list[JobResult]:
        """Fallback: scrape HTML search page."""
        from bs4 import BeautifulSoup

        results: list[JobResult] = []
        encoded = quote_plus(keyword)
        url = f"{self.base_url}/jobs?q={encoded}"

        html = await self._fetch(url, client)
        if not html:
            return results

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(
            ".job-card, .job-item, [class*='JobCard'], "
            "[class*='jobCard'], article, div[data-id]"
        )

        # Fallback: find links to job pages
        if not cards:
            job_links = soup.select("a[href*='/jobs/']")
            cards = [a.parent for a in job_links if a.parent]

        for card in cards:
            if len(results) >= self.max_jobs:
                break

            try:
                title_el = card.select_one("h2, h3, a[href*='/jobs/']")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                link_el = card.select_one("a[href*='/jobs/']")
                link = ""
                if link_el:
                    link = link_el.get("href", "")
                    if not link.startswith("http"):
                        link = self.base_url + link

                company_el = card.select_one("[class*='company'], .company-name")
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one("[class*='location']")
                loc = loc_el.get_text(strip=True) if loc_el else ""

                results.append(
                    JobResult(
                        title=title,
                        company=company,
                        location=loc,
                        url=link,
                        source_site=self.site_name,
                    )
                )
            except Exception as e:
                logger.debug(f"[jobvision] Error parsing card: {e}")
                continue

        return results
