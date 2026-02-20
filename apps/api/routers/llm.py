from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from services.llm import llm_service

router = APIRouter(prefix="/llm", tags=["llm"])


class GenerateRequest(BaseModel):
    prompt: str
    json_schema: dict | None = None


@router.post("/generate")
def generate(payload: GenerateRequest, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    result = llm_service.generate(payload.prompt, user_token=token, json_schema=payload.json_schema)
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"])
    return {"result": result}
