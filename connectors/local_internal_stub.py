from schemas.job import JobRaw
from connectors.base import now_utc


def sample_jobs() -> list[JobRaw]:
    return [
        JobRaw(source="local", source_job_id="1", url="https://example.com", raw_json={"title": "Python Engineer"}, fetched_at=now_utc())
    ]
