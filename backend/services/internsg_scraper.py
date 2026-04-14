from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

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

    def __init__(self, timeout_seconds: int = 12, max_stream_seconds: int = 25) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_stream_seconds = max_stream_seconds

    def scrape(self, role_query: str, limit: int = 25) -> list[Internship]:
        internships: list[Internship] = []
        for row in self._fetch_rows(role_query, limit=limit):
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
            # Stop early once enough quality internships are collected.
            if len(internships) >= limit:
                break
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
            logger.warning("TINYFISH_API_KEY missing. Falling back to direct InternSG scraping.")
            direct_rows = list(self._fetch_rows_direct(role_query, limit))
            if direct_rows:
                yield from direct_rows
            else:
                logger.warning("Direct InternSG scraping returned no rows; using WordPress post fallback.")
                yield from self._fetch_rows_wordpress(role_query, limit)
            return

        url = INTERNSG_SEARCH_URL.format(query=quote_plus(role_query))
        try:
            logger.info("Using TinyFish as primary InternSG source.")
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
                timeout=self.timeout_seconds,
                stream=True,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("TinyFish scrape failed (%s). Falling back to direct scraping.", exc)
            direct_rows = list(self._fetch_rows_direct(role_query, limit))
            if direct_rows:
                yield from direct_rows
            else:
                logger.warning("Direct InternSG scraping returned no rows; using WordPress post fallback.")
                yield from self._fetch_rows_wordpress(role_query, limit)
            return
        events = self._parse_sse_events(response)
        response.close()
        records = self._extract_listing_records(events)[:limit]
        if not records:
            logger.warning("TinyFish returned no internship rows; falling back to WordPress post feed.")
            yield from self._fetch_rows_wordpress(role_query, limit)
            return
        logger.info("TinyFish produced %s internship rows before filtering.", len(records))

        for idx, record in enumerate(records):
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

    def _fetch_rows_direct(self, role_query: str, limit: int) -> Iterable[RawInternshipRow]:
        url = INTERNSG_SEARCH_URL.format(query=quote_plus(role_query))
        try:
            response = requests.get(
                url,
                timeout=self.timeout_seconds,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError("InternSG direct scraping failed. Try again later.") from exc

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("article, .job-listing, .job-item, .grid .border")
        seen: set[tuple[str, str]] = set()

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
            description = text[:500]
            requirements = description
            yield RawInternshipRow(
                title=title,
                company=company,
                description=description,
                requirements=requirements,
                application_email=email_match.group(0) if email_match else None,
            )
            if len(seen) >= limit:
                break

    def _fetch_rows_wordpress(self, role_query: str, limit: int) -> Iterable[RawInternshipRow]:
        api_url = "https://www.internsg.com/wp-json/wp/v2/posts"
        try:
            response = requests.get(
                api_url,
                params={"search": role_query, "per_page": min(max(limit, 5), 20), "orderby": "date", "order": "desc"},
                timeout=self.timeout_seconds,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            posts = response.json()
        except requests.RequestException as exc:
            raise RuntimeError("InternSG fallback feed failed. Try again later.") from exc

        role_tokens = {token for token in re.findall(r"[a-zA-Z]+", role_query.lower()) if len(token) > 2}
        seen: set[tuple[str, str]] = set()
        for post in posts:
            raw_title = self._as_string(BeautifulSoup(str(post.get("title", {}).get("rendered", "")), "html.parser").get_text(" ", strip=True))
            description = self._as_string(
                BeautifulSoup(str(post.get("excerpt", {}).get("rendered", "")), "html.parser").get_text(" ", strip=True)
            )
            if not raw_title or not description:
                continue

            lowered = f"{raw_title} {description}".lower()
            overlap = len(role_tokens & set(re.findall(r"[a-zA-Z]+", lowered)))
            if role_tokens and overlap == 0:
                continue

            company, role = self._split_company_role(raw_title)
            if not company or not role:
                continue
            key = (company.lower(), role.lower())
            if key in seen:
                continue
            seen.add(key)

            email_match = EMAIL_PATTERN.search(description)
            yield RawInternshipRow(
                title=role,
                company=company,
                description=description[:500],
                requirements=description[:500],
                application_email=email_match.group(0) if email_match else None,
            )
            if len(seen) >= limit:
                break

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

    def _parse_sse_events(self, response: requests.Response) -> list[TinyFishEvent]:
        import time

        events: list[TinyFishEvent] = []
        start = time.perf_counter()
        event_name = "message"
        data_lines: list[str] = []
        for line in response.iter_lines(decode_unicode=True):
            if time.perf_counter() - start >= self.max_stream_seconds:
                logger.warning("InternSG SSE parsing reached %ss cap; returning partial results.", self.max_stream_seconds)
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
