from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

from backend.models.contact import Contact

GOOGLE_SEARCH_ENDPOINT = "https://www.google.com/search"
LINKEDIN_PROFILE_PATTERN = re.compile(r"^https://www\.linkedin\.com/in/[^/?#]+", re.I)
BAD_URL_MARKERS = ("/company/", "/jobs/", "/dir/", "/pub/", "/authwall", "linkedin.com/login")


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_clean_linkedin_url(raw_href: str) -> str | None:
    if not raw_href:
        return None
    href = raw_href.strip()
    if href.startswith("/url?q="):
        href = href.split("/url?q=", 1)[1].split("&", 1)[0]
    href = unquote(href)
    if not LINKEDIN_PROFILE_PATTERN.match(href):
        return None
    lowered = href.lower()
    if any(marker in lowered for marker in BAD_URL_MARKERS):
        return None
    return href.split("?", 1)[0].split("#", 1)[0]


@dataclass
class LinkedInCandidate:
    name: str
    title: str
    snippet: str
    url: str
    score: int


class LinkedInSearchService:
    def __init__(self, timeout_seconds: int = 4, max_runtime_seconds: int = 16) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_runtime_seconds = max_runtime_seconds
        self._cache: dict[str, list[dict[str, str]]] = {}

    def build_queries(self, company: str, role: str) -> list[str]:
        return [
            f'site:linkedin.com/in "{company}" recruiter Singapore',
            f'site:linkedin.com/in "{company}" "talent acquisition" Singapore',
            f'site:linkedin.com/in "{company}" hiring manager Singapore',
            f'site:linkedin.com/in "{company}" "{role}" Singapore',
            f'site:linkedin.com/in "{company}" "{role} engineer" Singapore',
        ]

    def discover_contacts(self, company: str, role: str, limit: int = 5) -> list[Contact]:
        candidates = self._discover_candidates(company, role)
        best = [candidate for candidate in candidates if candidate.score >= 6]
        safe_limit = max(1, min(limit, 5))
        contacts: list[Contact] = []
        for idx, candidate in enumerate(best[:safe_limit], start=1):
            contacts.append(
                Contact(
                    id=f"{re.sub(r'[^a-z0-9]+', '-', company.lower()).strip('-') or 'company'}-{idx}",
                    name=candidate.name,
                    role=candidate.title,
                    company=company,
                    linkedin_url=candidate.url,
                    education="",
                    seniority="manager" if "manager" in candidate.title else "individual_contributor",
                    experience="",
                    activity=0.7,
                )
            )
        return contacts

    def discover_job_contact(self, company: str, role: str) -> tuple[Contact | None, dict[str, object]]:
        candidates = self._discover_candidates(company, role)
        selected = next((candidate for candidate in candidates if candidate.score >= 6), None)
        debug = {
            "company": company,
            "candidates_found": len(candidates),
            "top_score": candidates[0].score if candidates else 0,
            "selected_profile_name": selected.name if selected else None,
        }
        if not selected:
            return None, debug
        contact = Contact(
            id=f"{re.sub(r'[^a-z0-9]+', '-', company.lower()).strip('-') or 'company'}-best",
            name=selected.name,
            role=selected.title,
            company=company,
            linkedin_url=selected.url,
            education="",
            seniority="manager" if "manager" in selected.title else "individual_contributor",
            experience="",
            activity=0.7,
        )
        return contact, debug

    def _discover_candidates(self, company: str, role: str) -> list[LinkedInCandidate]:
        start = time.perf_counter()
        queries = self.build_queries(company, role)
        seen_urls: set[str] = set()
        candidates: list[LinkedInCandidate] = []
        for query in queries[:5]:
            if time.perf_counter() - start >= self.max_runtime_seconds:
                break
            for result in self._search_google(query)[:5]:
                url = _extract_clean_linkedin_url(result.get("href", ""))
                if not url or url in seen_urls:
                    continue
                parsed = self._parse_candidate(company, role, result.get("title", ""), result.get("snippet", ""), url)
                if not parsed:
                    continue
                seen_urls.add(url)
                candidates.append(parsed)
        return sorted(candidates, key=lambda row: row.score, reverse=True)

    def _search_google(self, query: str) -> list[dict[str, str]]:
        if query in self._cache:
            return self._cache[query]
        time.sleep(random.uniform(1.5, 3.5))
        try:
            response = requests.get(
                GOOGLE_SEARCH_ENDPOINT,
                params={"q": query, "num": 5, "hl": "en"},
                timeout=self.timeout_seconds,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            rows: list[dict[str, str]] = []
            for node in soup.select("div.g"):
                anchor = node.select_one("a[href]")
                title_node = node.select_one("h3")
                snippet_node = node.select_one("div.VwiC3b, span.aCOpRe")
                if not anchor or not title_node:
                    continue
                rows.append(
                    {
                        "href": anchor.get("href", ""),
                        "title": _normalize_whitespace(title_node.get_text(" ", strip=True)),
                        "snippet": _normalize_whitespace(snippet_node.get_text(" ", strip=True) if snippet_node else ""),
                    }
                )
            self._cache[query] = rows
            return rows
        except Exception:
            self._cache[query] = []
            return []

    def _parse_candidate(self, company: str, role: str, title_text: str, snippet: str, url: str) -> LinkedInCandidate | None:
        normalized_title = _normalize_whitespace(title_text)
        normalized_snippet = _normalize_whitespace(snippet).lower()
        combined = f"{normalized_title.lower()} {normalized_snippet}"
        if company.lower() not in combined:
            return None
        name = normalized_title.split(" - ", 1)[0].split(" | ", 1)[0].strip() or "Unknown Contact"
        extracted_title = ""
        if " - " in normalized_title:
            parts = [part.strip() for part in normalized_title.split(" - ")]
            if len(parts) > 1:
                extracted_title = parts[1]
        lowered_title = extracted_title.lower() if extracted_title else combined
        score = self.score_candidate(company=company, role=role, profile_title=lowered_title, snippet=normalized_snippet)
        return LinkedInCandidate(name=name, title=extracted_title or "unknown", snippet=normalized_snippet, url=url, score=score)

    def score_candidate(self, company: str, role: str, profile_title: str, snippet: str) -> int:
        profile = f"{profile_title} {snippet}".lower()
        score = 0
        if any(token in profile for token in {"recruiter", "talent", "acquisition"}):
            score += 6
        if "hiring" in profile:
            score += 5
        if "manager" in profile:
            score += 4
        role_tokens = {token for token in re.findall(r"[a-zA-Z]+", role.lower()) if len(token) > 2}
        if role_tokens and any(token in profile for token in role_tokens):
            score += 4
            score += 2
        if company.lower() in profile:
            score += 3
        if any(token in profile for token in {"student", "intern", "graduate"}):
            score -= 3
        return score
