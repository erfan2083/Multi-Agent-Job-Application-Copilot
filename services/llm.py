from __future__ import annotations

import json
from core.config import settings


class LLMService:
    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        if not settings.openai_api_key:
            if json_schema:
                return {"status": "LLM not configured", "prompt_preview": prompt[:200]}
            return "LLM not configured"
        # Provider-agnostic stub for MVP.
        if json_schema:
            return {"status": "configured", "note": "Implement provider call here"}
        return "configured"


llm_service = LLMService()
