from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from core.config import settings
from core.utils.hashing import sha256_text


class AuthService:
    """Simple local auth/session service for gating LLM usage in MVP."""

    def __init__(self) -> None:
        self._sessions: dict[str, datetime] = {}

    def login(self, username: str, password: str) -> str | None:
        if username != settings.app_login_username:
            return None
        if sha256_text(password) != settings.app_login_password_hash:
            return None
        token = secrets.token_urlsafe(32)
        self._sessions[token] = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
        return token

    def verify_token(self, token: str) -> bool:
        expires_at = self._sessions.get(token)
        if not expires_at:
            return False
        if expires_at < datetime.now(timezone.utc):
            self._sessions.pop(token, None)
            return False
        return True


auth_service = AuthService()
