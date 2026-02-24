import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM provider: "claude" (browser session) or "openai" / "chatgpt" (API)
    llm_provider: str = "claude"

    # Claude session
    claude_email: str = ""
    claude_password: str = ""

    # OpenAI / ChatGPT
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Database
    database_url: str = "sqlite:///./job_hunter.db"

    # Scraping
    min_match_score: int = 60
    max_jobs_per_site: int = 20
    request_delay_seconds: float = 2.0

    # LLM rate limiting (requests per minute; OpenRouter free tier = 8)
    llm_rate_limit_rpm: int = 8
    llm_score_batch_size: int = 5

    # Paths
    upload_dir: str = "uploads"
    session_dir: str = "playwright-session"
    screenshot_dir: str = "screenshots"

    # Phase 3: Job site credentials for auto-apply
    jobinja_email: str = ""
    jobinja_password: str = ""
    irantalent_email: str = ""
    irantalent_password: str = ""
    wellfound_email: str = ""
    wellfound_password: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Ensure directories exist
Path(settings.upload_dir).mkdir(exist_ok=True)
Path(settings.session_dir).mkdir(exist_ok=True)
Path(settings.screenshot_dir).mkdir(exist_ok=True)
