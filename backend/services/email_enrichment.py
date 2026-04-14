from __future__ import annotations

import logging

from backend.models.contact import Contact, EmailRecord

logger = logging.getLogger(__name__)


class EmailEnrichmentService:
    """Strict email enrichment: no guessed addresses."""

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

        return None

    def _mock_provider_lookup(self, contact: Contact) -> str | None:
        # Stub for Apollo/Clearbit-style enrichment. Returns None unless integrated.
        logger.debug("Mock provider lookup for contact=%s", contact.id)
        return None
