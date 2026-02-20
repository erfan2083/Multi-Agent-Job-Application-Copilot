"""Claude session handler — communicates with claude.ai via Playwright browser session.

This module manages a persistent browser session logged into claude.ai,
allowing us to send prompts and receive responses without an API key.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from backend.config import settings

logger = logging.getLogger(__name__)


class ClaudeSession:
    """Manages a Playwright browser session logged into claude.ai."""

    CLAUDE_URL = "https://claude.ai"
    CHAT_URL = "https://claude.ai/new"

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._logged_in = False
        self._session_dir = Path(settings.session_dir)
        self._session_dir.mkdir(exist_ok=True)

    @property
    def is_ready(self) -> bool:
        return self._logged_in and self._page is not None

    async def start(self) -> None:
        """Launch browser and restore session if available."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        storage_path = self._session_dir / "state.json"

        if storage_path.exists():
            self._context = await self._browser.new_context(
                storage_state=str(storage_path)
            )
            logger.info("Restored saved browser session")
        else:
            self._context = await self._browser.new_context()
            logger.info("Created fresh browser context")

        self._page = await self._context.new_page()

        # Check if the saved session is still valid
        try:
            await self._page.goto(self.CLAUDE_URL, wait_until="networkidle", timeout=30000)
            # If we land on a page with the chat interface, we're logged in
            if "claude.ai" in self._page.url and "/login" not in self._page.url:
                self._logged_in = True
                logger.info("Session is valid, already logged in")
            else:
                logger.info("Session expired, need to log in")
        except Exception as e:
            logger.warning(f"Could not verify session: {e}")

    async def login(self, email: str | None = None, password: str | None = None) -> bool:
        """Log in to claude.ai via the OAuth flow.

        Uses credentials from parameters or settings.
        """
        email = email or settings.claude_email
        password = password or settings.claude_password

        if not email or not password:
            logger.error("No Claude credentials provided")
            return False

        if self._page is None:
            await self.start()

        try:
            await self._page.goto(
                f"{self.CLAUDE_URL}/login", wait_until="networkidle", timeout=30000
            )

            # Click "Continue with email" or similar
            email_button = self._page.locator(
                'button:has-text("email"), button:has-text("Email")'
            )
            if await email_button.count() > 0:
                await email_button.first.click()
                await asyncio.sleep(1)

            # Fill email
            email_input = self._page.locator('input[type="email"], input[name="email"]')
            if await email_input.count() > 0:
                await email_input.first.fill(email)
                await self._page.locator(
                    'button[type="submit"], button:has-text("Continue")'
                ).first.click()
                await asyncio.sleep(2)

            # Fill password
            password_input = self._page.locator(
                'input[type="password"], input[name="password"]'
            )
            if await password_input.count() > 0:
                await password_input.first.fill(password)
                await self._page.locator(
                    'button[type="submit"], button:has-text("Log in"), button:has-text("Sign in")'
                ).first.click()
                await asyncio.sleep(3)

            # Wait for redirect to main page
            await self._page.wait_for_url(
                f"{self.CLAUDE_URL}/**", timeout=15000
            )

            # Save session
            storage_path = self._session_dir / "state.json"
            await self._context.storage_state(path=str(storage_path))

            self._logged_in = True
            logger.info("Successfully logged in to claude.ai")
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    async def ask(self, prompt: str, timeout: int = 120) -> str:
        """Send a prompt to Claude and return the response text.

        Opens a new conversation each time to keep things clean.
        """
        if not self.is_ready:
            raise RuntimeError(
                "Claude session not ready. Call start() and login() first."
            )

        try:
            # Navigate to a new chat
            await self._page.goto(self.CHAT_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # Find the message input area
            input_selector = (
                '[contenteditable="true"], '
                'textarea[placeholder], '
                'div[data-placeholder]'
            )
            input_el = self._page.locator(input_selector).first
            await input_el.click()
            await asyncio.sleep(0.5)

            # Type the prompt (use fill for textareas, or keyboard for contenteditable)
            tag = await input_el.evaluate("el => el.tagName.toLowerCase()")
            if tag == "textarea":
                await input_el.fill(prompt)
            else:
                await self._page.keyboard.type(prompt, delay=5)

            await asyncio.sleep(0.5)

            # Submit
            await self._page.keyboard.press("Enter")

            # Wait for the response to appear and complete
            # Claude's response typically appears in a div with specific classes
            await asyncio.sleep(3)  # Initial wait for response to start

            # Poll until the response stops changing (Claude finished typing)
            response_text = ""
            stable_count = 0
            for _ in range(timeout * 2):  # Check every 0.5s
                await asyncio.sleep(0.5)

                # Try to get the latest assistant message
                messages = self._page.locator(
                    '[data-testid*="message"], '
                    '.font-claude-message, '
                    '[class*="assistant"], '
                    '[class*="response"]'
                )
                count = await messages.count()
                if count > 0:
                    latest = await messages.nth(count - 1).inner_text()
                    if latest == response_text and latest.strip():
                        stable_count += 1
                        if stable_count >= 4:  # Stable for 2 seconds
                            break
                    else:
                        response_text = latest
                        stable_count = 0

            if not response_text.strip():
                logger.warning("Got empty response from Claude")
                return ""

            return response_text.strip()

        except Exception as e:
            logger.error(f"Error asking Claude: {e}")
            raise

    async def ask_for_json(self, prompt: str, timeout: int = 120) -> dict:
        """Send a prompt and parse the response as JSON."""
        response = await self.ask(prompt, timeout=timeout)

        # Try to extract JSON from the response
        # Claude sometimes wraps JSON in markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # Try the whole response as JSON
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
            logger.error(f"Could not parse JSON from Claude response: {response[:200]}")
            return {}

    async def close(self) -> None:
        """Close the browser session."""
        if self._context:
            storage_path = self._session_dir / "state.json"
            try:
                await self._context.storage_state(path=str(storage_path))
            except Exception:
                pass
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._logged_in = False
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None


# ── Fallback scoring (rule-based) when Claude session is unavailable ─

def fallback_parse_resume(raw_text: str) -> dict:
    """Basic rule-based resume parsing as a fallback."""
    lines = raw_text.strip().split("\n")
    skills = []
    titles = []

    # Common tech keywords to detect
    tech_keywords = [
        "python", "javascript", "typescript", "react", "node", "java",
        "c++", "c#", "go", "rust", "sql", "html", "css", "docker",
        "kubernetes", "aws", "azure", "gcp", "git", "linux", "django",
        "flask", "fastapi", "spring", "angular", "vue", "mongodb",
        "postgresql", "mysql", "redis", "graphql", "rest", "api",
    ]

    title_keywords = [
        "developer", "engineer", "architect", "manager", "lead",
        "designer", "analyst", "consultant", "intern", "senior",
        "junior", "mid", "full stack", "frontend", "backend",
        "devops", "data", "ml", "ai", "machine learning",
    ]

    text_lower = raw_text.lower()

    for kw in tech_keywords:
        if kw in text_lower:
            skills.append(kw.capitalize() if len(kw) > 3 else kw.upper())

    for line in lines:
        line_lower = line.strip().lower()
        for tk in title_keywords:
            if tk in line_lower and len(line.strip()) < 60:
                titles.append(line.strip())
                break

    return {
        "full_name": lines[0].strip() if lines else "",
        "email": "",
        "phone": "",
        "skills": skills[:20],
        "technical_skills": skills[:20],
        "soft_skills": [],
        "job_titles": titles[:5],
        "total_experience_years": 0,
        "education": {},
        "languages": [],
        "summary": " ".join(lines[:3]) if lines else "",
    }


def fallback_score_job(profile: dict, job: dict) -> dict:
    """Basic rule-based job scoring as a fallback."""
    score = 0
    pros = []
    cons = []

    profile_skills = {s.lower() for s in profile.get("skills", [])}
    profile_titles = {t.lower() for t in profile.get("job_titles", [])}

    job_desc = (job.get("description", "") + " " + job.get("title", "")).lower()

    # Skill matching
    matched_skills = 0
    for skill in profile_skills:
        if skill in job_desc:
            matched_skills += 1

    if profile_skills:
        skill_ratio = matched_skills / len(profile_skills)
        score += int(skill_ratio * 50)
        if skill_ratio > 0.5:
            pros.append(f"{matched_skills} skills match")
        else:
            cons.append(f"Only {matched_skills}/{len(profile_skills)} skills match")

    # Title matching
    for title in profile_titles:
        words = title.lower().split()
        if any(w in job_desc for w in words if len(w) > 3):
            score += 20
            pros.append("Job title aligns with experience")
            break

    # Base score for having a description
    if job.get("description"):
        score += 10

    # Remote bonus if in preferences
    if job.get("is_remote"):
        score += 10
        pros.append("Remote position")

    score = min(score, 100)

    if not cons:
        cons.append("Manual review recommended")

    return {
        "score": score,
        "reason": f"Match based on {matched_skills} skill overlaps",
        "pros": pros,
        "cons": cons,
    }
