from __future__ import annotations

import json
import re
import time
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

from backend.models.contact import Contact

DUCKDUCKGO_HTML_ENDPOINT = "https://duckduckgo.com/html/"
BING_SEARCH_ENDPOINT = "https://www.bing.com/search"
LINKEDIN_PROFILE_PATTERN = re.compile(r"^https?://([a-z]{2,3}\.)?linkedin\.com/in/[^/?#]+", re.I)
ROLE_HINT_KEYWORDS = {
    "recruiter": {"recruit", "talent", "hiring", "sourcing", "acquisition"},
    "engineering": {"engineer", "developer", "software", "frontend", "backend", "full stack", "tech"},
    "product": {"product", "pm"},
}


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_clean_linkedin_url(raw_href: str) -> str | None:
    if not raw_href:
        return None
    href = raw_href.strip()
    if href.startswith("//"):
        href = f"https:{href}"
    if href.startswith("/"):
        return None

    parsed = urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path == "/l/":
        query_match = re.search(r"[?&]uddg=([^&]+)", href)
        if query_match:
            href = unquote(query_match.group(1))

    if LINKEDIN_PROFILE_PATTERN.match(href):
        return href.split("?", 1)[0].split("#", 1)[0]
    return None


def _derive_name_from_slug(profile_url: str) -> str:
    slug = profile_url.rstrip("/").split("/in/")[-1]
    slug = re.sub(r"[^a-zA-Z\- ]", " ", slug)
    parts = [part for part in re.split(r"[-\s]+", slug) if part]
    cleaned: list[str] = []
    for part in parts:
        if len(part) <= 1 or part.isdigit():
            continue
        if part.lower() in {"linkedin", "profile"}:
            continue
        cleaned.append(part.capitalize())
    if len(cleaned) >= 2:
        return f"{cleaned[0]} {cleaned[1]}"
    if cleaned:
        return cleaned[0]
    return "Unknown Contact"


def _extract_name_from_title(raw_title: str, fallback_url: str) -> str:
    title = _normalize_whitespace(raw_title)
    if not title:
        return _derive_name_from_slug(fallback_url)
    if " - " in title:
        return title.split(" - ", 1)[0].strip()
    if " | " in title:
        return title.split(" | ", 1)[0].strip()
    return _derive_name_from_slug(fallback_url)


def _pick_contact_role(title_text: str, snippet: str, requested_role: str) -> tuple[str, str]:
    haystack = f"{title_text} {snippet}".lower()
    if any(keyword in haystack for keyword in ROLE_HINT_KEYWORDS["recruiter"]):
        return ("Talent Acquisition Partner", "manager")
    if any(keyword in haystack for keyword in ROLE_HINT_KEYWORDS["product"]):
        return ("Product Manager", "manager")
    if any(keyword in haystack for keyword in ROLE_HINT_KEYWORDS["engineering"]):
        return ("Software Engineer", "individual_contributor")
    if "manager" in haystack or "head of" in haystack or "lead" in haystack:
        return ("Hiring Manager", "manager")
    return (f"{requested_role} Recruiter", "manager")


def _role_alignment_score(role: str, snippet: str, requested_role: str) -> float:
    requested_tokens = {token for token in requested_role.lower().split() if token}
    haystack_tokens = set(re.findall(r"[a-zA-Z]+", f"{role} {snippet}".lower()))
    overlap = len(requested_tokens & haystack_tokens) / max(len(requested_tokens), 1)
    recruiter_bonus = 0.2 if any(word in haystack_tokens for word in {"recruiter", "talent", "hiring"}) else 0.0
    return min(overlap + recruiter_bonus, 1.0)


