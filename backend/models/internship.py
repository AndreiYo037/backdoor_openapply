from __future__ import annotations

from pydantic import BaseModel, Field


class Internship(BaseModel):
    id: str
    company: str
    role: str
    description: str = ""
    requirements: str = ""
    application_email: str | None = None
    source: str = "InternSG"
    role_match: float = Field(default=0.0, ge=0.0, le=1.0)
