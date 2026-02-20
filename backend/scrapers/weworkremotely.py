"""Scraper for WeWorkRemotely.com — remote-only job board."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from backend.scrapers.base import BaseScraper, JobResult

logger = logging.getLogger(__name__)


class WeWorkRemotelyScraper(BaseScraper):
    site_name = "weworkremotely"
    base_url = "https://weworkremotely.com"

    async def search(self, keywords: list[str], location: str = "") -> list[JobResult]:
        results: list[JobResult] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for keyword in keywords:
                if len(results) >= self.max_jobs:
                    break

                encoded = quote_plus(keyword)
                url = f"{self.base_url}/remote-jobs/search?term={encoded}"

                html = await self._fetch(url, client)
                if not html:
                    await self._delay()
                    continue

                soup = BeautifulSoup(html, "html.parser")
                job_items = soup.select(
                    "li.feature, section.jobs article li, "
                    "li:has(a[href*='/remote-jobs/'])"
                )

                for item in job_items:
                    if len(results) >= self.max_jobs:
                        break

                    try:
                        link_el = item.select_one(
                            "a[href*='/remote-jobs/'], a.tooltip"
                        )
                        if not link_el:
                            continue

                        href = link_el.get("href", "")
                        if not href or href == "#":
                            continue
                        if not href.startswith("http"):
                            link = self.base_url + href
                        else:
                            link = href

                        title_el = item.select_one(
                            ".title, h3, span.title"
                        )
                        title = title_el.get_text(strip=True) if title_el else link_el.get_text(strip=True)

                        company_el = item.select_one(
                            ".company, span.company, h2"
                        )
                        company = company_el.get_text(strip=True) if company_el else ""

                        region_el = item.select_one(
                            ".region, .location"
                        )
                        loc = region_el.get_text(strip=True) if region_el else "Remote"

                        if title and len(title) > 2:
                            results.append(
                                JobResult(
                                    title=title,
                                    company=company,
                                    location=loc,
                                    url=link,
                                    source_site=self.site_name,
                                    is_remote=True,
                                )
                            )
                    except Exception as e:
                        logger.debug(f"[weworkremotely] Error parsing item: {e}")
                        continue

                await self._delay()

        return results
