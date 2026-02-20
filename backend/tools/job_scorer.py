"""Job match scorer — scores jobs against a candidate profile using Claude or fallback."""

from __future__ import annotations

import logging

from backend.claude_session import ClaudeSession, fallback_score_job
from backend.models import JobScoreResult

logger = logging.getLogger(__name__)

SCORE_PROMPT_TEMPLATE = """You are a job match evaluator. Score how well this candidate matches this job (0-100).

Candidate Profile:
{profile_json}

Job Details:
Title: {job_title}
Company: {company}
Description: {job_description}

Return ONLY valid JSON, no extra text:
{{
  "score": 75,
  "reason": "Strong Python skills match. Missing Kubernetes experience mentioned in job.",
  "pros": ["skill match", "experience level"],
  "cons": ["missing DevOps skills"]
}}"""


async def score_job(
    claude: ClaudeSession | None,
    profile: dict,
    job: dict,
) -> JobScoreResult:
    """Score a job listing against a candidate profile.

    Uses Claude if available, falls back to rule-based scoring.
    """
    import json

    if claude and claude.is_ready:
        try:
            prompt = SCORE_PROMPT_TEMPLATE.format(
                profile_json=json.dumps(profile, ensure_ascii=False, indent=2),
                job_title=job.get("title", ""),
                company=job.get("company", ""),
                job_description=job.get("description", "")[:3000],
            )

            result = await claude.ask_for_json(prompt)
            return JobScoreResult(
                score=int(result.get("score", 0)),
                reason=result.get("reason", ""),
                pros=result.get("pros", []),
                cons=result.get("cons", []),
            )
        except Exception as e:
            logger.warning(f"Claude scoring failed, using fallback: {e}")

    # Fallback to rule-based scoring
    result = fallback_score_job(profile, job)
    return JobScoreResult(**result)
