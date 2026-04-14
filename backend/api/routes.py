from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import logging
import time
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from backend.models.contact import Contact
from backend.models.internship import Internship
from backend.services.cv_matching import extract_cv_text, score_internships
from backend.services.email_enrichment import EmailEnrichmentService
from backend.services.internsg_scraper import InternSGScraper
from backend.services.linkedin_search import LinkedInSearchService
from backend.services.message_generator import MessageGenerator
from backend.services.outreach_tracker import OutreachTracker
from backend.services.scoring_engine import ScoringEngine
from backend.services.strategy_engine import StrategyEngine
from backend.storage.database import PersistentDatabase

logger = logging.getLogger(__name__)
TARGET_CONTACTS_PER_COMPANY = 5
MIN_CONTACTS_PER_COMPANY = 3
FINAL_MIN_RESULTS = 3
FINAL_MAX_RESULTS = 5


class UserRecord(BaseModel):
    id: str
    name: str
    email: str
    university: str
    cv_url: str


class OutreachLogInput(BaseModel):
    user_id: str
    contact_id: str
    channel: str
    sent: bool = True
    replied: bool = False
    positive_reply: bool = False


class ContactSelectionInput(BaseModel):
    user_id: str
    contact_ids: list[str] = Field(default_factory=list)
    daily_cap: int = 20


class MessageInput(BaseModel):
    user_id: str
    contact_id: str
    internship_id: str


