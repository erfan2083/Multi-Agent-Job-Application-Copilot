from __future__ import annotations

from services.storage import storage_service
from schemas.candidate import CandidateProfile
from schemas.job import JobWithScores


def generate_docs(profile: CandidateProfile, jobs: list[JobWithScores]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for job in jobs:
        jid = str(job.job.id)
        facts = ", ".join([s.name for s in profile.skills.hard[:5]])
        cover = (
            f"Dear {job.job.company} hiring team,\n"
            f"I am excited to apply for {job.job.title}. My background includes {facts}.\n"
            "This letter only reflects details from my provided resume."
        )
        bullet_tweaks = "\n".join([f"- Emphasize {m}" for m in job.scores.matched_skills[:5]])
        cover_path = storage_service.write_text("docs", f"{jid}_cover_letter.txt", cover)
        resume_adj_path = storage_service.write_text("docs", f"{jid}_resume_tweaks.txt", bullet_tweaks or "- No matched skills identified.")
        output[jid] = {"cover_letter": cover_path, "resume_tweaks": resume_adj_path}
    return output
