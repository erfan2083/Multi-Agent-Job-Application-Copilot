from agents.scoring import score_job
from schemas.candidate import CandidateProfile, CandidateSkills, HardSkill, Preferences
from schemas.job import ApplyMethod, JobNormalized
from core.utils.dates import utcnow


def test_scoring_remote_mismatch():
    profile = CandidateProfile(name="x", preferences=Preferences(remote_only=True), skills=CandidateSkills(hard=[]))
    job = JobNormalized(
        source="x", source_job_id="1", url="u", title="t", company="c", description="", remote=False,
        apply_method=ApplyMethod(type="link", apply_url="u"), extracted_at=utcnow()
    )
    s = score_job(job, profile)
    assert s.fit_score <= 1


def test_scoring_match_skill():
    profile = CandidateProfile(name="x", skills=CandidateSkills(hard=[HardSkill(name="Python", level=4)]))
    job = JobNormalized(
        source="x", source_job_id="1", url="u", title="Python Engineer", company="c", description="Need python",
        apply_method=ApplyMethod(type="email", email="hr@example.com"), extracted_at=utcnow()
    )
    s = score_job(job, profile)
    assert s.fit_score > 20
