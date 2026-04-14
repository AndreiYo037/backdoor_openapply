from __future__ import annotations

import re
from typing import Iterable

from backend.models.contact import Contact, ContactScore, EmailRecord

TARGET_ROLE_KEYWORDS = {
    "software": {"engineer", "developer", "backend", "frontend", "fullstack", "swe"},
    "data": {"data", "analyst", "scientist", "ml", "ai"},
    "product": {"product", "pm"},
    "design": {"design", "ux", "ui"},
    "marketing": {"marketing", "growth", "brand"},
}

NEGATIVE_ROLE_TERMS = {"sales", "accountant", "legal", "operations", "finance", "procurement"}


def _seniority_value(seniority: str) -> float:
    if seniority == "manager":
        return 0.7
    if seniority == "director":
        return 0.55
    return 0.85


def _reachability_score(contact: Contact, university: str) -> float:
    alumni = 1.0 if university and university.lower() in contact.education.lower() else 0.3
    small_gap = 0.8 if contact.seniority in {"individual_contributor", "manager"} else 0.5
    role_l = contact.role.lower()
    similar_path = 0.8 if any(t in role_l for t in {"engineer", "product", "talent", "recruit"}) else 0.45

    years = [int(part) for part in re.findall(r"\d+", contact.experience)]
    years_value = years[0] if years else 5
    career_distance = 1.0 if years_value <= 8 else 0.6
    return min(
        (alumni * 0.35) + (small_gap * 0.30) + (similar_path * 0.20) + (career_distance * 0.15),
        1.0,
    )


def _role_relevance(role_query: str, contact_role: str) -> float:
    role_query_l = role_query.lower()
    contact_role_l = contact_role.lower()
    if any(term in contact_role_l for term in NEGATIVE_ROLE_TERMS):
        return 0.0
    role_tokens = set(role_query_l.split())
    contact_tokens = set(contact_role_l.split())
    overlap = len(role_tokens & contact_tokens) / max(len(role_tokens), 1)

    intent_boost = 0.0
    for family, keywords in TARGET_ROLE_KEYWORDS.items():
        if family in role_query_l and any(word in contact_role_l for word in keywords):
            intent_boost = max(intent_boost, 0.35)
    recruiter_boost = 0.2 if any(k in contact_role_l for k in {"recruiter", "hiring", "talent"}) else 0.0
    return min(overlap + intent_boost + recruiter_boost, 1.0)


class ScoringEngine:
    def score(
        self,
        contacts: Iterable[Contact],
        role_query: str,
        university: str,
        email_by_contact_id: dict[str, EmailRecord],
    ) -> list[ContactScore]:
        role_tokens = set(role_query.lower().split())
        scores: list[ContactScore] = []
        for contact in contacts:
            contact_tokens = set(contact.role.lower().split())
            lexical_overlap = len(role_tokens & contact_tokens) / max(len(role_tokens), 1)
            role_relevance = _role_relevance(role_query, contact.role)
            role_match = min((0.55 * lexical_overlap) + (0.45 * role_relevance), 1.0)
            affinity = 1.0 if university and university.lower() in contact.education.lower() else 0.5
            seniority = _seniority_value(contact.seniority)
            activity = min(max(contact.activity, 0.0), 1.0)
            email = email_by_contact_id.get(contact.id)
            email_confidence = email.confidence_score if email else 0.0
            reachability = _reachability_score(contact, university)
            final_score = min(
                (0.35 * role_match)
                + (0.25 * affinity)
                + (0.20 * seniority)
                + (0.10 * activity)
                + (0.10 * email_confidence)
                + (0.10 * reachability),
                1.0,
            )
            scores.append(
                ContactScore(
                    contact_id=contact.id,
                    role_match=role_match,
                    affinity=affinity,
                    seniority=seniority,
                    activity=activity,
                    email_confidence=email_confidence,
                    reachability_score=reachability,
                    final_score=final_score,
                )
            )
        return sorted(scores, key=lambda item: item.final_score, reverse=True)

    def apply_hard_filters(
        self,
        contacts: list[Contact],
        scores: list[ContactScore],
        email_by_contact_id: dict[str, EmailRecord],
        max_per_company: int = 5,
    ) -> list[tuple[Contact, ContactScore]]:
        score_index = {score.contact_id: score for score in scores}
        kept: list[tuple[Contact, ContactScore]] = []
        company_counter: dict[str, int] = {}

        for contact in sorted(contacts, key=lambda c: score_index[c.id].final_score, reverse=True):
            score = score_index[contact.id]
            email = email_by_contact_id.get(contact.id)
            if email and email.confidence_label == "LOW":
                continue
            if score.role_match < 0.35 or score.activity < 0.35 or score.reachability_score < 0.40:
                continue
            used = company_counter.get(contact.company, 0)
            if used >= max(3, min(max_per_company, 5)):
                continue
            company_counter[contact.company] = used + 1
            kept.append((contact, score))
        return kept
