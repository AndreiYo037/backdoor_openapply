from __future__ import annotations

import logging
import re

from backend.models.contact import Contact, EmailRecord

logger = logging.getLogger(__name__)


def infer_domain(company: str) -> str:
    clean = re.sub(r"[^a-z0-9]", "", company.lower())
    return f"{clean or 'company'}.com"


def enrich_contacts(company: str) -> list[str]:
    domain = infer_domain(company)
    return [f"careers@{domain}", f"hr@{domain}", f"jobs@{domain}"]


class EmailEnrichmentService:
    """Email enrichment with company fallback aliases."""

    def enrich(
        self,
        contact: Contact,
        internsg_email: str | None,
    ) -> EmailRecord | None:
        if internsg_email:
            # Per pipeline contract: InternSG-provided email is trusted as HIGH.
            return EmailRecord(
                id=f"email-{contact.id}",
                contact_id=contact.id,
                email=internsg_email,
                confidence_score=1.0,
                confidence_label="HIGH",
            )

        provider_email = self._mock_provider_lookup(contact)
        if provider_email:
            return EmailRecord(
                id=f"email-{contact.id}",
                contact_id=contact.id,
                email=provider_email,
                confidence_score=0.7,
                confidence_label="MEDIUM",
            )

        aliases = enrich_contacts(contact.company)
        if not aliases:
            return None
        return EmailRecord(
            id=f"email-{contact.id}",
            contact_id=contact.id,
            email=aliases[0],
            confidence_score=0.4,
            confidence_label="LOW",
        )

    def _mock_provider_lookup(self, contact: Contact) -> str | None:
        # Stub for Apollo/Clearbit-style enrichment. Returns None unless integrated.
        logger.debug("Mock provider lookup for contact=%s", contact.id)
        return None
