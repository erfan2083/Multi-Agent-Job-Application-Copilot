"""Resume parser — extracts text from PDF and DOCX files."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
from docx import Document


def parse_pdf(file_path: str | Path) -> str:
    """Extract all text from a PDF file."""
    text_parts: list[str] = []
    with fitz.open(str(file_path)) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def parse_docx(file_path: str | Path) -> str:
    """Extract all text from a DOCX file."""
    doc = Document(str(file_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs).strip()


def parse_resume(file_path: str | Path) -> str:
    """Parse a resume file and return its raw text.

    Supports .pdf and .docx formats.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(path)
    elif suffix in (".docx", ".doc"):
        return parse_docx(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use PDF or DOCX.")
