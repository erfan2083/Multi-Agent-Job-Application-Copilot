"""Base scraper class for job boards."""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import AsyncIterator

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

# Rotate user agents to reduce blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class JobResult:
    """Represents a single scraped job listing."""

    def __init__(
        self,
        title: str,
        company: str,
        location: str,
        url: str,
        source_site: str,
        description: str = "",
        is_remote: bool = False,
        salary_range: str = "",
    ):
        self.title = title
        self.company = company
        self.location = location
        self.url = url
        self.source_site = source_site
        self.description = description
        self.is_remote = is_remote
        self.salary_range = salary_range

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "source_site": self.source_site,
            "description": self.description,
            "is_remote": self.is_remote,
            "salary_range": self.salary_range,
        }


class BaseScraper(ABC):
    """Abstract base class for all job board scrapers."""

    site_name: str = "unknown"
    base_url: str = ""

    def __init__(self) -> None:
        self.delay = settings.request_delay_seconds
        self.max_jobs = settings.max_jobs_per_site

    def _get_headers(self) -> dict:
        ua = random.choice(USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
            # NOTE: Do NOT set Accept-Encoding manually — let httpx handle it
            # so it automatically decompresses gzip/br responses.
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "DNT": "1",
            "Cache-Control": "max-age=0",
        }

    async def _delay(self) -> None:
        """Random delay between requests."""
        delay = self.delay + random.uniform(0.5, 1.5)
        await asyncio.sleep(delay)

    async def _fetch(self, url: str, client: httpx.AsyncClient) -> str | None:
        """Fetch a URL with error handling."""
        try:
            resp = await client.get(url, headers=self._get_headers(), timeout=20.0)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPStatusError as e:
            logger.warning(f"[{self.site_name}] HTTP {e.response.status_code} for {url}")
            return None
        except Exception as e:
            logger.warning(f"[{self.site_name}] Request failed for {url}: {e}")
            return None

    @abstractmethod
    async def search(self, keywords: list[str], location: str = "") -> list[JobResult]:
        """Search for jobs and return results."""
        ...

    async def search_safe(self, keywords: list[str], location: str = "") -> list[JobResult]:
        """Search with error handling — never raises."""
        try:
            results = await self.search(keywords, location)
            logger.info(f"[{self.site_name}] Found {len(results)} jobs")
            return results
        except Exception as e:
            logger.error(f"[{self.site_name}] Scraper failed: {e}")
            return []
