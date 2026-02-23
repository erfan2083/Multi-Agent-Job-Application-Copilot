"""LLM provider abstraction — supports Claude (browser session) and OpenAI (API).

Users can choose which LLM backend to use via the LLM_PROVIDER environment
variable or at runtime through the API.  Every place that previously called
``ClaudeSession`` directly now goes through the unified ``LLMProvider``
interface.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)


# ── Abstract base ────────────────────────────────────────────────────

class BaseLLMProvider(ABC):
    """Common interface every LLM backend must implement."""

    @property
    @abstractmethod
    def is_ready(self) -> bool: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def ask(self, prompt: str, timeout: int = 120) -> str: ...

    async def ask_for_json(self, prompt: str, timeout: int = 120) -> dict:
        """Send a prompt and parse the response as JSON."""
        response = await self.ask(prompt, timeout=timeout)
        if not response:
            return {}

        # Try markdown code block first
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = response.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Last resort: find the first { ... } block
            brace_match = re.search(r"\{[\s\S]*\}", response)
            if brace_match:
                try:
                    return json.loads(brace_match.group(0))
                except json.JSONDecodeError:
                    pass
            logger.error(
                f"Could not parse JSON from LLM response: {response[:200]}"
            )
            return {}


# ── Claude (browser session) provider ────────────────────────────────

class ClaudeBrowserProvider(BaseLLMProvider):
    """Wraps the existing ClaudeSession for backward compatibility."""

    def __init__(self) -> None:
        self._session: Optional[object] = None
        self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    async def start(self) -> None:
        from backend.claude_session import ClaudeSession

        session = ClaudeSession()
        await session.start()

        if not session.is_ready:
            success = await session.login()
            if not success:
                logger.warning("Claude browser login failed")
                self._ready = False
                self._session = session
                return

        self._session = session
        self._ready = True

    async def close(self) -> None:
        if self._session:
            await self._session.close()
        self._ready = False

    async def ask(self, prompt: str, timeout: int = 120) -> str:
        if not self._session or not self._ready:
            raise RuntimeError("Claude browser session is not ready")
        return await self._session.ask(prompt, timeout=timeout)

    async def ask_for_json(self, prompt: str, timeout: int = 120) -> dict:
        if not self._session or not self._ready:
            return {}
        return await self._session.ask_for_json(prompt, timeout=timeout)


# ── OpenAI / ChatGPT provider ───────────────────────────────────────

class OpenAIProvider(BaseLLMProvider):
    """Uses the OpenAI Python SDK (``openai`` package)."""

    def __init__(self) -> None:
        self._client = None
        self._ready = False
        self._model = settings.openai_model

    @property
    def is_ready(self) -> bool:
        return self._ready

    async def start(self) -> None:
        api_key = settings.openai_api_key
        if not api_key:
            logger.warning("No OPENAI_API_KEY set — OpenAI provider disabled")
            self._ready = False
            return

        try:
            from openai import OpenAI

            self._client = OpenAI(
                                base_url="https://openrouter.ai/api/v1",
                                api_key=api_key,
                            )
            self._ready = True
            logger.info(f"OpenAI provider ready (model={self._model})")
        except ImportError:
            logger.error(
                "openai package not installed. Run: pip install openai"
            )
            self._ready = False
        except Exception as exc:
            logger.error(f"OpenAI init failed: {exc}")
            self._ready = False

    async def close(self) -> None:
        if self._client:
            await self._client.close()
        self._client = None
        self._ready = False

    async def ask(self, prompt: str, timeout: int = 120) -> str:
        if not self._client or not self._ready:
            raise RuntimeError("OpenAI provider is not ready")

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4096,
                timeout=timeout,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error(f"OpenAI request failed: {exc}")
            raise


# ── Factory ──────────────────────────────────────────────────────────

_PROVIDERS: dict[str, type[BaseLLMProvider]] = {
    "claude": ClaudeBrowserProvider,
    "openai": OpenAIProvider,
    "chatgpt": OpenAIProvider,  # alias
}


def get_provider_class(name: str) -> type[BaseLLMProvider]:
    """Return the provider class for the given name."""
    cls = _PROVIDERS.get(name.lower())
    if cls is None:
        raise ValueError(
            f"Unknown LLM provider '{name}'. "
            f"Choose from: {', '.join(_PROVIDERS)}"
        )
    return cls


async def create_provider(name: str | None = None) -> BaseLLMProvider:
    """Instantiate, start, and return a provider.

    Falls back to ``settings.llm_provider`` when *name* is ``None``.
    """
    name = name or settings.llm_provider
    cls = get_provider_class(name)
    provider = cls()
    await provider.start()
    return provider
