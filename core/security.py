import os
from pathlib import Path


def ensure_data_dirs(base: Path) -> None:
    for folder in ["resumes", "docs", "reports", "screenshots", "emails"]:
        (base / folder).mkdir(parents=True, exist_ok=True)


def get_secret(name: str) -> str | None:
    return os.getenv(name)
