from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace

from backend.api import routes
from backend.models.contact import Contact
from backend.models.internship import Internship


def test_pipeline_contract_and_non_empty_data(monkeypatch) -> None:
    monkeypatch.setattr(routes, "extract_cv_text", lambda _bytes: "machine learning")
    monkeypatch.setattr(routes, "score_internships", lambda _cv, jobs: jobs)

    def fake_scrape_from_search_url(self, search_url: str, role_query: str, limit: int = 25, max_pages: int = 3):  # noqa: ANN001
        jobs = [
            Internship(
                id="intern-1",
                company="Grab",
                role="Machine Learning Intern",
                location="Singapore",
                description="Machine learning internship in Singapore with production model deployment responsibilities and mentorship.",
                requirements="Python, ML",
                job_url="https://www.internsg.com/job/1",
                source="InternSG",
            )
        ]
        meta = SimpleNamespace(input_url=search_url, total_pages_fetched=1, raw_jobs=1, filtered_jobs=1)
        return jobs, meta

    monkeypatch.setattr(routes.InternSGScraper, "scrape_from_search_url", fake_scrape_from_search_url)
    monkeypatch.setattr(
        routes.LinkedInSearchService,
        "discover_job_contact",
        lambda self, company, role: (
            Contact(
                id="c1",
                name="Jane Tan",
                role="Technical Recruiter",
                company=company,
                linkedin_url="https://www.linkedin.com/in/jane-tan-1",
                education="",
                seniority="manager",
                experience="",
                activity=0.7,
            ),
            {"company": company, "candidates_found": 2, "top_score": 9, "selected_profile_name": "Jane Tan"},
        ),
    )

    app = FastAPI()
    app.include_router(routes.build_router())
    client = TestClient(app)

    response = client.post(
        "/api/pipeline/run",
        data={"target_role": "Machine Learning"},
        files={"cv": ("cv.pdf", b"dummy-pdf", "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert isinstance(body["data"], dict)
    assert len(body["data"]["jobs"]) >= 1
    assert len(body["internships"]) >= 1
