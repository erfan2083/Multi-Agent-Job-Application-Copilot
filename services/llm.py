from __future__ import annotations

from core.config import settings
from services.auth import auth_service


class LLMService:
    def generate(self, prompt: str, user_token: str, json_schema: dict | None = None) -> str | dict:
        if not auth_service.verify_token(user_token):
            return {"error": "Unauthorized. Login required before using LLM."}

        if not settings.openai_api_key:
            if json_schema:
                return {"status": "LLM not configured", "prompt_preview": prompt[:200]}
            return "LLM not configured"

        # Provider-agnostic stub for MVP.
        if json_schema:
            return {"status": "configured", "note": "Implement provider call here"}
        return "configured"


llm_service = LLMService()
