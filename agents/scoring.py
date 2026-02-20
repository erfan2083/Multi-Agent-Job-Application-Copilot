from __future__ import annotations

from datetime import datetime, timezone
from schemas.candidate import CandidateProfile
from schemas.job import JobNormalized, JobWithScores, Scores


def score_job(job: JobNormalized, profile: CandidateProfile) -> Scores:
    if profile.preferences.remote_only and not job.remote:
        return Scores(fit_score=1, win_probability=1, reasons=["Remote-only preference mismatch"], missing_skills=[], matched_skills=[])
    matched = []
    missing = []
    fit = 20.0
    desc = (job.description + " " + " ".join(job.requirements)).lower()
    for hs in profile.skills.hard:
        if hs.name.lower() in desc:
            fit += 12
            matched.append(hs.name)
    for req in job.requirements:
        if req.lower() not in desc:
            missing.append(req)
    if any(k.lower() in desc for k in profile.preferences.exclude_keywords):
        fit -= 30
    if profile.preferences.include_keywords and any(k.lower() in desc for k in profile.preferences.include_keywords):
        fit += 10
    fit = max(0, min(100, fit))
    win = fit * 0.7
    if job.posted_at and (datetime.now(timezone.utc) - job.posted_at).days <= 7:
        win += 10
    if job.apply_method.type == "email":
        win += 10
    if job.apply_method.type == "ats":
        win -= 10
    win = max(0, min(100, win))
    reasons = [f"Matched skills: {', '.join(matched) or 'none'}", f"Apply method: {job.apply_method.type}"]
    return Scores(fit_score=fit, win_probability=win, reasons=reasons, missing_skills=missing, matched_skills=matched)


def score_jobs(jobs: list[JobNormalized], profile: CandidateProfile) -> list[JobWithScores]:
    scored = [JobWithScores(job=j, scores=score_job(j, profile)) for j in jobs]
    return sorted(scored, key=lambda x: (x.scores.fit_score, x.scores.win_probability), reverse=True)
