from __future__ import annotations

from backend.models.contact import Contact, EmailRecord


class StrategyEngine:
    def decide(self, contact: Contact, email_record: EmailRecord | None) -> str:
        if contact.seniority == "manager":
            return "linkedin_first_then_email"
        if not email_record:
            return "linkedin_only"
        if email_record.confidence_label == "HIGH":
            return "email_first_linkedin_followup"
        if email_record.confidence_label == "MEDIUM":
            return "linkedin_first_optional_email"
        return "linkedin_only"
