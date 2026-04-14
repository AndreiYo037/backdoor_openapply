from __future__ import annotations

import io
import re
from typing import Iterable

from pypdf import PdfReader

from backend.models.internship import Internship

TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}")


def extract_cv_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF upload."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def extract_skills(text: str) -> set[str]:
    tokens = {token.lower() for token in TOKEN_PATTERN.findall(text)}
    stop = {"with", "from", "that", "this", "have", "your", "will", "for", "the", "and"}
    return {token for token in tokens if token not in stop and len(token) > 2}


def score_internships(cv_text: str, internships: Iterable[Internship]) -> list[Internship]:
    cv_skills = extract_skills(cv_text)
    ranked: list[Internship] = []
    for internship in internships:
        job_tokens = extract_skills(f"{internship.role} {internship.description} {internship.requirements}")
        overlap = len(cv_skills & job_tokens)
        score = overlap / max(len(job_tokens), 1)
        ranked.append(internship.model_copy(update={"role_match": min(score, 1.0)}))
    return sorted(ranked, key=lambda i: i.role_match, reverse=True)
