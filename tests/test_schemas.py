from schemas.candidate import CandidateProfile
from schemas.job import ApplyMethod, JobNormalized
from core.utils.dates import utcnow


def test_candidate_profile_defaults():
    profile = CandidateProfile(name="Jane")
    assert profile.preferences.remote_only is True


def test_job_schema():
    job = JobNormalized(
        source="x",
        source_job_id="1",
        url="https://example.com",
        title="Engineer",
        company="Acme",
        description="Python FastAPI",
        apply_method=ApplyMethod(type="email", email="hr@example.com"),
        extracted_at=utcnow(),
    )
    assert job.apply_method.type == "email"
