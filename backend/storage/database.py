from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PersistentDatabase:
    """SQLite-backed persistence for required production tables."""

    def __init__(self, db_path: str = "backend/data/app.db") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        logger.info("[Storage] Connect -> Input: db_path=%s", self.db_path)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        logger.info("[Storage] Connect -> Output: ok")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    university TEXT,
                    cv_url TEXT
                );

                CREATE TABLE IF NOT EXISTS internships (
                    id TEXT PRIMARY KEY,
                    company TEXT NOT NULL,
                    role TEXT NOT NULL,
                    description TEXT,
                    requirements TEXT,
                    application_email TEXT,
                    source TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS contacts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    company TEXT NOT NULL,
                    linkedin_url TEXT NOT NULL,
                    education TEXT,
                    seniority TEXT
                );

                CREATE TABLE IF NOT EXISTS emails (
                    id TEXT PRIMARY KEY,
                    contact_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    FOREIGN KEY(contact_id) REFERENCES contacts(id)
                );

                CREATE TABLE IF NOT EXISTS contact_scores (
                    contact_id TEXT PRIMARY KEY,
                    role_match REAL NOT NULL,
                    affinity REAL NOT NULL,
                    seniority REAL NOT NULL,
                    activity REAL NOT NULL,
                    email_confidence REAL NOT NULL,
                    reachability_score REAL NOT NULL,
                    final_score REAL NOT NULL,
                    FOREIGN KEY(contact_id) REFERENCES contacts(id)
                );

                CREATE TABLE IF NOT EXISTS outreach_logs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    contact_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    sent INTEGER NOT NULL,
                    replied INTEGER NOT NULL,
                    positive_reply INTEGER NOT NULL,
                    sent_date TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(contact_id) REFERENCES contacts(id)
                );
                """
            )
        logger.info("[Storage] InitSchema -> Output: ready")

    def upsert_user(self, user: dict[str, Any]) -> None:
        logger.info("[Storage] UpsertUser -> Input: id=%s", user.get("id"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (id, name, email, university, cv_url)
                VALUES (:id, :name, :email, :university, :cv_url)
                ON CONFLICT(id) DO UPDATE SET
                  name = excluded.name,
                  email = excluded.email,
                  university = excluded.university,
                  cv_url = excluded.cv_url
                """,
                user,
            )
        logger.info("[Storage] UpsertUser -> Output: ok")

    def upsert_internship(self, internship: dict[str, Any]) -> None:
        logger.info("[Storage] UpsertInternship -> Input: id=%s", internship.get("id"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO internships (id, company, role, description, requirements, application_email, source)
                VALUES (:id, :company, :role, :description, :requirements, :application_email, :source)
                ON CONFLICT(id) DO UPDATE SET
                  company = excluded.company,
                  role = excluded.role,
                  description = excluded.description,
                  requirements = excluded.requirements,
                  application_email = excluded.application_email,
                  source = excluded.source
                """,
                internship,
            )
        logger.info("[Storage] UpsertInternship -> Output: ok")

    def upsert_contact(self, contact: dict[str, Any]) -> None:
        logger.info("[Storage] UpsertContact -> Input: id=%s", contact.get("id"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO contacts (id, name, role, company, linkedin_url, education, seniority)
                VALUES (:id, :name, :role, :company, :linkedin_url, :education, :seniority)
                ON CONFLICT(id) DO UPDATE SET
                  name = excluded.name,
                  role = excluded.role,
                  company = excluded.company,
                  linkedin_url = excluded.linkedin_url,
                  education = excluded.education,
                  seniority = excluded.seniority
                """,
                contact,
            )
        logger.info("[Storage] UpsertContact -> Output: ok")

    def upsert_email(self, email_row: dict[str, Any]) -> None:
        logger.info("[Storage] UpsertEmail -> Input: id=%s", email_row.get("id"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO emails (id, contact_id, email, confidence_score)
                VALUES (:id, :contact_id, :email, :confidence_score)
                ON CONFLICT(id) DO UPDATE SET
                  contact_id = excluded.contact_id,
                  email = excluded.email,
                  confidence_score = excluded.confidence_score
                """,
                email_row,
            )
        logger.info("[Storage] UpsertEmail -> Output: ok")

    def upsert_contact_score(self, score_row: dict[str, Any]) -> None:
        logger.info("[Storage] UpsertContactScore -> Input: contact_id=%s", score_row.get("contact_id"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO contact_scores
                  (contact_id, role_match, affinity, seniority, activity, email_confidence, reachability_score, final_score)
                VALUES
                  (:contact_id, :role_match, :affinity, :seniority, :activity, :email_confidence, :reachability_score, :final_score)
                ON CONFLICT(contact_id) DO UPDATE SET
                  role_match = excluded.role_match,
                  affinity = excluded.affinity,
                  seniority = excluded.seniority,
                  activity = excluded.activity,
                  email_confidence = excluded.email_confidence,
                  reachability_score = excluded.reachability_score,
                  final_score = excluded.final_score
                """,
                score_row,
            )
        logger.info("[Storage] UpsertContactScore -> Output: ok")

    def insert_outreach_log(self, row: dict[str, Any]) -> None:
        logger.info("[Storage] InsertOutreachLog -> Input: id=%s", row.get("id"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO outreach_logs
                  (id, user_id, contact_id, channel, sent, replied, positive_reply, sent_date)
                VALUES
                  (:id, :user_id, :contact_id, :channel, :sent, :replied, :positive_reply, :sent_date)
                """,
                row,
            )
        logger.info("[Storage] InsertOutreachLog -> Output: ok")

    def count_sent_today(self, user_id: str, iso_date: str) -> int:
        logger.info("[Storage] CountSentToday -> Input: user_id=%s date=%s", user_id, iso_date)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM outreach_logs
                WHERE user_id = ? AND sent = 1 AND sent_date = ?
                """,
                (user_id, iso_date),
            ).fetchone()
        total = int(row["total"]) if row else 0
        logger.info("[Storage] CountSentToday -> Output: total=%s", total)
        return total

    def table_counts(self) -> dict[str, int]:
        table_names = [
            "users",
            "internships",
            "contacts",
            "emails",
            "contact_scores",
            "outreach_logs",
        ]
        counts: dict[str, int] = {}
        with self._connect() as conn:
            for table in table_names:
                row = conn.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
                counts[table] = int(row["total"]) if row else 0
        logger.info("[Storage] TableCounts -> Output: %s", counts)
        return counts

    def health_check(self) -> bool:
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT 1 AS ok").fetchone()
            ok = bool(row and int(row["ok"]) == 1)
            logger.info("[Storage] HealthCheck -> Output: ok=%s", ok)
            return ok
        except Exception as exc:
            logger.exception("[Storage] HealthCheck -> Error: %s", exc)
            return False
