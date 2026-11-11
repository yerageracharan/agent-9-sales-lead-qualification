from __future__ import annotations

from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

from prospect_scout import (
    build_search_queries,
    load_prospects,
    make_csv,
    save_prospects,
    scan_website,
)

st.set_page_config(page_title="Prospect Scout", page_icon="🔎", layout="wide")
st.title("Prospect Scout")
st.caption("Evidence-first prospect discovery and reachability research for small-business services.")

st.info(
    "This is a human-in-the-loop research tool. It does not scrape Google Maps, harvest social networks, "
    "send emails or messages, submit forms, or bypass website access rules. Search for candidate businesses, "
    "paste their official website URLs, and let the scanner check public contact routes."
)

with st.sidebar:
    st.header("Search setup")
    niche = st.text_input("Business niche", value="HVAC contractor")
    metro = st.text_input("US city or metro area", placeholder="e.g. Dallas, TX")
    if metro.strip():
        try:
            queries = build_search_queries(niche, metro)
            st.markdown("**Open a search in your browser**")
            for index, query in enumerate(queries, start=1):
                url = "https://www.google.com/search?q=" + quote_plus(query)
                st.markdown(f"{index}. [Search: {query}]({url})")
            st.caption("Search results are discovery leads. Verify each business on its own official website.")
        except ValueError as exc:
            st.warning(str(exc))

st.subheader("1. Add candidate business websites")
urls_text = st.text_area(
    "Paste official website URLs, one per line",
    height=150,
    placeholder="https://example-hvac.com\nhttps://another-heating-company.com",
)
max_pages = st.slider("Maximum same-site pages per company", min_value=1, max_value=6, value=5)

if st.button("Scan websites", type="primary", disabled=not urls_text.strip()):
    raw_urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
    unique_urls = list(dict.fromkeys(raw_urls))[:30]
    if len(raw_urls) > 30:
        st.warning("The first 30 unique URLs will be scanned in this run.")
    progress = st.progress(0)
    results = []
    for index, url in enumerate(unique_urls, start=1):
        with st.spinner(f"Checking {url}"):
            try:
                results.append(scan_website(url, max_pages=max_pages))
            except Exception as exc:
                results.append({
                    "website": url,
                    "domain": "",
                    "business_name": "",
                    "status": "error",
                    "reachability_score": 0,
                    "reachability_tier": "Low",
                    "recommended_route": "Manual review required",
                    "observations": [f"Scan failed: {type(exc).__name__}"],
                    "emails": [],
                    "decision_maker_mentions": [],
                    "phone_links": [],
                    "pages_checked": [],
                    "contact_form_detected": False,
                    "facebook_url": "",
                    "instagram_url": "",
                    "contact_page_found": False,
                    "quote_or_booking_cta": False,
                    "service_relevance": False,
                })
        progress.progress(index / len(unique_urls))
    st.session_state["scan_results"] = results
    successful = [r for r in results if r.get("status") == "scanned"]
    if successful:
        save_prospects(successful)
    st.success(f"Finished. {len(successful)} websites scanned; {len(results) - len(successful)} need manual review.")

results = st.session_state.get("scan_results", [])
saved = load_prospects()

st.subheader("2. Review the prospects")
display_records = results if results else saved
if display_records:
    rows = []
    for item in display_records:
        rows.append({
            "Business": item.get("business_name") or item.get("domain") or item.get("website"),
            "Reachability": item.get("reachability_score", 0),
            "Tier": item.get("reachability_tier", "Low"),
            "Best route": item.get("recommended_route", ""),
            "Email": "Yes" if item.get("emails") else "No",
            "Contact form": "Yes" if item.get("contact_form_detected") else "No",
            "Facebook": "Yes" if item.get("facebook_url") else "No",
            "Instagram": "Yes" if item.get("instagram_url") else "No",
            "HVAC signals": "Yes" if item.get("service_relevance") else "Not detected",
            "Status": item.get("status", ""),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    for item in display_records:
        label = item.get("business_name") or item.get("domain") or item.get("website")
        with st.expander(f"{label} — {item.get('reachability_tier', 'Low')} reachability"):
            st.write("**Website:**", item.get("website", ""))
            st.write("**Recommended route:**", item.get("recommended_route", ""))
            if item.get("emails"):
                st.write("**Public email(s):**", ", ".join(item["emails"]))
                st.caption("Publicly displayed does not mean monitored or deliverable.")
            if item.get("decision_maker_mentions"):
                st.write("**Possible decision-maker mentions:**", ", ".join(item["decision_maker_mentions"]))
                st.caption("Verify the name and role manually before addressing a message.")
            if item.get("facebook_url"):
                st.write("**Facebook:**", item["facebook_url"])
            if item.get("instagram_url"):
                st.write("**Instagram:**", item["instagram_url"])
            if item.get("phone_links"):
                st.write("**Published phone link(s):**", ", ".join(item["phone_links"]))
                st.caption("Recorded as public site information only; phone is not included in the reachability score.")
            st.write("**Pages checked:**")
            for page in item.get("pages_checked", []):
                st.markdown(f"- {page}")
            st.write("**Evidence and observations:**")
            for observation in item.get("observations", []):
                st.markdown(f"- {observation}")
            st.caption("A missing signal means it was not found in the limited pages scanned, not that it does not exist.")

    st.download_button(
        "Download prospects as CSV",
        data=make_csv(display_records),
        file_name="prospect-scout-results.csv",
        mime="text/csv",
    )
else:
    st.caption("No saved prospects yet. Add a few official business websites above to begin.")

st.subheader("3. How to interpret the score")
st.markdown(
    """
    - **High (7–10):** several usable, non-phone contact routes were found.
    - **Medium (4–6):** at least one plausible digital route exists, but verify the route.
    - **Low (0–3):** limited digital reachability evidence; do not spend audit time here first.

    The score is a prioritisation heuristic, not a probability of response or purchase.
    Email presence is not inbox verification. A contact form is not proof that a person reads submissions.
    """
)

st.subheader("Suggested workflow")
st.markdown(
    """
    1. Pick one US metro and one business niche.
    2. Use the search links to find candidate businesses through public search results or industry directories.
    3. Open the company's own website and copy its URL here.
    4. Prioritise prospects with more than one verified digital contact route.
    5. Manually review the website evidence and the current social pages before contacting anyone.
    6. Track replies and opt-outs in your own CRM; do not send bulk automated messages from this app.
    """
)
