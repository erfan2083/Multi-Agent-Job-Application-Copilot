"""Scraper for IranTalent.com — Iranian job board."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from backend.scrapers.base import BaseScraper, JobResult

logger = logging.getLogger(__name__)


class IranTalentScraper(BaseScraper):
    site_name = "irantalent"
    base_url = "https://www.irantalent.com"

    def _get_headers(self) -> dict:
        headers = super()._get_headers()
        headers["Referer"] = self.base_url
        return headers

    async def search(self, keywords: list[str], location: str = "") -> list[JobResult]:
        results: list[JobResult] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for keyword in keywords:
                if len(results) >= self.max_jobs:
                    break

                encoded = quote_plus(keyword)
                url = f"{self.base_url}/en/jobs?keyword={encoded}"

                if location:
                    url += f"&location={quote_plus(location)}"

                html = await self._fetch(url, client)
                if not html:
                    await self._delay()
                    continue

                soup = BeautifulSoup(html, "html.parser")
                job_cards = soup.select(
                    ".job-list-item, .job-card, [class*='JobCard'], "
                    "[class*='jobCard'], [class*='job-item'], "
                    "article, div[data-job-id]"
                )

                # Fallback: find links to job detail pages
                if not job_cards:
                    job_links = soup.select("a[href*='/job/'], a[href*='/jobs/']")
                    job_cards = [a.parent for a in job_links if a.parent]

                for card in job_cards:
                    if len(results) >= self.max_jobs:
                        break

                    try:
                        title_el = card.select_one(
                            "h2 a, h3 a, a[href*='/job/'], a[href*='/jobs/'], "
                            ".job-title, [class*='title'] a"
                        )
                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        if not title or len(title) < 3:
                            continue

                        link = title_el.get("href", "")
                        if link and not link.startswith("http"):
                            link = self.base_url + link

                        company_el = card.select_one(
                            ".company-name, .employer-name, "
                            "[class*='company'], [class*='employer']"
                        )
                        company = company_el.get_text(strip=True) if company_el else ""

                        location_el = card.select_one(
                            ".job-location, [class*='location'], "
                            "[class*='city']"
                        )
                        loc = location_el.get_text(strip=True) if location_el else ""

                        desc_el = card.select_one(
                            ".job-description, .job-summary, p"
                        )
                        description = desc_el.get_text(strip=True)[:1000] if desc_el else ""

                        is_remote = any(
                            w in (title + loc + description).lower()
                            for w in ["remote", "ریموت", "دورکاری"]
                        )

                        # Deduplicate
                        if any(r.url == link for r in results):
                            continue

                        results.append(
                            JobResult(
                                title=title,
                                company=company,
                                location=loc,
                                url=link,
                                source_site=self.site_name,
                                description=description,
                                is_remote=is_remote,
                            )
                        )
                    except Exception as e:
                        logger.debug(f"[irantalent] Error parsing card: {e}")
                        continue

                await self._delay()

        return results