class LinkedInSearchService:
    """Discover likely LinkedIn profiles from public web search results."""

    def __init__(self, timeout_seconds: int = 2, max_runtime_seconds: int = 3) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_runtime_seconds = max_runtime_seconds

    def discover_contacts(self, company: str, role: str, limit: int = 12) -> list[Contact]:
        start = time.perf_counter()
        safe_limit = max(1, min(limit, 20))
        queries = [
            f'"{company}" recruiter linkedin',
            f'"{company}" talent acquisition linkedin',
            f'"{company}" machine learning linkedin',
            f'"{company}" data science linkedin',
        ]

        seen_urls: set[str] = set()
        candidates: list[tuple[float, Contact]] = []
        company_slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-") or "company"

        for query in queries:
            if time.perf_counter() - start >= self.max_runtime_seconds:
                break
            remaining = max(self.max_runtime_seconds - (time.perf_counter() - start), 0.5)
            timeout = min(self.timeout_seconds, remaining)
            for result in self._search_duckduckgo(query, timeout):
                if self._try_add_candidate(result, company, role, company_slug, seen_urls, candidates):
                    if len(candidates) >= safe_limit * 2:
                        break
            if len(candidates) >= safe_limit * 2:
                break

            if time.perf_counter() - start >= self.max_runtime_seconds:
                break
            remaining = max(self.max_runtime_seconds - (time.perf_counter() - start), 0.5)
            timeout = min(self.timeout_seconds, remaining)
            for result in self._search_bing(query, timeout):
                if self._try_add_candidate(result, company, role, company_slug, seen_urls, candidates):
                    if len(candidates) >= safe_limit * 2:
                        break
            if len(candidates) >= safe_limit * 2:
                break

        if not candidates:
            # Return an empty list instead of made-up profile URLs.
            return []

        ranked = sorted(candidates, key=lambda row: row[0], reverse=True)
        return [contact for _, contact in ranked[:safe_limit]]

    def _search_duckduckgo(self, query: str, timeout_seconds: float) -> list[dict[str, str]]:
        try:
            response = requests.get(
                DUCKDUCKGO_HTML_ENDPOINT,
                params={"q": query},
                timeout=timeout_seconds,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            result_nodes = soup.select("a.result__a")
            rows: list[dict[str, str]] = []
            for node in result_nodes:
                wrapper = node.find_parent("div", class_="result")
                snippet_node = wrapper.select_one(".result__snippet") if wrapper else None
                snippet = _normalize_whitespace(snippet_node.get_text(" ", strip=True) if snippet_node else "")
                title_text = _normalize_whitespace(node.get_text(" ", strip=True))
                rows.append({"href": node.get("href", ""), "title": title_text, "snippet": snippet})
            return rows
        except Exception:
            return []

    def _search_bing(self, query: str, timeout_seconds: float) -> list[dict[str, str]]:
        try:
            response = requests.get(
                BING_SEARCH_ENDPOINT,
                params={"q": query},
                timeout=timeout_seconds,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            rows: list[dict[str, str]] = []
            for node in soup.select("li.b_algo"):
                anchor = node.select_one("h2 a")
                if not anchor:
                    continue
                title_text = _normalize_whitespace(anchor.get_text(" ", strip=True))
                snippet_node = node.select_one(".b_caption p")
                snippet = _normalize_whitespace(snippet_node.get_text(" ", strip=True) if snippet_node else "")
                rows.append({"href": anchor.get("href", ""), "title": title_text, "snippet": snippet})
            return rows
        except Exception:
            return []

    def _try_add_candidate(
        self,
        result_row: dict[str, str],
        company: str,
        role: str,
        company_slug: str,
        seen_urls: set[str],
        candidates: list[tuple[float, Contact]],
    ) -> bool:
        url = _extract_clean_linkedin_url(result_row.get("href", ""))
        if not url or url in seen_urls:
            return False
        lowered_url = url.lower()
        if any(token in lowered_url for token in ("/company/", "/jobs/", "/authwall", "linkedin.com/signup")):
            return False

        title_text = result_row.get("title", "")
        snippet = result_row.get("snippet", "")
        if company.lower() not in f"{title_text} {snippet}".lower():
            return False
        relevance_text = f"{title_text} {snippet}".lower()
        relevant_markers = {
            "recruiter",
            "talent acquisition",
            "hiring",
            "machine learning",
            "data science",
            "ai",
            "engineer",
        }
        if not any(marker in relevance_text for marker in relevant_markers):
            return False

        inferred_name = _extract_name_from_title(title_text, url)
        inferred_role, seniority = _pick_contact_role(title_text, snippet, role)
        relevance = _role_alignment_score(inferred_role, snippet, role)
        years = 2 + int(relevance * 8)
        activity = min(0.45 + (0.5 * relevance), 0.95)
        role_slug = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-") or "role"

        seen_urls.add(url)
        candidates.append(
            (
                relevance,
                Contact(
                    id=f"{company_slug}-{role_slug}-{len(seen_urls)}",
                    name=inferred_name,
                    role=inferred_role,
                    company=company,
                    linkedin_url=url,
                    education="",
                    seniority=seniority,
                    experience=f"{years} years",
                    activity=activity,
                ),
            )
        )
        return True
