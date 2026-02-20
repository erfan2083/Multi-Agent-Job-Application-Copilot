from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MJAC"
    env: str = "dev"
    database_url: str = "sqlite:///./mjajc.db"
    data_dir: Path = Path("data")
    openai_api_key: str | None = None
    app_login_username: str = "admin"
    app_login_password_hash: str = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"  # sha256("admin")
    session_ttl_hours: int = 12
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_sender: str = "noreply@example.com"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
