from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

import requests

from backend.models.internship import Internship

TINYFISH_ENDPOINT = "https://agent.tinyfish.ai/v1/automation/run-sse"
INTERNSG_SEARCH_URL = "https://www.internsg.com/jobs/?search={query}"
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MOCK_COMPANY_MARKERS = {"sample internsg company", "demo internsg employer", "sample company", "demo company"}
logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 8
MAX_RETRIES = 2
TINYFISH_MAX_RUNTIME_SECONDS = 18


@dataclass
class TinyFishEvent:
    event: str
    data: Any


@dataclass
class RawInternshipRow:
    title: str
    company: str
    location: str
    description: str
    requirements: str
    job_url: str
    application_email: str | None


@dataclass
class ScrapeMeta:
    input_url: str
    total_pages_fetched: int
    raw_jobs: int
    filtered_jobs: int


class InternSGScraper:
    """InternSG scraper from explicit user-provided search URL."""

    def __init__(self, timeout_seconds: int = REQUEST_TIMEOUT_SECONDS, max_stream_seconds: int = 12) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_stream_seconds = max_stream_seconds

    def scrape(self, role_query: str, limit: int = 25) -> list[Internship]:
        fallback_url = INTERNSG_SEARCH_URL.format(query=quote_plus(role_query))
        internships, _meta = self.scrape_from_search_url(fallback_url, role_query=role_query, limit=limit)
        return internships

    def scrape_from_search_url(
        self,
        search_url: str,
        role_query: str,
        limit: int = 25,
        max_pages: int = 3,
    ) -> tuple[list[Internship], ScrapeMeta]:
        if not self.validate_search_url(search_url):
            raise ValueError("Invalid InternSG URL. Expected internsg.com/jobs search URL.")

        page_urls = self.build_paginated_urls(search_url, max_pages=max_pages)
        rows = self._fetch_from_tinyfish_urls(page_urls, limit=limit)
        merged = self._merge_and_score_rows(self._dedupe_rows(rows), role_query)

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
                    location=row.location,
                    description=row.description,
                    requirements=row.requirements,
                    job_url=row.job_url,
                    application_email=row.application_email,
                    source="InternSG",
                )
            )
            if len(internships) >= limit:
                break

        meta = ScrapeMeta(
            input_url=search_url,
            total_pages_fetched=len(page_urls),
            raw_jobs=len(rows),
            filtered_jobs=len(internships),
        )
        logger.info(
            "Pipeline source metrics: %s",
            {
                "input_url": search_url,
                "total_pages_fetched": len(page_urls),
                "tinyfishCount": len(rows),
                "fallbackCount": 0,
                "mergedCount": len(merged),
                "finalCount": len(internships),
            },
        )
        return internships, meta

    def expand_query(self, role: str) -> list[str]:
        lowered = role.lower().strip()
        if "machine learning" in lowered:
            return [
                "machine learning intern singapore",
                "ml intern singapore",
                "ai intern singapore",
                "data science intern singapore",
                "machine learning internship singapore",
                "ai machine learning intern singapore",
            ]
        return [
            f"{role} intern singapore",
            f"{role} internship singapore",
            f"{role} intern",
            f"{role} internship",
            f"{role} intern asia",
            f"{role} internship asia",
        ]

    def validate_search_url(self, search_url: str) -> bool:
        try:
            parsed = urlparse(search_url)
        except Exception:
            return False
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        return ("internsg.com" in host) and ("/jobs" in path)

    def build_paginated_urls(self, search_url: str, max_pages: int = 3) -> list[str]:
        parsed = urlparse(search_url)
        query_pairs = dict(parse_qsl(parsed.query, keep_blank_values=True))
        urls: list[str] = []
        for page in range(1, max_pages + 1):
            page_query = dict(query_pairs)
            if page == 1:
                page_query.pop("page", None)
            else:
                page_query["page"] = str(page)
            rebuilt = parsed._replace(query=urlencode(page_query))
            urls.append(urlunparse(rebuilt))
        return urls

    def _fetch_from_tinyfish_urls(self, urls: list[str], limit: int) -> list[RawInternshipRow]:
        api_key = os.getenv("TINYFISH_API_KEY", "").strip()
        if not api_key:
            return []

        rows: list[RawInternshipRow] = []
        start = time.perf_counter()
        for source_url in urls:
            if time.perf_counter() - start >= TINYFISH_MAX_RUNTIME_SECONDS:
                logger.warning("TinyFish global budget exceeded; stopping TinyFish queries.")
                break
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
                        "Extract internships from this exact InternSG listing page only. "
                        "Do not navigate elsewhere. Collect up to "
                        f"{min(limit, 30)} internships. Return JSON array rows with "
                        "job_title, company, location, description, requirements, application_email, job_url."
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
            location=self._as_string(record.get("location")),
            description=description,
            requirements=requirements,
            job_url=self._as_string(record.get("job_url") or record.get("url") or record.get("link")),
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

        ranked = sorted(deduped.values(), key=score, reverse=True)
        return [row for row in ranked if self._is_strict_internship_row(row, role_query)]

    def _dedupe_rows(self, source_rows: dict[str, list[RawInternshipRow]]) -> list[RawInternshipRow]:
        merged = source_rows if isinstance(source_rows, list) else []
        seen: set[str] = set()
        result: list[RawInternshipRow] = []
        for item in merged:
            key = f"{item.company}-{item.title}".lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def _is_strict_internship_row(self, row: RawInternshipRow, role_query: str) -> bool:
        title = row.title.strip().lower()
        if not row.company.strip() or not title:
            return False
        if "intern" not in title and "internship" not in title:
            return False
        if len(row.description.strip()) < 60:
            return False
        role_tokens = {
            token for token in re.findall(r"[a-zA-Z]+", role_query.lower()) if token not in {"intern", "internship"}
        }
        haystack = f"{row.title} {row.description} {row.requirements}".lower()
        if role_tokens and not any(token in haystack for token in role_tokens):
            return False
        return True

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

