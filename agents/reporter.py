from __future__ import annotations

from uuid import uuid4
from core.utils.dates import utcnow
from schemas.application import ApplicationRecord
from schemas.job import JobWithScores
from schemas.report import Report
from services.storage import storage_service


def build_report(top_jobs: list[JobWithScores], applications: list[ApplicationRecord], notes: str = "") -> Report:
    report = Report(run_id=uuid4(), timestamp=utcnow(), top_jobs=top_jobs, applied=applications, failed=[], notes=notes)
    md_lines = ["# MJAC Run Report", "", f"Run: {report.run_id}", "", "## Top Jobs"]
    for item in top_jobs[:20]:
        md_lines.append(f"- {item.job.title} @ {item.job.company}: fit {item.scores.fit_score:.1f}, win {item.scores.win_probability:.1f}")
    storage_service.write_text("reports", f"{report.run_id}.md", "\n".join(md_lines))
    storage_service.write_text("reports", f"{report.run_id}.json", report.model_dump_json(indent=2))
    return report
