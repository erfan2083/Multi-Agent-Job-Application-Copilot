"""LLM provider abstraction — supports Claude (browser session) and OpenAI (API).

Users can choose which LLM backend to use via the LLM_PROVIDER environment
variable or at runtime through the API.  Every place that previously called
``ClaudeSession`` directly now goes through the unified ``LLMProvider``
interface.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)


# ── Rate limiter ────────────────────────────────────────────────────

class AsyncRateLimiter:
    """Sliding-window rate limiter for async code."""

    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self._max = max_requests
        self._window = window_seconds
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request slot is available within the rate window."""
        async with self._lock:
            now = time.monotonic()
            # Drop timestamps outside the sliding window
            self._timestamps = [
                t for t in self._timestamps if now - t < self._window
            ]

            if len(self._timestamps) >= self._max:
                # Wait for the oldest request to fall outside the window
                wait = self._window - (now - self._timestamps[0]) + 0.5
                if wait > 0:
                    logger.info(
                        f"Rate limit: waiting {wait:.1f}s before next LLM request"
                    )
                    await asyncio.sleep(wait)
                    # Refresh after sleeping
                    now = time.monotonic()
                    self._timestamps = [
                        t for t in self._timestamps if now - t < self._window
                    ]

            self._timestamps.append(time.monotonic())


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
        try:
            from backend.claude_session import ClaudeSession
        except ImportError:
            logger.warning("claude_session module not available")
            self._ready = False
            return

        try:
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
        except NotImplementedError:
            # Windows + uvicorn --reload: asyncio subprocess_exec is not
            # supported on the default ProactorEventLoop inside the reloader.
            logger.warning(
                "Playwright subprocess not supported in this environment "
                "(common on Windows with uvicorn --reload). "
                "Use the OpenAI/OpenRouter provider instead."
            )
            self._ready = False
        except Exception as exc:
            logger.warning(f"Claude session start failed: {exc}")
            self._ready = False

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
    """Uses the OpenAI Python SDK with rate limiting and retry logic.

    Handles OpenRouter free-tier rate limits (default 8 RPM) by:
    1. Pre-request rate limiting via a sliding-window limiter.
    2. Retrying 429 responses with exponential backoff (2s, 4s, 8s, …).
    """

    MAX_RETRIES = 5
    BASE_RETRY_DELAY = 2.0  # seconds

    def __init__(self) -> None:
        self._client = None
        self._ready = False
        self._model = settings.openai_model
        # Reserve one slot so we don't constantly hit the wall
        rpm = max(1, settings.llm_rate_limit_rpm - 1)
        self._rate_limiter = AsyncRateLimiter(
            max_requests=rpm, window_seconds=60.0
        )

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
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                max_retries=0,  # We handle retries ourselves
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

        last_exc: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            # Wait for a rate-limit slot
            await self._rate_limiter.acquire()

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
                last_exc = exc
                exc_str = str(exc)

                if "429" in exc_str:
                    delay = self.BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Rate limited (429), retry {attempt + 1}/"
                        f"{self.MAX_RETRIES} in {delay:.0f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    # Non-rate-limit error — don't retry
                    logger.error(f"OpenAI request failed: {exc}")
                    raise

        logger.error(
            f"OpenAI request failed after {self.MAX_RETRIES} retries: {last_exc}"
        )
        raise last_exc  # type: ignore[misc]


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
