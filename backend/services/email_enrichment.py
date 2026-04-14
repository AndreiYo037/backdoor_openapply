from __future__ import annotations

import re

from backend.models.contact import Contact, EmailRecord

DOMAIN_SANITIZER = re.compile(r"[^a-z0-9]")
PUBLIC_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "proton.me", "icloud.com"}
GENERIC_LOCALPART_MARKERS = {
    "hr",
    "careers",
    "jobs",
    "recruit",
    "recruitment",
    "hiring",
    "talent",
    "admin",
    "contact",
    "hello",
    "info",
}


def infer_domain(company: str) -> str:
    normalized = company.lower()
    normalized = re.sub(r"\b(pte|ltd|llp|inc|corp|co|company|private|limited)\b", " ", normalized)
    normalized = DOMAIN_SANITIZER.sub("", normalized)
    normalized = normalized or "company"
    return f"{normalized}.com"


def _split_name_parts(name: str) -> tuple[str, str] | None:
    parts = [segment for segment in re.split(r"[\s\-]+", name.lower()) if segment]
    if not parts:
        return None
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""
    return (first, last)


def _email_parts(email: str) -> tuple[str, str]:
    local, _, domain = email.lower().partition("@")
    return local.strip(), domain.strip()


def _is_generic_company_mailbox(local_part: str) -> bool:
    tokens = {token for token in re.split(r"[._\-+]", local_part) if token}
    return bool(tokens & GENERIC_LOCALPART_MARKERS)


def _likely_personal_match(name: str, email: str) -> bool:
    parsed = _split_name_parts(name)
    if not parsed:
        return False
    first, last = parsed
    local_part, _ = _email_parts(email)
    if first and first in local_part and len(first) >= 3:
        return True
    if last and last in local_part and len(last) >= 3:
        return True
    if first and last and f"{first[0]}{last}" in local_part:
        return True
    return False


class EmailEnrichmentService:
    """Email enrichment with confidence tiers:
    HIGH from listing, MEDIUM inferred pattern, LOW discarded by caller/filter.
    """

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

        if contact.name.strip():
            name_parts = _split_name_parts(contact.name)
            if name_parts:
                first, last = name_parts
                domain = infer_domain(contact.company)
                patterns = [
                    f"{first}.{last}@{domain}" if last else "",
                    f"{first}@{domain}",
                    f"{first[0]}{last}@{domain}" if last else "",
                ]
                inferred = next((candidate for candidate in patterns if candidate), "")
                if not inferred:
                    return None
                return EmailRecord(
                    id=f"email-{contact.id}",
                    contact_id=contact.id,
                    email=inferred,
                    confidence_score=0.5,
                    confidence_label="MEDIUM",
                )

        # LOW-confidence fallbacks are discarded by returning None.
        return None
