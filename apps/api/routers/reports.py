from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from agents.orchestrator import run_pipeline

router = APIRouter(prefix="/reports", tags=["reports"])
_runs: dict[str, dict] = {}


class RunRequest(BaseModel):
    resume_text: str
    preferences: dict = {}


@router.post("/run")
def run(payload: RunRequest):
    state = run_pipeline(payload.resume_text, payload.preferences)
    run_id = str(state["report"].run_id)
    _runs[run_id] = state["report"].model_dump()
    return {"run_id": run_id, "top_jobs": state["scored_jobs"][:10]}


@router.get("/{run_id}")
def get_report(run_id: str):
    return _runs.get(run_id, {"error": "not found"})
