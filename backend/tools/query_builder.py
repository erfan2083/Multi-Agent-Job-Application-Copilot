"""Query builder — generates search queries from profile and preferences using LLM or rules."""

from __future__ import annotations

import json
import logging

from backend.llm_provider import BaseLLMProvider
from backend.models import SearchQueries

logger = logging.getLogger(__name__)

QUERY_PROMPT_TEMPLATE = """Based on this candidate profile and preferences, generate optimal search queries for job boards.

Profile: {profile_json}
Preferences: {preferences}

Return ONLY valid JSON, no extra text:
{{
  "keywords": ["Python developer", "backend engineer"],
  "persian_keywords": ["برنامه‌نویس پایتون", "توسعه‌دهنده بک‌اند"],
  "locations": ["remote", "Tehran"],
  "filters": {{
    "experience_level": "mid",
    "job_type": "remote"
  }}
}}"""


async def build_search_queries(
    claude: BaseLLMProvider | None,
    profile: dict,
    preferences_text: str,
) -> SearchQueries:
    """Build search queries from profile and user preferences.

    Uses Claude if available, falls back to rule-based generation.
    """
    if claude and claude.is_ready:
        try:
            prompt = QUERY_PROMPT_TEMPLATE.format(
                profile_json=json.dumps(profile, ensure_ascii=False, indent=2),
                preferences=preferences_text,
            )

            result = await claude.ask_for_json(prompt)
            return SearchQueries(
                keywords=result.get("keywords", []),
                persian_keywords=result.get("persian_keywords", []),
                locations=result.get("locations", []),
                filters=result.get("filters", {}),
            )
        except Exception as e:
            logger.warning(f"Claude query building failed, using fallback: {e}")

    # Fallback: build queries from profile data
    return _fallback_build_queries(profile, preferences_text)


def _fallback_build_queries(profile: dict, preferences_text: str) -> SearchQueries:
    """Generate search queries using simple rules."""
    keywords = []
    persian_keywords = []

    # Use job titles from profile
    titles = profile.get("job_titles", [])
    for title in titles[:3]:
        keywords.append(title)

    # Use top skills
    skills = profile.get("skills", []) or profile.get("technical_skills", [])
    for skill in skills[:5]:
        keywords.append(f"{skill} developer")

    # If no keywords, use generic terms
    if not keywords:
        keywords = ["software developer", "software engineer"]

    # Try to detect Persian keywords from preferences text
    pref_lower = preferences_text.lower()

    # Common Persian job-related terms
    persian_map = {
        "python": "برنامه‌نویس پایتون",
        "backend": "توسعه‌دهنده بک‌اند",
        "frontend": "توسعه‌دهنده فرانت‌اند",
        "fullstack": "توسعه‌دهنده فول‌استک",
        "devops": "مهندس دوآپس",
        "data": "مهندس داده",
        "mobile": "توسعه‌دهنده موبایل",
        "react": "برنامه‌نویس ری‌اکت",
        "java": "برنامه‌نویس جاوا",
    }

    for eng, per in persian_map.items():
        if eng in pref_lower or any(eng in kw.lower() for kw in keywords):
            persian_keywords.append(per)

    if not persian_keywords:
        persian_keywords = ["برنامه‌نویس", "توسعه‌دهنده نرم‌افزار"]

    # Detect locations
    locations = []
    if "remote" in pref_lower or "ریموت" in preferences_text or "دورکاری" in preferences_text:
        locations.append("remote")
    if "tehran" in pref_lower or "تهران" in preferences_text:
        locations.append("Tehran")

    # Detect job type
    job_type = "any"
    if "remote" in pref_lower or "ریموت" in preferences_text:
        job_type = "remote"
    elif "onsite" in pref_lower or "حضوری" in preferences_text:
        job_type = "onsite"
    elif "hybrid" in pref_lower or "هیبرید" in preferences_text:
        job_type = "hybrid"

    return SearchQueries(
        keywords=keywords,
        persian_keywords=persian_keywords,
        locations=locations,
        filters={"job_type": job_type},
    )
