from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import quote_plus

import requests

from backend.models.internship import Internship

TINYFISH_ENDPOINT = "https://agent.tinyfish.ai/v1/automation/run-sse"
INTERNSG_SEARCH_URL = "https://www.internsg.com/job/?f_p={query}"
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MOCK_COMPANY_MARKERS = {"sample internsg company", "demo internsg employer", "sample company", "demo company"}
logger = logging.getLogger(__name__)


@dataclass
class TinyFishEvent:
    event: str
    data: Any


@dataclass
class RawInternshipRow:
    title: str
    company: str
    description: str
    requirements: str
    application_email: str | None


class InternSGScraper:
    """TinyFish-powered InternSG scraper (non-restricted source only)."""

    def __init__(self, timeout_seconds: int = 15) -> None:
        self.timeout_seconds = timeout_seconds

    def scrape(self, role_query: str, limit: int = 25) -> list[Internship]:
        rows = list(self._fetch_rows(role_query, limit=limit))
        internships: list[Internship] = []
        for idx, row in enumerate(rows, start=1):
            if row.company.lower() in MOCK_COMPANY_MARKERS:
                continue
            internships.append(
                Internship(
                    id=f"internsg-{idx}",
                    company=row.company,
                    role=row.title,
                    description=row.description,
                    requirements=row.requirements,
                    application_email=row.application_email,
                    source="InternSG",
                )
            )
        logger.info("InternSG scrape complete: query='%s' count=%s", role_query, len(internships))
        if internships:
            sample = internships[0]
            logger.info(
                "InternSG sample job: company='%s' role='%s' has_email=%s",
                sample.company,
                sample.role,
                bool(sample.application_email),
            )
        return internships

    def _fetch_rows(self, role_query: str, limit: int) -> Iterable[RawInternshipRow]:
        api_key = os.getenv("TINYFISH_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("TINYFISH_API_KEY is required for InternSG discovery.")

        url = INTERNSG_SEARCH_URL.format(query=quote_plus(role_query))
        response = requests.post(
            TINYFISH_ENDPOINT,
            headers={"Content-Type": "application/json", "X-API-Key": api_key},
            json={
                "url": url,
                "goal": (
                    "Read this InternSG search result page and collect up to "
                    f"{min(limit, 30)} internships. Return JSON array rows with "
                    "job_title, company, description, requirements, application_email."
                ),
                "browser_profile": "stealth",
                "api_integration": "openapply",
            },
            timeout=self.timeout_seconds * 2,
            stream=True,
        )
        response.raise_for_status()
        events = self._parse_sse_events(response)
        for idx, record in enumerate(self._extract_listing_records(events)[:limit]):
            title = self._as_string(record.get("job_title")) or self._as_string(record.get("title"))
            company = self._as_string(record.get("company"))
            if not title or not company:
                continue
            description = self._as_string(record.get("description"))
            requirements = self._as_string(record.get("requirements")) or description
            email = self._as_string(record.get("application_email"))
            email_match = EMAIL_PATTERN.search(email or f"{description} {requirements}")
            yield RawInternshipRow(
                title=title,
                company=company,
                description=description,
                requirements=requirements,
                application_email=email_match.group(0) if email_match else None,
            )

    def _parse_sse_events(self, response: requests.Response) -> list[TinyFishEvent]:
        events: list[TinyFishEvent] = []
        event_name = "message"
        data_lines: list[str] = []
        for line in response.iter_lines(decode_unicode=True):
            if line is None:
                continue
            clean = line.strip()
            if not clean:
                if data_lines:
                    raw = "\n".join(data_lines).strip()
                    events.append(TinyFishEvent(event=event_name, data=self._parse_json(raw)))
                event_name = "message"
                data_lines = []
                continue
            if clean.startswith("event:"):
                event_name = clean.split(":", 1)[1].strip() or "message"
            elif clean.startswith("data:"):
                data_lines.append(clean.split(":", 1)[1].strip())
        if data_lines:
            raw = "\n".join(data_lines).strip()
            events.append(TinyFishEvent(event=event_name, data=self._parse_json(raw)))
        return events

    def _extract_listing_records(self, events: list[TinyFishEvent]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for event in events:
            roots = [event.data]
            if isinstance(event.data, dict):
                roots.extend(
                    [event.data.get("result"), event.data.get("resultJson"), event.data.get("output")]
                )
            for root in roots:
                candidates.extend(self._walk_for_rows(root))
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for row in candidates:
            key = (
                self._as_string(row.get("job_title") or row.get("title")).lower(),
                self._as_string(row.get("company")).lower(),
            )
            if key[0] and key[1] and key not in seen:
                seen.add(key)
                deduped.append(row)
        return deduped

    def _walk_for_rows(self, value: Any) -> list[dict[str, Any]]:
        if isinstance(value, str):
            parsed = self._parse_json(value)
            if parsed != value:
                return self._walk_for_rows(parsed)
            return []
        if isinstance(value, list):
            rows: list[dict[str, Any]] = []
            for item in value:
                rows.extend(self._walk_for_rows(item))
            return rows
        if isinstance(value, dict):
            has_job = bool(self._as_string(value.get("job_title") or value.get("title")))
            has_company = bool(self._as_string(value.get("company")))
            if has_job and has_company:
                return [value]
            rows: list[dict[str, Any]] = []
            for nested in value.values():
                rows.extend(self._walk_for_rows(nested))
            return rows
        return []

    def _parse_json(self, raw: str) -> Any:
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def _as_string(self, value: Any) -> str:
        return value.strip() if isinstance(value, str) else ""
