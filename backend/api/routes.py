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
from backend.services.company_careers_scraper import CompanyCareersScraper
from backend.services.cv_matching import extract_cv_text, score_internships
from backend.services.internsg_scraper import InternSGScraper
from backend.services.linkedin_search import LinkedInSearchService
from backend.services.message_generator import MessageGenerator
from backend.services.outreach_tracker import OutreachTracker
from backend.storage.database import PersistentDatabase

logger = logging.getLogger(__name__)
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
    careers_scraper = CompanyCareersScraper()
    linkedin = LinkedInSearchService()
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

    def _ok(data: Any) -> dict[str, Any]:
        return {"success": True, "data": data, "error": None}

    def _err(message: str, data: Any | None = None) -> dict[str, Any]:
        return {"success": False, "data": data, "error": message}

    def _result_key(company: str, role: str) -> str:
        return f"{company.strip().lower()}||{role.strip().lower()}"

    def _internship_quality_score(internship: Internship, contact: Contact, role: str) -> int:
        score = 0
        title = internship.role.lower()
        body = f"{internship.role} {internship.description} {internship.requirements}".lower()
        contact_role = contact.role.lower()
        if "intern" in title:
            score += 5
        role_tokens = {token for token in role.lower().split() if token}
        if any(token in body for token in role_tokens):
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

    def _strict_job_filter(internship: Internship, target_role: str) -> bool:
        if "intern" not in internship.role.lower() and "internship" not in internship.role.lower():
            return False
        if not internship.company.strip() or len(internship.description.strip()) < 80:
            return False
        role_tokens = {token for token in target_role.lower().split() if len(token) > 2}
        haystack = f"{internship.role} {internship.description} {internship.requirements}".lower()
        return not role_tokens or any(token in haystack for token in role_tokens)

    def _format_job_output(internship: Internship, contact: Contact, quality_score: int) -> dict[str, Any]:
        return {
            "id": internship.id,
            "title": internship.role,
            "company": internship.company,
            "location": internship.location or ("Singapore" if "singapore" in internship.description.lower() else ""),
            "description": internship.description,
            "url": internship.job_url,
            "source": internship.source,
            "linkedin_contact": {
                "name": contact.name,
                "role": contact.role,
                "linkedin_url": contact.linkedin_url,
            },
            "quality_score": quality_score,
        }

    @router.post("/pipeline/run")
    async def run_pipeline(
        target_role: str = Form(...),
        user_id: str = Form("u1"),
        user_name: str = Form("Student"),
        user_email: str = Form("student@example.com"),
        university: str = Form("National University of Singapore"),
        cv: UploadFile = File(...),
    ) -> dict[str, Any]:
        try:
            logger.info("[API] PipelineEntry -> Input: user_id=%s role=%s", user_id, target_role)
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

            scrape_start = time.perf_counter()
            logger.info("[Service] InternSGScraper -> Input: role=%s", target_role)
            internships = scraper.scrape(target_role, limit=30)
            logger.info("[Service] InternSGScraper -> Output: count=%s duration=%.2fs", len(internships), time.perf_counter() - scrape_start)
            ranked_stage1 = score_internships(cv_text, internships)[:25]
            logger.info("[Service] CVMatching -> Output: ranked_count=%s", len(ranked_stage1))
            for internship in ranked_stage1:
                state.internships[internship.id] = internship
                database.upsert_internship(internship.model_dump(exclude={"role_match"}))

            def qualify_jobs(rows: list[Internship]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
                qualified: list[dict[str, Any]] = []
                debug_rows: list[dict[str, Any]] = []
                linkedin_candidates = 0
                for internship in rows:
                    if not _strict_job_filter(internship, target_role):
                        continue
                    logger.info("[Service] LinkedInSearch -> Input: company=%s role=%s", internship.company, internship.role)
                    contact, debug_row = linkedin.discover_job_contact(internship.company, internship.role or target_role)
                    linkedin_candidates += int(debug_row.get("candidates_found", 0))
                    debug_rows.append(debug_row)
                    if not contact:
                        continue
                    quality_score = _internship_quality_score(internship, contact, target_role)
                    qualified.append(_format_job_output(internship, contact, quality_score))
                return qualified, debug_rows, linkedin_candidates

            qualified_stage1, per_job_debug, linkedin_candidates = qualify_jobs(ranked_stage1)

            if len(qualified_stage1) >= FINAL_MIN_RESULTS:
                final_jobs = sorted(qualified_stage1, key=lambda row: row["quality_score"], reverse=True)[:FINAL_MAX_RESULTS]
            else:
                logger.info("[Service] CompanyCareersScraper -> Input: role=%s", target_role)
                stage2_rows = careers_scraper.scrape(target_role, limit=20)
                logger.info("[Service] CompanyCareersScraper -> Output: count=%s", len(stage2_rows))
                stage2_internships = [
                    Internship(
                        id=f"career-{idx}",
                        company=row.company,
                        role=row.title,
                        location=row.location,
                        description=row.description,
                        requirements=row.description,
                        job_url=row.job_url,
                        source="CareerPage",
                    )
                    for idx, row in enumerate(stage2_rows, start=1)
                ]
                qualified_stage2, debug_stage2, linkedin_candidates_stage2 = qualify_jobs(stage2_internships)
                per_job_debug.extend(debug_stage2)
                linkedin_candidates += linkedin_candidates_stage2
                merged = qualified_stage1 + qualified_stage2
                final_jobs = sorted(merged, key=lambda row: row["quality_score"], reverse=True)[:FINAL_MAX_RESULTS]

            logger.info(
                "[API] PipelineExit -> Output: %s",
                {
                    "expanded_queries": scraper.expand_query(target_role),
                    "raw_results": len(ranked_stage1),
                    "filtered_jobs": len(qualified_stage1),
                    "linkedin_profiles_found": linkedin_candidates,
                    "qualified_profiles": sum(1 for row in per_job_debug if row.get("selected_profile_name")),
                    "final_count": len(final_jobs),
                },
            )

            payload = {
                "user": state.users[user_id].model_dump(),
                "cv_text": cv_text,
                "jobs": final_jobs,
                "internships": final_jobs,
                "contacts": [],
                "reason": None if final_jobs else "No internships met high-confidence LinkedIn contact requirement",
                "debug": {
                    "raw_jobs": len(ranked_stage1),
                    "filtered_jobs": len(qualified_stage1),
                    "linkedin_candidates": linkedin_candidates,
                    "qualified_contacts": sum(1 for row in per_job_debug if row.get("selected_profile_name")),
                },
            }
            response = _ok(payload)
            response.update(payload)
            return response
        except RuntimeError as exc:
            logger.exception("[API] PipelineError -> %s", exc)
            raise HTTPException(status_code=503, detail=_err(str(exc)))
        except Exception as exc:
            logger.exception("[API] PipelineUnhandledError -> %s", exc)
            raise HTTPException(status_code=500, detail=_err("Internal server error"))

    @router.get("/contacts")
    def get_contacts(
        company: str = Query(..., min_length=1),
        role: str = Query(..., min_length=1),
    ) -> dict[str, Any]:
        try:
            logger.info("[API] ContactsEntry -> Input: company=%s role=%s", company, role)
            key = _result_key(company, role)
            contacts = state.contact_results_by_key.get(key, [])
            payload = {"company": company, "role": role, "contacts": contacts}
            response = _ok(payload)
            response.update(payload)
            return response
        except Exception as exc:
            logger.exception("[API] ContactsError -> %s", exc)
            raise HTTPException(status_code=500, detail=_err("Failed to load contacts"))

    @router.post("/outreach/messages")
    def generate_messages(payload: MessageInput) -> dict[str, str]:
        try:
            logger.info("[API] GenerateMessagesEntry -> Input: user_id=%s", payload.user_id)
            user = state.users.get(payload.user_id)
            contact = state.contacts.get(payload.contact_id)
            internship = state.internships.get(payload.internship_id)
            if not user or not contact or not internship:
                raise HTTPException(status_code=404, detail=_err("User/contact/internship not found"))
            message = message_generator.generate(contact, internship, "CV uploaded by user", user.university)
            response = _ok(message)
            response.update(message)
            return response
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("[API] GenerateMessagesError -> %s", exc)
            raise HTTPException(status_code=500, detail=_err("Message generation failed"))

    @router.post("/outreach/select")
    def enforce_selection(payload: ContactSelectionInput) -> dict[str, Any]:
        try:
            grouped: dict[str, list[str]] = defaultdict(list)
            for contact_id in payload.contact_ids:
                contact = state.contacts.get(contact_id)
                if contact:
                    grouped[contact.company].append(contact_id)
            violations = {company: ids for company, ids in grouped.items() if len(ids) > 5}
            if violations:
                raise HTTPException(status_code=400, detail=_err("Max 5 contacts per company exceeded"))
            sent_today = tracker.count_sent_today(payload.user_id)
            if sent_today + len(payload.contact_ids) > payload.daily_cap:
                raise HTTPException(status_code=400, detail=_err("Daily outreach cap exceeded"))
            return _ok({"ok": True, "selected_count": len(payload.contact_ids)})
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("[API] OutreachSelectError -> %s", exc)
            raise HTTPException(status_code=500, detail=_err("Outreach selection failed"))

    @router.post("/outreach/logs")
    def log_outreach(payload: OutreachLogInput) -> dict[str, Any]:
        try:
            row = tracker.record(
                user_id=payload.user_id,
                contact_id=payload.contact_id,
                channel=payload.channel,
                sent=payload.sent,
                replied=payload.replied,
                positive_reply=payload.positive_reply,
            )
            return _ok({"outreach_log": row})
        except Exception as exc:
            logger.exception("[API] OutreachLogError -> %s", exc)
            raise HTTPException(status_code=500, detail=_err("Outreach logging failed"))

    @router.get("/admin/stats")
    def read_stats() -> dict[str, Any]:
        try:
            persisted = database.table_counts()
            return _ok(
                {
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
            )
        except Exception as exc:
            logger.exception("[API] AdminStatsError -> %s", exc)
            raise HTTPException(status_code=500, detail=_err("Failed to read stats"))

    return router
