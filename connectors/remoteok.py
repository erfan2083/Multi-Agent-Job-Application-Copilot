from __future__ import annotations

import requests
from connectors.base import BaseConnector, now_utc
from schemas.job import JobRaw


class RemoteOKConnector(BaseConnector):
    source = "remoteok"
    endpoint = "https://remoteok.com/api"

    def search(self, preferences: dict) -> list[JobRaw]:
        resp = requests.get(self.endpoint, timeout=20, headers={"User-Agent": "MJAC/0.1"})
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for item in data[1:31]:
            jobs.append(
                JobRaw(
                    source=self.source,
                    source_job_id=str(item.get("id") or item.get("slug")),
                    url=item.get("url", ""),
                    raw_json=item,
                    fetched_at=now_utc(),
                )
            )
        return jobs
