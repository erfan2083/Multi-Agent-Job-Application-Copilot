from connectors.remoteok import RemoteOKConnector
from connectors.weworkremotely import WeWorkRemotelyConnector
from schemas.job import JobRaw


def discover_jobs(preferences: dict) -> list[JobRaw]:
    jobs: list[JobRaw] = []
    for connector in [RemoteOKConnector(), WeWorkRemotelyConnector()]:
        try:
            jobs.extend(connector.search(preferences))
        except Exception:
            continue
    return jobs
