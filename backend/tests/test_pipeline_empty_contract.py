from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import routes
from backend.models.internship import Internship


def test_pipeline_returns_strict_empty_contract_when_no_contact_qualifies(monkeypatch) -> None:
    monkeypatch.setattr(routes, "extract_cv_text", lambda _bytes: "machine learning")
    monkeypatch.setattr(routes, "score_internships", lambda _cv, jobs: jobs)

    def fake_scrape(self, role_query: str, limit: int = 25):  # noqa: ANN001
        return [
            Internship(
                id="intern-1",
                company="Grab",
                role="Machine Learning Intern",
                location="Singapore",
                description="Machine learning internship in Singapore with model deployment responsibilities.",
                requirements="Python, ML",
                job_url="https://www.internsg.com/job/1",
                source="InternSG",
            )
        ]

    monkeypatch.setattr(routes.InternSGScraper, "scrape", fake_scrape)
    monkeypatch.setattr(
        routes.LinkedInSearchService,
        "discover_job_contact",
        lambda self, company, role: (
            None,
            {"company": company, "candidates_found": 0, "top_score": 0, "selected_profile_name": None},
        ),
    )
    monkeypatch.setattr(routes.CompanyCareersScraper, "scrape", lambda self, role_query, limit=10: [])

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
    assert body["internships"] == []
    assert body["reason"] == "No internships met high-confidence LinkedIn contact requirement"
    assert set(body["debug"].keys()) == {"raw_jobs", "filtered_jobs", "linkedin_candidates", "qualified_contacts"}
