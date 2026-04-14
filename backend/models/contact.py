from __future__ import annotations

from pydantic import BaseModel, Field


class Contact(BaseModel):
    id: str
    name: str
    role: str
    company: str
    linkedin_url: str
    education: str = ""
    seniority: str = "individual_contributor"
    experience: str = ""
    activity: float = Field(default=0.5, ge=0.0, le=1.0)


class EmailRecord(BaseModel):
    id: str
    contact_id: str
    email: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_label: str


class ContactScore(BaseModel):
    contact_id: str
    role_match: float = Field(ge=0.0, le=1.0)
    affinity: float = Field(ge=0.0, le=1.0)
    seniority: float = Field(ge=0.0, le=1.0)
    activity: float = Field(ge=0.0, le=1.0)
    email_confidence: float = Field(ge=0.0, le=1.0)
    reachability_score: float = Field(ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)
