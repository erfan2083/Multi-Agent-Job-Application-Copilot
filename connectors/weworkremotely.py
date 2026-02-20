from __future__ import annotations

import feedparser
from connectors.base import BaseConnector, now_utc
from schemas.job import JobRaw


class WeWorkRemotelyConnector(BaseConnector):
    source = "weworkremotely"
    feed_url = "https://weworkremotely.com/remote-jobs.rss"

    def search(self, preferences: dict) -> list[JobRaw]:
        feed = feedparser.parse(self.feed_url)
        jobs = []
        for entry in feed.entries[:30]:
            jobs.append(
                JobRaw(
                    source=self.source,
                    source_job_id=entry.get("id", entry.get("link", "")),
                    url=entry.get("link", ""),
                    raw_json={"title": entry.get("title", ""), "summary": entry.get("summary", "")},
                    fetched_at=now_utc(),
                )
            )
        return jobs
