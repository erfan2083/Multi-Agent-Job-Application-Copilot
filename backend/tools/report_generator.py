"""Report generator — creates summary reports of search results."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.claude_session import ClaudeSession

logger = logging.getLogger(__name__)

REPORT_PROMPT = """Summarize these job search results for the candidate. Write in a brief, helpful way.
Include: total jobs found, top matches, common skill gaps, and recommendations.
If the candidate seems to speak Persian, include a brief Persian summary too.

Profile: {profile_json}
Jobs found: {job_count}
Top jobs: {top_jobs}

Return a brief text summary (not JSON)."""


async def generate_report(
    claude: ClaudeSession | None,
    profile: dict,
    jobs: list[dict[str, Any]],
) -> str:
    """Generate a summary report of search results."""
    top_jobs = sorted(jobs, key=lambda j: j.get("match_score", 0), reverse=True)[:5]
    top_jobs_brief = [
        {
            "title": j.get("title"),
            "company": j.get("company"),
            "score": j.get("match_score"),
            "reason": j.get("match_reason", "")[:200],
        }
        for j in top_jobs
    ]

    if claude and claude.is_ready:
        try:
            prompt = REPORT_PROMPT.format(
                profile_json=json.dumps(profile, ensure_ascii=False),
                job_count=len(jobs),
                top_jobs=json.dumps(top_jobs_brief, ensure_ascii=False, indent=2),
            )
            return await claude.ask(prompt)
        except Exception as e:
            logger.warning(f"Claude report generation failed: {e}")

    # Fallback: simple text report
    return _fallback_report(profile, jobs, top_jobs_brief)


def _fallback_report(
    profile: dict,
    jobs: list[dict],
    top_jobs: list[dict],
) -> str:
    """Generate a simple text report without Claude."""
    total = len(jobs)
    high_match = sum(1 for j in jobs if j.get("match_score", 0) >= 80)
    mid_match = sum(1 for j in jobs if 60 <= j.get("match_score", 0) < 80)

    lines = [
        f"Search complete! Found {total} job listings.",
        f"  - {high_match} high match (80+)",
        f"  - {mid_match} good match (60-79)",
        "",
    ]

    if top_jobs:
        lines.append("Top matches:")
        for i, job in enumerate(top_jobs, 1):
            lines.append(
                f"  {i}. {job['title']} at {job['company']} "
                f"(Score: {job['score']})"
            )

    lines.extend([
        "",
        f"نتایج جستجو: {total} موقعیت شغلی پیدا شد.",
        f"  - {high_match} تطابق بالا",
        f"  - {mid_match} تطابق متوسط",
    ])

    return "\n".join(lines)
