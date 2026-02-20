"""Scraper for Jobinja.ir — Iranian job board."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from backend.scrapers.base import BaseScraper, JobResult

logger = logging.getLogger(__name__)


class JobinjaScraper(BaseScraper):
    site_name = "jobinja"
    base_url = "https://jobinja.ir"

    async def search(self, keywords: list[str], location: str = "") -> list[JobResult]:
        results: list[JobResult] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for keyword in keywords:
                if len(results) >= self.max_jobs:
                    break

                encoded = quote_plus(keyword)
                url = f"{self.base_url}/jobs?filters%5Bkeywords%5D%5B0%5D={encoded}"

                if location:
                    url += f"&filters%5Blocations%5D%5B0%5D={quote_plus(location)}"

                html = await self._fetch(url, client)
                if not html:
                    await self._delay()
                    continue

                soup = BeautifulSoup(html, "html.parser")
                job_cards = soup.select(".o-listView__itemInfo, .c-jobListView__item")

                for card in job_cards:
                    if len(results) >= self.max_jobs:
                        break

                    try:
                        title_el = card.select_one(
                            "h3 a, .c-jobListView__titleLink, a[href*='/jobs/']"
                        )
                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        link = title_el.get("href", "")
                        if link and not link.startswith("http"):
                            link = self.base_url + link

                        company_el = card.select_one(
                            ".c-jobListView__company, .c-companyHeader__name"
                        )
                        company = company_el.get_text(strip=True) if company_el else ""

                        location_el = card.select_one(
                            ".c-jobListView__location, .c-jobListView__meta"
                        )
                        loc = location_el.get_text(strip=True) if location_el else ""

                        is_remote = any(
                            w in (title + loc).lower()
                            for w in ["remote", "ریموت", "دورکاری"]
                        )

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
                        logger.debug(f"[jobinja] Error parsing card: {e}")
                        continue

                await self._delay()

            # Fetch descriptions for each job
            for job in results[:10]:  # Limit detail fetches
                if not job.url:
                    continue
                detail_html = await self._fetch(job.url, client)
                if detail_html:
                    detail_soup = BeautifulSoup(detail_html, "html.parser")
                    desc_el = detail_soup.select_one(
                        ".o-box__text, .c-jobView__description, .s-jobDesc"
                    )
                    if desc_el:
                        job.description = desc_el.get_text(strip=True)[:2000]
                await self._delay()

        return results
