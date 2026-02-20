import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Claude session
    claude_email: str = ""
    claude_password: str = ""

    # Database
    database_url: str = "sqlite:///./job_hunter.db"

    # Scraping
    min_match_score: int = 60
    max_jobs_per_site: int = 20
    request_delay_seconds: float = 2.0

    # Paths
    upload_dir: str = "uploads"
    session_dir: str = "playwright-session"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Ensure directories exist
Path(settings.upload_dir).mkdir(exist_ok=True)
Path(settings.session_dir).mkdir(exist_ok=True)