@dataclass
class AppState:
    users: dict[str, UserRecord]
    internships: dict[str, Internship]
    contacts: dict[str, Contact]
    emails: dict[str, dict[str, Any]]
    contact_scores: dict[str, dict[str, Any]]
    contact_results_by_key: dict[str, list[dict[str, Any]]]


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api")
    database = PersistentDatabase()
    scraper = InternSGScraper()
    linkedin = LinkedInSearchService()
    email_service = EmailEnrichmentService()
    scoring = ScoringEngine()
    strategy = StrategyEngine()
    message_generator = MessageGenerator()
    tracker = OutreachTracker(database)
    state = AppState(
        users={},
        internships={},
        contacts={},
        emails={},
        contact_scores={},
        contact_results_by_key={},
    )

    def _result_key(company: str, role: str) -> str:
        return f"{company.strip().lower()}||{role.strip().lower()}"

    def _dedupe_contacts(contacts: list[Contact], company: str) -> list[Contact]:
        unique: dict[tuple[str, str, str], Contact] = {}
        for contact in contacts:
            if contact.company.lower() != company.lower():
                continue
            unique_key = (contact.name.strip().lower(), contact.company.strip().lower(), contact.role.strip().lower())
            if unique_key not in unique:
                unique[unique_key] = contact
        return list(unique.values())

    def _format_contact_output(
        contact: Contact,
        score_row: Any,
        email_row: Any,
    ) -> dict[str, Any]:
        reason = (
            f"Role match {score_row.role_match:.2f}, affinity {score_row.affinity:.2f}, "
            f"reachability {score_row.reachability_score:.2f}"
        )
        return {
            "id": contact.id,
            "name": contact.name,
            "role": contact.role,
            "company": contact.company,
            "linkedin_url": contact.linkedin_url,
            "email": email_row.email if email_row else None,
            "email_confidence": email_row.confidence_label if email_row else "NONE",
            "scores": {
                "role_match": score_row.role_match,
                "affinity": score_row.affinity,
                "reachability": score_row.reachability_score,
                "final": score_row.final_score,
            },
            "reason": reason,
        }

    def _internship_quality_score(internship: Internship, contact: Contact) -> int:
        score = 0
        title = internship.role.lower()
        body = f"{internship.role} {internship.description} {internship.requirements}".lower()
        contact_role = contact.role.lower()
        if "intern" in title:
            score += 5
        if any(token in body for token in {"machine learning", "ml", "ai", "data science"}):
            score += 5
        if "singapore" in body:
            score += 3
        if any(token in contact_role for token in {"recruiter", "talent acquisition", "hiring"}):
            score += 5
        elif any(token in contact_role for token in {"engineer", "data scientist", "machine learning"}):
            score += 4
        else:
            score += 2
        if "." in contact.linkedin_url:
            score += 2
        return score

    @router.post("/pipeline/run")
    async def run_pipeline(
        target_role: str = Form(...),
        user_id: str = Form("u1"),
        user_name: str = Form("Student"),
        user_email: str = Form("student@example.com"),
        university: str = Form("National University of Singapore"),
        cv: UploadFile = File(...),
    ) -> dict[str, Any]:
        state.internships.clear()
        state.contacts.clear()
        state.emails.clear()
        state.contact_scores.clear()
        state.contact_results_by_key.clear()

        pdf_bytes = await cv.read()
        cv_text = extract_cv_text(pdf_bytes)
        state.users[user_id] = UserRecord(
            id=user_id,
            name=user_name,
            email=user_email,
            university=university,
            cv_url=f"uploads/{cv.filename}",
        )
        database.upsert_user(state.users[user_id].model_dump())

        try:
            logger.info("Pipeline start: user_id=%s role='%s'", user_id, target_role)
            scrape_start = time.perf_counter()
            internships = scraper.scrape(target_role, limit=30)
            logger.info("InternSG scrape duration=%.2fs", time.perf_counter() - scrape_start)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        ranked_internships = score_internships(cv_text, internships)[:20]
        logger.info("Pipeline internships ranked: count=%s", len(ranked_internships))
        for internship in ranked_internships:
            state.internships[internship.id] = internship
            database.upsert_internship(internship.model_dump(exclude={"role_match"}))

        company_best_email: dict[str, str | None] = {}
        for internship in ranked_internships:
            if internship.company not in company_best_email and internship.application_email:
                company_best_email[internship.company] = internship.application_email

        contacts_out: list[dict[str, Any]] = []
        qualified_jobs: list[dict[str, Any]] = []
        linkedin_matches = 0

        for internship in ranked_internships:
            company = internship.company
            internship_role = internship.role or target_role
            if not company.strip():
                continue

            body = f"{internship.role} {internship.description} {internship.requirements}".lower()
            if "intern" not in internship.role.lower():
                continue
            if len(internship.description.strip()) < 60:
                continue
            if not any(token in body for token in {"machine learning", "ml", "ai", "data science"}):
                continue

            discovered = linkedin.discover_contacts(company, internship_role, limit=TARGET_CONTACTS_PER_COMPANY)
            deduped_contacts = _dedupe_contacts(discovered, company)[:TARGET_CONTACTS_PER_COMPANY]
            if not deduped_contacts:
                continue

            linkedin_matches += len(deduped_contacts)
            best_contact = deduped_contacts[0]
            quality_score = _internship_quality_score(internship, best_contact)
            qualified_jobs.append(
                {
                    "title": internship.role,
                    "company": internship.company,
                    "location": "Singapore" if "singapore" in body else "Unknown",
                    "description": internship.description,
                    "linkedin_contact": {
                        "name": best_contact.name,
                        "role": best_contact.role,
                        "linkedin_url": best_contact.linkedin_url,
                    },
                    "quality_score": quality_score,
                }
            )

        final_jobs = sorted(qualified_jobs, key=lambda row: row["quality_score"], reverse=True)[:FINAL_MAX_RESULTS]
        if len(final_jobs) >= FINAL_MIN_RESULTS:
            final_jobs = final_jobs[:FINAL_MAX_RESULTS]

        logger.info(
            "Pipeline strict metrics: %s",
            {
                "expanded_queries": scraper.expand_query(target_role),
                "raw_results": len(internships),
                "after_filtering": len(qualified_jobs),
                "linkedin_found": linkedin_matches,
                "final_count": len(final_jobs),
            },
        )

        return {
            "user": state.users[user_id].model_dump(),
            "cv_text": cv_text,
            "internships": final_jobs,
            "contacts": contacts_out,
            "reason": (
                None
                if final_jobs
                else "No high-quality internships found with identifiable LinkedIn contacts"
            ),
            "debug": {
                "raw_count": len(internships),
                "filtered_count": len(qualified_jobs),
                "linkedin_matches": linkedin_matches,
            },
        }

    @router.get("/contacts")
    def get_contacts(
        company: str = Query(..., min_length=1),
        role: str = Query(..., min_length=1),
    ) -> dict[str, Any]:
        key = _result_key(company, role)
        contacts = state.contact_results_by_key.get(key, [])
        return {"company": company, "role": role, "contacts": contacts}

    @router.post("/outreach/messages")
    def generate_messages(payload: MessageInput) -> dict[str, str]:
        user = state.users.get(payload.user_id)
        contact = state.contacts.get(payload.contact_id)
        internship = state.internships.get(payload.internship_id)
        if not user or not contact or not internship:
            raise HTTPException(status_code=404, detail="User/contact/internship not found")
        return message_generator.generate(contact, internship, "CV uploaded by user", user.university)

    @router.post("/outreach/select")
    def enforce_selection(payload: ContactSelectionInput) -> dict[str, Any]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for contact_id in payload.contact_ids:
            contact = state.contacts.get(contact_id)
            if contact:
                grouped[contact.company].append(contact_id)
        violations = {company: ids for company, ids in grouped.items() if len(ids) > 5}
        if violations:
            raise HTTPException(status_code=400, detail="Max 5 contacts per company exceeded")
        sent_today = tracker.count_sent_today(payload.user_id)
        if sent_today + len(payload.contact_ids) > payload.daily_cap:
            raise HTTPException(status_code=400, detail="Daily outreach cap exceeded")
        return {"ok": True, "selected_count": len(payload.contact_ids)}

    @router.post("/outreach/logs")
    def log_outreach(payload: OutreachLogInput) -> dict[str, Any]:
        row = tracker.record(
            user_id=payload.user_id,
            contact_id=payload.contact_id,
            channel=payload.channel,
            sent=payload.sent,
            replied=payload.replied,
            positive_reply=payload.positive_reply,
        )
        return {"outreach_log": row}

    @router.get("/admin/stats")
    def read_stats() -> dict[str, Any]:
        persisted = database.table_counts()
        return {
            "database_path": database.db_path,
            "persisted_counts": persisted,
            "in_memory_counts": {
                "users": len(state.users),
                "internships": len(state.internships),
                "contacts": len(state.contacts),
                "emails": len(state.emails),
                "contact_scores": len(state.contact_scores),
                "outreach_logs": len(tracker.logs),
            },
        }

    return router
