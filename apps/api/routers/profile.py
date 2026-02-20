from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
import pdfplumber
from io import BytesIO
from docx import Document
from agents.resume_analyst import extract_candidate_profile

router = APIRouter(prefix="/profile", tags=["profile"])


def _read_resume(upload: UploadFile | None, resume_text: str | None) -> str:
    if resume_text:
        return resume_text
    if not upload:
        raise HTTPException(status_code=400, detail="Provide resume file or resume_text")
    suffix = (upload.filename or "").lower()
    data = upload.file.read()
    if suffix.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    if suffix.endswith(".pdf"):
        with pdfplumber.open(BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    if suffix.endswith(".docx"):
        doc = Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    raise HTTPException(status_code=400, detail="Unsupported resume format")


@router.post("/parse_resume")
async def parse_resume(file: UploadFile | None = File(default=None), resume_text: str | None = Form(default=None), remote_only: bool = Form(default=True)):
    text = _read_resume(file, resume_text)
    profile = extract_candidate_profile(text, {"remote_only": remote_only})
    return profile
