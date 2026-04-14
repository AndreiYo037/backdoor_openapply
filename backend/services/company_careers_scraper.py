from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

COMPANY_CAREER_URLS: dict[str, str] = {
    "Grab": "https://www.grab.careers/en/jobs/",
    "Shopee": "https://careers.shopee.sg/jobs/",
    "TikTok": "https://careers.tiktok.com/",
    "DBS": "https://www.dbs.com/careers/default.page",
    "OCBC": "https://www.ocbc.com/group/careers",
    "UOB": "https://www.uobgroup.com/uobgroup/careers/index.page",
    "GovTech": "https://www.tech.gov.sg/careers/",
    "SEA Group": "https://www.sea.com/careers",
}


@dataclass
class CareerJobRow:
    title: str
    company: str
    location: str
    description: str
    job_url: str


class CompanyCareersScraper:
    def __init__(self, timeout_seconds: int = 8) -> None:
        self.timeout_seconds = timeout_seconds

    def scrape(self, role_query: str, limit: int = 10) -> list[CareerJobRow]:
        jobs: list[CareerJobRow] = []
        role_tokens = {token for token in re.findall(r"[a-zA-Z]+", role_query.lower()) if len(token) > 2}
        for company, url in COMPANY_CAREER_URLS.items():
            if len(jobs) >= limit:
                break
            rows = self._fetch_company_jobs(company, url, role_tokens)
            for row in rows:
                jobs.append(row)
                if len(jobs) >= limit:
                    break
        return jobs

    def _fetch_company_jobs(self, company: str, url: str, role_tokens: set[str]) -> list[CareerJobRow]:
        try:
            response = requests.get(url, timeout=self.timeout_seconds, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Career page fetch failed company=%s url=%s error=%s", company, url, exc)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        rows: list[CareerJobRow] = []
        for anchor in soup.select("a[href]"):
            text = anchor.get_text(" ", strip=True)
            lowered = text.lower()
            if "intern" not in lowered and "internship" not in lowered:
                continue
            if role_tokens and not any(token in lowered for token in role_tokens):
                continue
            href = anchor.get("href", "")
            job_url = href if href.startswith("http") else f"{url.rstrip('/')}/{href.lstrip('/')}"
            body = f"{text} {anchor.get('title', '')}".strip()
            location = "Singapore" if "singapore" in lowered else "Asia" if "asia" in lowered else ""
            rows.append(
                CareerJobRow(
                    title=text[:160],
                    company=company,
                    location=location,
                    description=body[:500],
                    job_url=job_url,
                )
            )
        return rows
