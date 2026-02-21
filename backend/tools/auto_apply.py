"""Phase 3 — Optional auto-apply via Playwright browser automation.

Supports per-site application logic for sites with straightforward forms.
User confirmation is always required before submission.

Supported sites:
    - jobinja.ir       (form-based apply)
    - irantalent.com   (resume upload button)
    - wellfound.com    (1-click apply)

Not supported (heavy bot detection / captchas):
    - linkedin.com
    - indeed.com
    - glassdoor.com
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from backend.config import settings
from backend.database import Application, JobListing, ResumeProfile, SessionLocal

logger = logging.getLogger(__name__)

# Sites that support automated application
SUPPORTED_SITES = {"jobinja", "irantalent", "wellfound"}


class AutoApplyResult:
    """Outcome of an auto-apply attempt."""

    def __init__(
        self,
        success: bool,
        method: str = "auto",
        screenshot_path: str = "",
        notes: str = "",
    ):
        self.success = success
        self.method = method
        self.screenshot_path = screenshot_path
        self.notes = notes


class AutoApplyEngine:
    """Manages Playwright sessions for per-site auto-apply."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._contexts: dict[str, BrowserContext] = {}
        self._screenshot_dir = Path(settings.screenshot_dir)
        self._screenshot_dir.mkdir(exist_ok=True)

    async def start(self) -> None:
        """Launch the browser if not already running."""
        if self._browser:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        logger.info("AutoApplyEngine browser started")

    async def close(self) -> None:
        for ctx in self._contexts.values():
            try:
                await ctx.close()
            except Exception:
                pass
        self._contexts.clear()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None

    async def _get_context(self, site: str) -> BrowserContext:
        """Return (or create) a browser context for the given site."""
        if site not in self._contexts:
            state_path = Path(settings.session_dir) / f"apply_{site}.json"
            if state_path.exists():
                ctx = await self._browser.new_context(
                    storage_state=str(state_path)
                )
            else:
                ctx = await self._browser.new_context()
            self._contexts[site] = ctx
        return self._contexts[site]

    async def _save_context(self, site: str) -> None:
        ctx = self._contexts.get(site)
        if ctx:
            state_path = Path(settings.session_dir) / f"apply_{site}.json"
            try:
                await ctx.storage_state(path=str(state_path))
            except Exception:
                pass

    async def _screenshot(self, page: Page, job_id: int, site: str) -> str:
        """Take a proof screenshot and return the path."""
        path = self._screenshot_dir / f"apply_{site}_{job_id}.png"
        try:
            await page.screenshot(path=str(path), full_page=False)
            return str(path)
        except Exception as exc:
            logger.warning(f"Screenshot failed: {exc}")
            return ""

    # ── Site-specific apply methods ──────────────────────────────────

    async def apply(
        self,
        job_id: int,
        resume_id: int,
    ) -> AutoApplyResult:
        """Apply to a job — dispatches to the correct site handler.

        Returns an AutoApplyResult. Saves the Application record to DB.
        """
        db = SessionLocal()
        try:
            job = db.query(JobListing).filter_by(id=job_id).first()
            if not job:
                return AutoApplyResult(False, notes="Job not found")

            resume = db.query(ResumeProfile).filter_by(id=resume_id).first()
            if not resume:
                return AutoApplyResult(False, notes="Resume not found")

            site = job.source_site
            if site not in SUPPORTED_SITES:
                return AutoApplyResult(
                    False, notes=f"Auto-apply not supported for {site}"
                )

            # Check for existing application
            existing = (
                db.query(Application)
                .filter_by(job_id=job_id)
                .filter(Application.status.in_(["submitted", "pending"]))
                .first()
            )
            if existing:
                return AutoApplyResult(
                    False, notes="Already applied to this job"
                )

            await self.start()

            # Dispatch to site handler
            handler = {
                "jobinja": self._apply_jobinja,
                "irantalent": self._apply_irantalent,
                "wellfound": self._apply_wellfound,
            }.get(site)

            if not handler:
                return AutoApplyResult(
                    False, notes=f"No handler for {site}"
                )

            result = await handler(job, resume)

            # Persist the application record
            app = Application(
                job_id=job_id,
                applied_at=datetime.now(timezone.utc) if result.success else None,
                method=result.method,
                status="submitted" if result.success else "failed",
                notes=result.notes,
            )
            db.add(app)

            # Update job status
            if result.success:
                job.status = "applied"
            db.commit()
            db.refresh(app)

            result.notes = (
                f"Application #{app.id}: {result.notes}"
                if result.notes
                else f"Application #{app.id}"
            )
            return result

        except Exception as exc:
            logger.error(f"Auto-apply error: {exc}", exc_info=True)
            return AutoApplyResult(False, notes=str(exc))
        finally:
            db.close()

    # ── Jobinja ──────────────────────────────────────────────────────

    async def _apply_jobinja(
        self, job: JobListing, resume: ResumeProfile
    ) -> AutoApplyResult:
        """Apply on Jobinja.ir — click the apply button, fill the form."""
        ctx = await self._get_context("jobinja")
        page = await ctx.new_page()

        try:
            # Log in if needed
            if not await self._jobinja_ensure_logged_in(page):
                return AutoApplyResult(
                    False,
                    notes="Could not log in to Jobinja. Set JOBINJA_EMAIL and JOBINJA_PASSWORD.",
                )

            await page.goto(job.url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # Look for apply button
            apply_btn = page.locator(
                'button:has-text("ارسال رزومه"), '
                'a:has-text("ارسال رزومه"), '
                'button:has-text("Apply"), '
                '[class*="apply"]'
            )
            if await apply_btn.count() == 0:
                ss = await self._screenshot(page, job.id, "jobinja")
                return AutoApplyResult(
                    False,
                    screenshot_path=ss,
                    notes="Apply button not found on job page",
                )

            await apply_btn.first.click()
            await asyncio.sleep(3)

            # Take screenshot as proof
            ss = await self._screenshot(page, job.id, "jobinja")
            await self._save_context("jobinja")

            return AutoApplyResult(
                True,
                method="auto",
                screenshot_path=ss,
                notes="Application submitted on Jobinja",
            )
        except Exception as exc:
            ss = await self._screenshot(page, job.id, "jobinja")
            return AutoApplyResult(False, screenshot_path=ss, notes=str(exc))
        finally:
            await page.close()

    async def _jobinja_ensure_logged_in(self, page: Page) -> bool:
        """Check if logged into Jobinja; if not, attempt login."""
        email = settings.jobinja_email
        password = settings.jobinja_password
        if not email or not password:
            return False

        await page.goto(
            "https://jobinja.ir/user/dashboard",
            wait_until="networkidle",
            timeout=30000,
        )
        await asyncio.sleep(1)

        if "/login" not in page.url and "/register" not in page.url:
            return True  # Already logged in

        # Navigate to login
        await page.goto(
            "https://jobinja.ir/login",
            wait_until="networkidle",
            timeout=30000,
        )
        await asyncio.sleep(1)

        try:
            email_input = page.locator('input[name="email"], input[type="email"]')
            if await email_input.count() > 0:
                await email_input.first.fill(email)

            password_input = page.locator(
                'input[name="password"], input[type="password"]'
            )
            if await password_input.count() > 0:
                await password_input.first.fill(password)

            submit = page.locator(
                'button[type="submit"], input[type="submit"]'
            )
            if await submit.count() > 0:
                await submit.first.click()
                await asyncio.sleep(3)

            # Check if login succeeded
            if "/login" not in page.url:
                await self._save_context("jobinja")
                return True
        except Exception as exc:
            logger.warning(f"Jobinja login failed: {exc}")

        return False

    # ── IranTalent ───────────────────────────────────────────────────

    async def _apply_irantalent(
        self, job: JobListing, resume: ResumeProfile
    ) -> AutoApplyResult:
        """Apply on IranTalent.com — click apply, upload resume if needed."""
        ctx = await self._get_context("irantalent")
        page = await ctx.new_page()

        try:
            if not await self._irantalent_ensure_logged_in(page):
                return AutoApplyResult(
                    False,
                    notes="Could not log in to IranTalent. Set IRANTALENT_EMAIL and IRANTALENT_PASSWORD.",
                )

            await page.goto(job.url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            apply_btn = page.locator(
                'button:has-text("Apply"), '
                'a:has-text("Apply"), '
                'button:has-text("ارسال"), '
                '[class*="apply"]'
            )
            if await apply_btn.count() == 0:
                ss = await self._screenshot(page, job.id, "irantalent")
                return AutoApplyResult(
                    False,
                    screenshot_path=ss,
                    notes="Apply button not found on IranTalent job page",
                )

            await apply_btn.first.click()
            await asyncio.sleep(3)

            ss = await self._screenshot(page, job.id, "irantalent")
            await self._save_context("irantalent")

            return AutoApplyResult(
                True,
                method="auto",
                screenshot_path=ss,
                notes="Application submitted on IranTalent",
            )
        except Exception as exc:
            ss = await self._screenshot(page, job.id, "irantalent")
            return AutoApplyResult(False, screenshot_path=ss, notes=str(exc))
        finally:
            await page.close()

    async def _irantalent_ensure_logged_in(self, page: Page) -> bool:
        email = settings.irantalent_email
        password = settings.irantalent_password
        if not email or not password:
            return False

        await page.goto(
            "https://www.irantalent.com/en/dashboard",
            wait_until="networkidle",
            timeout=30000,
        )
        await asyncio.sleep(1)

        if "/login" not in page.url and "/sign-in" not in page.url:
            return True

        await page.goto(
            "https://www.irantalent.com/en/login",
            wait_until="networkidle",
            timeout=30000,
        )
        await asyncio.sleep(1)

        try:
            email_input = page.locator('input[name="email"], input[type="email"]')
            if await email_input.count() > 0:
                await email_input.first.fill(email)

            password_input = page.locator(
                'input[name="password"], input[type="password"]'
            )
            if await password_input.count() > 0:
                await password_input.first.fill(password)

            submit = page.locator(
                'button[type="submit"], input[type="submit"]'
            )
            if await submit.count() > 0:
                await submit.first.click()
                await asyncio.sleep(3)

            if "/login" not in page.url and "/sign-in" not in page.url:
                await self._save_context("irantalent")
                return True
        except Exception as exc:
            logger.warning(f"IranTalent login failed: {exc}")

        return False

    # ── Wellfound ────────────────────────────────────────────────────

    async def _apply_wellfound(
        self, job: JobListing, resume: ResumeProfile
    ) -> AutoApplyResult:
        """Apply on Wellfound — 1-click apply for startup jobs."""
        ctx = await self._get_context("wellfound")
        page = await ctx.new_page()

        try:
            if not await self._wellfound_ensure_logged_in(page):
                return AutoApplyResult(
                    False,
                    notes="Could not log in to Wellfound. Set WELLFOUND_EMAIL and WELLFOUND_PASSWORD.",
                )

            await page.goto(job.url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            apply_btn = page.locator(
                'button:has-text("Apply"), '
                'a:has-text("Apply"), '
                '[data-test="apply-button"], '
                '[class*="apply"]'
            )
            if await apply_btn.count() == 0:
                ss = await self._screenshot(page, job.id, "wellfound")
                return AutoApplyResult(
                    False,
                    screenshot_path=ss,
                    notes="Apply button not found on Wellfound job page",
                )

            await apply_btn.first.click()
            await asyncio.sleep(3)

            ss = await self._screenshot(page, job.id, "wellfound")
            await self._save_context("wellfound")

            return AutoApplyResult(
                True,
                method="auto",
                screenshot_path=ss,
                notes="Application submitted on Wellfound",
            )
        except Exception as exc:
            ss = await self._screenshot(page, job.id, "wellfound")
            return AutoApplyResult(False, screenshot_path=ss, notes=str(exc))
        finally:
            await page.close()

    async def _wellfound_ensure_logged_in(self, page: Page) -> bool:
        email = settings.wellfound_email
        password = settings.wellfound_password
        if not email or not password:
            return False

        await page.goto(
            "https://wellfound.com/dashboard",
            wait_until="networkidle",
            timeout=30000,
        )
        await asyncio.sleep(1)

        if "/login" not in page.url:
            return True

        await page.goto(
            "https://wellfound.com/login",
            wait_until="networkidle",
            timeout=30000,
        )
        await asyncio.sleep(1)

        try:
            email_input = page.locator('input[name="email"], input[type="email"]')
            if await email_input.count() > 0:
                await email_input.first.fill(email)

            password_input = page.locator(
                'input[name="password"], input[type="password"]'
            )
            if await password_input.count() > 0:
                await password_input.first.fill(password)

            submit = page.locator(
                'button[type="submit"], input[type="submit"]'
            )
            if await submit.count() > 0:
                await submit.first.click()
                await asyncio.sleep(3)

            if "/login" not in page.url:
                await self._save_context("wellfound")
                return True
        except Exception as exc:
            logger.warning(f"Wellfound login failed: {exc}")

        return False


def is_auto_apply_supported(source_site: str) -> bool:
    """Check if auto-apply is supported for the given job site."""
    return source_site in SUPPORTED_SITES


def get_supported_sites() -> list[str]:
    """Return list of sites that support auto-apply."""
    return sorted(SUPPORTED_SITES)
