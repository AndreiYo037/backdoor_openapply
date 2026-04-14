from __future__ import annotations

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from backend.models.internship import Internship

TINYFISH_ENDPOINT = "https://agent.tinyfish.ai/v1/automation/run-sse"
INTERNSG_SEARCH_URL = "https://www.internsg.com/job/?f_p={query}"
INTERNSG_WORDPRESS_URL = "https://www.internsg.com/wp-json/wp/v2/posts"
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MOCK_COMPANY_MARKERS = {"sample internsg company", "demo internsg employer", "sample company", "demo company"}
logger = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 8
MAX_RETRIES = 2
TINYFISH_MAX_QUERY_ATTEMPTS = 3
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


class InternSGScraper:
    """InternSG scraper with parallel TinyFish + fallback sources."""

    def __init__(self, timeout_seconds: int = REQUEST_TIMEOUT_SECONDS, max_stream_seconds: int = 12) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_stream_seconds = max_stream_seconds

    def scrape(self, role_query: str, limit: int = 25) -> list[Internship]:
        queries = self.expand_query(role_query)
        source_rows = self._fetch_rows_parallel(queries, limit=limit)
        merged = self._merge_and_score_rows(self._dedupe_rows(source_rows), role_query)

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

        logger.info(
            "Pipeline source metrics: %s",
            {
                "queries": queries,
                "tinyfishCount": len(source_rows.get("tinyfish", [])),
                "fallbackCount": len(source_rows.get("fallback", [])),
                "mergedCount": len(merged),
                "finalCount": len(internships),
            },
        )
        if not internships:
            raise RuntimeError("No high-quality internships found from available sources.")
        return internships

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

    def _fetch_rows_parallel(self, queries: list[str], limit: int) -> dict[str, list[RawInternshipRow]]:
        results: dict[str, list[RawInternshipRow]] = {"tinyfish": [], "fallback": []}
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(self._fetch_from_tinyfish, queries, limit): "tinyfish",
                executor.submit(self._fetch_from_fallback, queries, limit): "fallback",
            }
            for future in as_completed(futures):
                source = futures[future]
                try:
                    results[source] = future.result()
                except Exception as exc:
                    logger.warning("Source failed: %s error=%s", source, exc)
                    results[source] = []
        return results

    def _fetch_from_tinyfish(self, queries: list[str], limit: int) -> list[RawInternshipRow]:
        api_key = os.getenv("TINYFISH_API_KEY", "").strip()
        if not api_key:
            return []

        rows: list[RawInternshipRow] = []
        start = time.perf_counter()
        for query in queries[:TINYFISH_MAX_QUERY_ATTEMPTS]:
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
        return rows

    def _fetch_from_fallback(self, queries: list[str], limit: int) -> list[RawInternshipRow]:
        rows: list[RawInternshipRow] = []
        for query in queries:
            rows.extend(self._fetch_rows_direct(query, limit))
            rows.extend(self._fetch_rows_wordpress(query, limit))
            if len(rows) >= limit * 3:
                break
        return rows

    def _fetch_rows_direct(self, role_query: str, limit: int) -> list[RawInternshipRow]:
        url = INTERNSG_SEARCH_URL.format(query=quote_plus(role_query))
        response = self._retry_request(method="GET", url=url, headers={"User-Agent": "Mozilla/5.0"})
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("article, .job-listing, .job-item, .grid .border")
        seen: set[tuple[str, str]] = set()
        rows: list[RawInternshipRow] = []
        for card in cards:
            text = " ".join(card.stripped_strings)
            if not text:
                continue
            title = self._extract_title_from_card(card, text)
            company = self._extract_company_from_card(card, text)
            if not title or not company:
                continue
            key = (title.lower(), company.lower())
            if key in seen:
                continue
            seen.add(key)
            email_match = EMAIL_PATTERN.search(text)
            rows.append(
                RawInternshipRow(
                    title=title,
                    company=company,
                    location="Singapore" if "singapore" in text.lower() else "",
                    description=text[:500],
                    requirements=text[:500],
                    job_url=self._extract_job_url_from_card(card),
                    application_email=email_match.group(0) if email_match else None,
                )
            )
            if len(rows) >= limit:
                break
        return rows

    def _fetch_rows_wordpress(self, role_query: str, limit: int) -> list[RawInternshipRow]:
        response = self._retry_request(
            method="GET",
            url=INTERNSG_WORDPRESS_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            params={"search": role_query, "per_page": min(max(limit, 5), 20), "orderby": "date", "order": "desc"},
        )
        if not response:
            return []

        posts = response.json()
        rows: list[RawInternshipRow] = []
        for post in posts:
            raw_title = self._as_string(
                BeautifulSoup(str(post.get("title", {}).get("rendered", "")), "html.parser").get_text(" ", strip=True)
            )
            description = self._as_string(
                BeautifulSoup(str(post.get("excerpt", {}).get("rendered", "")), "html.parser").get_text(" ", strip=True)
            )
            if not raw_title or not description:
                continue
            company, role = self._split_company_role(raw_title)
            if not company or not role:
                continue
            email_match = EMAIL_PATTERN.search(description)
            rows.append(
                RawInternshipRow(
                    title=role,
                    company=company,
                    location="Singapore" if "singapore" in description.lower() else "",
                    description=description[:500],
                    requirements=description[:500],
                    job_url=self._as_string(post.get("link")),
                    application_email=email_match.group(0) if email_match else None,
                )
            )
            if len(rows) >= limit:
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
        merged = source_rows.get("tinyfish", []) + source_rows.get("fallback", [])
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

    def _split_company_role(self, title: str) -> tuple[str, str]:
        cleaned = title.replace("&#8211;", "-").replace("–", "-").replace("—", "-")
        parts = [part.strip() for part in cleaned.split("-") if part.strip()]
        if len(parts) >= 2:
            return parts[0][:120], parts[1][:160]
        return "", ""

    def _extract_title_from_card(self, card: Any, fallback_text: str) -> str:
        for selector in ["h1", "h2", "h3", ".job-title", "a[title]"]:
            node = card.select_one(selector)
            if node:
                text = self._as_string(node.get_text(" ", strip=True))
                if text:
                    return text
        return self._as_string(fallback_text.split("  ")[0][:120])

    def _extract_company_from_card(self, card: Any, fallback_text: str) -> str:
        for selector in [".company", ".job-company", ".text-muted", ".text-gray-500"]:
            node = card.select_one(selector)
            if node:
                text = self._as_string(node.get_text(" ", strip=True))
                if text:
                    return text
        parts = [part.strip() for part in re.split(r"[-|•]", fallback_text) if part.strip()]
        if len(parts) > 1:
            return self._as_string(parts[1][:120])
        return ""

    def _extract_job_url_from_card(self, card: Any) -> str:
        anchor = card.select_one("a[href]")
        if not anchor:
            return ""
        href = self._as_string(anchor.get("href"))
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if href.startswith("/"):
            return f"https://www.internsg.com{href}"
        return ""
