from __future__ import annotations

import re
from schemas.candidate import CandidateProfile


def extract_candidate_profile(resume_text: str, preferences: dict | None = None) -> CandidateProfile:
    email = re.search(r"[\w\.-]+@[\w\.-]+", resume_text)
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    name = lines[0] if lines else "Unknown"
    hard = []
    for skill in ["python", "fastapi", "sql", "docker", "aws", "javascript"]:
        if skill in resume_text.lower():
            hard.append({"name": skill.title(), "level": 3, "evidence": [f"Mentioned in resume: {skill}"]})
    profile = CandidateProfile(
        name=name,
        email=email.group(0) if email else None,
        headline=lines[1] if len(lines) > 1 else "",
        skills={"hard": hard, "soft": []},
    )
    if preferences:
        profile.preferences = profile.preferences.model_copy(update=preferences)
    return profile
