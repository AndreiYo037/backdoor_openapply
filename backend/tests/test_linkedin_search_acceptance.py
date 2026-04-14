from backend.services.linkedin_search import LinkedInSearchService, _extract_clean_linkedin_url


def test_build_queries_is_exactly_five() -> None:
    service = LinkedInSearchService()
    queries = service.build_queries("Grab", "machine learning")
    assert queries == [
        'site:linkedin.com/in "Grab" recruiter Singapore',
        'site:linkedin.com/in "Grab" "talent acquisition" Singapore',
        'site:linkedin.com/in "Grab" hiring manager Singapore',
        'site:linkedin.com/in "Grab" "machine learning" Singapore',
        'site:linkedin.com/in "Grab" "machine learning engineer" Singapore',
    ]


def test_url_filter_accepts_only_linkedin_people_profiles() -> None:
    assert _extract_clean_linkedin_url("https://www.linkedin.com/in/jane-doe-123") == (
        "https://www.linkedin.com/in/jane-doe-123"
    )
    assert _extract_clean_linkedin_url("https://www.linkedin.com/company/grab") is None
    assert _extract_clean_linkedin_url("https://www.linkedin.com/jobs/view/1") is None
    assert _extract_clean_linkedin_url("https://www.linkedin.com/pub/john/12/34") is None


def test_candidate_threshold_acceptance() -> None:
    service = LinkedInSearchService()
    strong = service.score_candidate(
        company="Grab",
        role="machine learning",
        profile_title="technical recruiter",
        snippet="grab singapore talent acquisition hiring",
    )
    weak = service.score_candidate(
        company="Grab",
        role="machine learning",
        profile_title="student ambassador",
        snippet="graduate intern community",
    )
    assert strong >= 6
    assert weak < 6
