from web_search import build_prospect_queries, _normalise_domain, _is_web_url


def test_build_prospect_queries_uses_niche_and_metro():
    queries = build_prospect_queries("HVAC contractor", "Dallas, TX")
    assert len(queries) == 2
    assert all("Dallas, TX" in query for query in queries)
    assert all("HVAC contractor" in query for query in queries)


def test_build_prospect_queries_requires_metro():
    try:
        build_prospect_queries("HVAC contractor", "")
    except ValueError as exc:
        assert "city or metro" in str(exc)
    else:
        raise AssertionError("Expected a missing-metro ValueError")


def test_domain_normalisation_removes_www():
    assert _normalise_domain("https://www.example.com/contact") == "example.com"


def test_only_http_and_https_results_are_accepted():
    assert _is_web_url("https://example.com")
    assert _is_web_url("http://example.com")
    assert not _is_web_url("mailto:owner@example.com")
    assert not _is_web_url("javascript:alert(1)")
