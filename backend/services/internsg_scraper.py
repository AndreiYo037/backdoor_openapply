from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote_plus

import requests

from backend.models.internship import Internship

TINYFISH_ENDPOINT = "https://agent.tinyfish.ai/v1/automation/run-sse"
INTERNSG_SEARCH_URL = "https://www.internsg.com/job/?f_p={query}"
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MOCK_COMPANY_MARKERS = {"sample internsg company", "demo internsg employer", "sample company", "demo company"}
logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 8
MAX_RETRIES = 2
TINYFISH_MAX_QUERY_ATTEMPTS = 3
TINYFISH_MAX_RUNTIME_SECONDS = 25

QUERY_EXPANSION_RULES: list[tuple[tuple[str, ...], list[str]]] = [
    (
        ("machine learning", "ml", "artificial intelligence", "ai"),
        [
            "machine learning intern",
            "ml intern",
            "data science intern",
            "ai intern",
            "machine learning internship singapore",
        ],
    ),
    (
        ("software engineer", "software developer", "developer"),
        [
            "software engineer intern",
            "software developer intern",
            "backend intern",
            "frontend intern",
            "full stack intern singapore",
        ],
    ),
    (
        ("data", "analytics", "analyst"),
        [
            "data analyst intern",
            "data science intern",
            "business analytics intern",
            "data internship singapore",
        ],
    ),
]


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
    """Strict TinyFish-only InternSG scraper."""

    def __init__(self, timeout_seconds: int = REQUEST_TIMEOUT_SECONDS, max_stream_seconds: int = 12) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_stream_seconds = max_stream_seconds

    def scrape(self, role_query: str, limit: int = 25) -> list[Internship]:
        rows = self._fetch_from_tinyfish(self.expand_query(role_query), limit=limit)
        merged = self._merge_and_score_rows(rows, role_query)
        logger.info("Merged internship rows count=%s", len(merged))

        internships: list[Internship] = []
        for row in merged:
            if row.company.lower() in MOCK_COMPANY_MARKERS:
                continue
            has_required_fields = bool(
                row.company.strip() and row.title.strip() and row.description.strip() and row.requirements.strip()
            )
            if not has_required_fields:
                continue
            internships.append(
                Internship(
                    id=f"internsg-{len(internships) + 1}",
                    company=row.company,
                    role=row.title,
                    description=row.description,
                    requirements=row.requirements,
                    application_email=row.application_email,
                    source="InternSG",
                )
            )
            if len(internships) >= limit:
                break

        logger.info("Final returned internship count=%s", len(internships))
        if not internships:
            raise RuntimeError("No valid internships returned by TinyFish for this query.")
        return internships

    def expand_query(self, role: str) -> list[str]:
        lowered = role.lower().strip()
        expanded: list[str] = []
        for keywords, candidates in QUERY_EXPANSION_RULES:
            if any(keyword in lowered for keyword in keywords):
                expanded.extend(candidates)
        if not expanded:
            expanded.extend([f"{lowered} intern", f"{lowered} internship singapore", lowered])

        seen: set[str] = set()
        deduped: list[str] = []
        for query in expanded:
            key = query.strip().lower()
            if key and key not in seen:
                seen.add(key)
                deduped.append(query.strip())
        logger.info("Expanded queries: %s", deduped)
        return deduped

    def _fetch_from_tinyfish(self, expanded_queries: list[str], limit: int) -> list[RawInternshipRow]:
        api_key = os.getenv("TINYFISH_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("TINYFISH_API_KEY is required for strict TinyFish mode.")

        rows: list[RawInternshipRow] = []
        start = time.perf_counter()
        for query in expanded_queries[:TINYFISH_MAX_QUERY_ATTEMPTS]:
            if time.perf_counter() - start >= TINYFISH_MAX_RUNTIME_SECONDS:
                logger.warning("TinyFish global budget exceeded; stopping TinyFish queries.")
                break
            source_url = INTERNSG_SEARCH_URL.format(query=quote_plus(query))
            remaining = max(TINYFISH_MAX_RUNTIME_SECONDS - (time.perf_counter() - start), 1.0)
            effective_timeout = min(self.timeout_seconds, remaining)
            effective_stream_cap = min(self.max_stream_seconds, max(int(remaining), 1))

            response = self._retry_request(
                method="POST",
                url=TINYFISH_ENDPOINT,
                headers={"Content-Type": "application/json", "X-API-Key": api_key},
                json_payload={
                    "url": source_url,
                    "goal": (
                        "Read this InternSG search result page and collect up to "
                        f"{min(limit, 30)} internships. Return JSON array rows with "
                        "job_title, company, description, requirements, application_email."
                    ),
                    "browser_profile": "stealth",
                    "api_integration": "openapply",
                },
                stream=True,
                timeout_override=effective_timeout,
            )
            if not response:
                continue
            events = self._parse_sse_events(response, max_stream_seconds=effective_stream_cap)
            response.close()
            for record in self._extract_listing_records(events):
                parsed = self._row_from_record(record)
                if parsed:
                    rows.append(parsed)
                if len(rows) >= limit * 3:
                    break
            if len(rows) >= limit * 3:
                break

        logger.info("Per-source results: tinyfish=%s", len(rows))
        return rows

    def _retry_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
        stream: bool = False,
        timeout_override: float | None = None,
    ) -> requests.Response | None:
        timeout_seconds = self.timeout_seconds if timeout_override is None else timeout_override
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_payload,
                    timeout=timeout_seconds,
                    stream=stream,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                logger.warning(
                    "Request failed [%s] attempt %s/%s: %s",
                    url,
                    attempt,
                    MAX_RETRIES + 1,
                    exc,
                )
        return None

    def _row_from_record(self, record: dict[str, Any]) -> RawInternshipRow | None:
        title = self._as_string(record.get("job_title")) or self._as_string(record.get("title"))
        company = self._as_string(record.get("company"))
        if not title or not company:
            return None
        description = self._as_string(record.get("description"))
        requirements = self._as_string(record.get("requirements")) or description
        email = self._as_string(record.get("application_email"))
        email_match = EMAIL_PATTERN.search(email or f"{description} {requirements}")
        return RawInternshipRow(
            title=title,
            company=company,
            description=description,
            requirements=requirements,
            application_email=email_match.group(0) if email_match else None,
        )

    def _merge_and_score_rows(self, rows: list[RawInternshipRow], role_query: str) -> list[RawInternshipRow]:
        deduped: dict[tuple[str, str], RawInternshipRow] = {}
        for row in rows:
            key = (row.company.strip().lower(), row.title.strip().lower())
            if key[0] and key[1] and key not in deduped:
                deduped[key] = row

        role_tokens = {token for token in re.findall(r"[a-zA-Z]+", role_query.lower()) if len(token) > 2}

        def score(row: RawInternshipRow) -> float:
            haystack = f"{row.title} {row.description} {row.requirements}".lower()
            hay_tokens = set(re.findall(r"[a-zA-Z]+", haystack))
            keyword_match_score = len(role_tokens & hay_tokens) / max(len(role_tokens), 1)
            title_similarity_score = SequenceMatcher(None, role_query.lower(), row.title.lower()).ratio()
            location_match_boost = 0.2 if "singapore" in haystack else 0.0
            return keyword_match_score + title_similarity_score + location_match_boost

        return sorted(deduped.values(), key=score, reverse=True)

    def _parse_sse_events(self, response: requests.Response, max_stream_seconds: int | None = None) -> list[TinyFishEvent]:
        events: list[TinyFishEvent] = []
        start = time.perf_counter()
        event_name = "message"
        data_lines: list[str] = []
        stream_cap = self.max_stream_seconds if max_stream_seconds is None else max_stream_seconds
        for line in response.iter_lines(decode_unicode=True):
            if time.perf_counter() - start >= stream_cap:
                logger.warning("InternSG SSE parsing reached %ss cap; returning partial results.", stream_cap)
                break
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
