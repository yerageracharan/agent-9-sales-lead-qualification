from prospect_scout import (
    build_search_queries,
    reachability_tier,
    recommended_route,
    score_reachability,
)


def test_reachability_score_is_bounded_and_uses_non_phone_routes():
    score = score_reachability(
        emails=["owner@example.com"],
        contact_form=True,
        facebook=True,
        instagram=True,
        decision_maker_names=["Jane Doe (owner)"],
        contact_page=True,
    )
    assert score == 10


def test_phone_information_does_not_affect_reachability_score():
    without_phone = score_reachability([], False, False, False, [], False)
    with_public_routes = score_reachability(["service@example.com"], False, False, False, [], False)
    assert without_phone == 0
    assert with_public_routes == 3


def test_reachability_tiers():
    assert reachability_tier(8) == "High"
    assert reachability_tier(5) == "Medium"
    assert reachability_tier(1) == "Low"


def test_route_prefers_published_business_email():
    assert recommended_route(["service@example.com"], True, True, True) == "Published business email"


def test_contact_form_route_is_selected_when_email_is_not_public():
    assert recommended_route([], True, True, False) == "Website contact form, then active social page"


def test_search_queries_include_niche_and_metro():
    queries = build_search_queries("HVAC contractor", "Dallas, TX")
    assert len(queries) == 4
    assert all("Dallas, TX" in query for query in queries)
    assert any("official website" in query for query in queries)
