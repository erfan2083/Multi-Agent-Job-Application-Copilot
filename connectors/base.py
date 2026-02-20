from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from schemas.job import JobRaw


class BaseConnector(ABC):
    source: str

    @abstractmethod
    def search(self, preferences: dict) -> list[JobRaw]:
        raise NotImplementedError


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
