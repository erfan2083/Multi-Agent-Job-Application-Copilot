"""Job match scorer — scores jobs against a candidate profile using LLM or fallback."""

from __future__ import annotations

import json
import logging
import re

from backend.claude_session import fallback_score_job
from backend.config import settings
from backend.llm_provider import BaseLLMProvider
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

BATCH_SCORE_PROMPT = """You are a job match evaluator. Score how well this candidate matches EACH of the following jobs (0-100).

Candidate Profile:
{profile_json}

Jobs to evaluate:
{jobs_json}

Return ONLY a valid JSON array with one object per job, in the same order:
[
  {{"job_index": 0, "score": 75, "reason": "Brief explanation"}},
  {{"job_index": 1, "score": 60, "reason": "Brief explanation"}}
]"""


async def score_job(
    claude: BaseLLMProvider | None,
    profile: dict,
    job: dict,
) -> JobScoreResult:
    """Score a single job listing against a candidate profile.

    Uses Claude if available, falls back to rule-based scoring.
    """
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


async def score_jobs_batch(
    claude: BaseLLMProvider | None,
    profile: dict,
    jobs: list[dict],
    batch_size: int | None = None,
) -> list[JobScoreResult]:
    """Score multiple jobs in batches to reduce API calls.

    With batch_size=5, scoring 10 jobs uses 2 API calls instead of 10.
    """
    if batch_size is None:
        batch_size = settings.llm_score_batch_size

    all_results: list[JobScoreResult] = []

    if not claude or not claude.is_ready:
        for job in jobs:
            result = fallback_score_job(profile, job)
            all_results.append(JobScoreResult(**result))
        return all_results

    for i in range(0, len(jobs), batch_size):
        batch = jobs[i : i + batch_size]

        # Build concise job descriptions for the batch
        jobs_brief = []
        for idx, job in enumerate(batch):
            jobs_brief.append({
                "index": idx,
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "description": job.get("description", "")[:1500],
            })

        try:
            prompt = BATCH_SCORE_PROMPT.format(
                profile_json=json.dumps(profile, ensure_ascii=False, indent=2),
                jobs_json=json.dumps(jobs_brief, ensure_ascii=False, indent=2),
            )

            raw = await claude.ask(prompt)

            # Parse the JSON array from the response
            scores = _parse_score_array(raw)

            # Map results by index
            score_map: dict[int, dict] = {}
            for s in scores:
                idx = s.get("job_index", s.get("index", -1))
                score_map[idx] = s

            for idx, job in enumerate(batch):
                if idx in score_map:
                    s = score_map[idx]
                    all_results.append(JobScoreResult(
                        score=int(s.get("score", 0)),
                        reason=s.get("reason", ""),
                        pros=s.get("pros", []),
                        cons=s.get("cons", []),
                    ))
                else:
                    result = fallback_score_job(profile, job)
                    all_results.append(JobScoreResult(**result))

        except Exception as e:
            logger.warning(f"Batch scoring failed, using fallback: {e}")
            for job in batch:
                result = fallback_score_job(profile, job)
                all_results.append(JobScoreResult(**result))

    return all_results


def _parse_score_array(raw: str) -> list[dict]:
    """Extract a JSON array from the LLM response, handling common formats."""
    # Try markdown code block first
    code_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if code_match:
        text = code_match.group(1).strip()
    else:
        text = raw.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # Try to find a JSON array anywhere in the text
    arr_match = re.search(r"\[[\s\S]*\]", raw)
    if arr_match:
        try:
            parsed = json.loads(arr_match.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    logger.error(f"Could not parse score array from LLM response: {raw[:300]}")
    return []
