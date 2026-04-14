from backend.services.internsg_scraper import InternSGScraper


def test_expand_query_machine_learning_exact() -> None:
    scraper = InternSGScraper()
    assert scraper.expand_query("Machine Learning") == [
        "machine learning intern singapore",
        "ml intern singapore",
        "ai intern singapore",
        "data science intern singapore",
        "machine learning internship singapore",
        "ai machine learning intern singapore",
    ]


def test_expand_query_role_agnostic_pattern() -> None:
    scraper = InternSGScraper()
    queries = scraper.expand_query("Product")
    assert queries == [
        "Product intern singapore",
        "Product internship singapore",
        "Product intern",
        "Product internship",
        "Product intern asia",
        "Product internship asia",
    ]
    assert len(queries) == 6
    assert all(("intern" in query.lower()) or ("internship" in query.lower()) for query in queries)
