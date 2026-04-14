from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
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
    state = AppState(users={}, internships={}, contacts={}, emails={}, contact_scores={})

    @router.post("/pipeline/run")
    async def run_pipeline(
        target_role: str = Form(...),
        user_id: str = Form("u1"),
        user_name: str = Form("Student"),
        user_email: str = Form("student@example.com"),
        university: str = Form("National University of Singapore"),
        cv: UploadFile = File(...),
    ) -> dict[str, Any]:
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
            internships = scraper.scrape(target_role, limit=30)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        ranked_internships = score_internships(cv_text, internships)[:20]
        for internship in ranked_internships:
            state.internships[internship.id] = internship
            database.upsert_internship(internship.model_dump(exclude={"role_match"}))

        company_best_email: dict[str, str | None] = {}
        for internship in ranked_internships:
            if internship.company not in company_best_email and internship.application_email:
                company_best_email[internship.company] = internship.application_email

        all_contacts: list[Contact] = []
        for internship in ranked_internships[:8]:
            company_contacts = linkedin.discover_contacts(internship.company, target_role, limit=12)
            all_contacts.extend(company_contacts)

        for contact in all_contacts:
            state.contacts[contact.id] = contact
            database.upsert_contact(contact.model_dump(exclude={"experience", "activity"}))

        email_by_contact_id: dict[str, Any] = {}
        for contact in all_contacts:
            email_record = email_service.enrich(contact, company_best_email.get(contact.company))
            if email_record:
                state.emails[email_record.id] = email_record.model_dump()
                email_by_contact_id[contact.id] = email_record
                database.upsert_email(
                    {
                        "id": email_record.id,
                        "contact_id": email_record.contact_id,
                        "email": email_record.email,
                        "confidence_score": email_record.confidence_score,
                    }
                )

        scored = scoring.score(all_contacts, target_role, university, email_by_contact_id)
        filtered = scoring.apply_hard_filters(all_contacts, scored, email_by_contact_id, max_per_company=5)

        contacts_out = []
        for contact, score_row in filtered:
            email_row = email_by_contact_id.get(contact.id)
            strategy_plan = strategy.decide(contact, email_row)
            state.contact_scores[contact.id] = score_row.model_dump()
            database.upsert_contact_score(score_row.model_dump())
            contacts_out.append(
                {
                    "contact": contact.model_dump(),
                    "score": score_row.model_dump(),
                    "email": email_row.model_dump() if email_row else None,
                    "strategy": strategy_plan,
                    "why_selected": (
                        f"Role match {score_row.role_match:.2f}, affinity {score_row.affinity:.2f}, "
                        f"reachability {score_row.reachability_score:.2f}"
                    ),
                }
            )

        return {
            "user": state.users[user_id].model_dump(),
            "cv_text": cv_text,
            "internships": [internship.model_dump() for internship in ranked_internships],
            "contacts": contacts_out,
        }

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
