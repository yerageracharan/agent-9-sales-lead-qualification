from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from prospect_scout import (
    load_prospects,
    make_csv,
    save_prospects,
    scan_website,
)
from web_search import search_web_for_prospects

st.set_page_config(page_title="Prospect Scout", page_icon="🔎", layout="wide")
st.title("Prospect Scout")
st.caption("Live web discovery + evidence-based prospect qualification.")

def get_tavily_key() -> str:
    key = os.getenv("TAVILY_API_KEY", "").strip()
    try:
        key = str(st.secrets.get("TAVILY_API_KEY", key)).strip() or key
    except Exception:
        pass
    return key


def scan_and_save(urls: list[str], max_pages: int) -> list[dict]:
    unique_urls = list(dict.fromkeys(url.strip() for url in urls if url.strip()))[:30]
    progress = st.progress(0)
    results: list[dict] = []
    for index, url in enumerate(unique_urls, start=1):
        with st.spinner(f"Inspecting {url}"):
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
    successful = [row for row in results if row.get("status") == "scanned"]
    if successful:
        save_prospects(successful)
    st.session_state["scan_results"] = results
    st.success(f"Completed {len(results)} scans. {len(successful)} were successful.")
    return results


def render_results(display_records: list[dict]) -> None:
    if not display_records:
        st.caption("No saved prospects yet. Search the web or paste official business websites above.")
        return

    rows = []
    for item in display_records:
        rows.append({
            "Business": item.get("business_name") or item.get("domain") or item.get("website"),
            "Reachability": item.get("reachability_score", 0),
            "Tier": item.get("reachability_tier", "Low"),
            "Best route": item.get("recommended_route", ""),
            "Email": "Found" if item.get("emails") else "Not found",
            "Contact form": "Found" if item.get("contact_form_detected") else "Not found",
            "Facebook": "Found" if item.get("facebook_url") else "Not found",
            "Instagram": "Found" if item.get("instagram_url") else "Not found",
            "HVAC signals": "Found" if item.get("service_relevance") else "Not detected",
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
                st.caption("Publicly displayed does not mean monitored, deliverable, or read.")
            if item.get("decision_maker_mentions"):
                st.write("**Possible decision-maker mentions:**", ", ".join(item["decision_maker_mentions"]))
                st.caption("These are text matches, not verified identities. Check the company's team/about page.")
            if item.get("facebook_url"):
                st.write("**Facebook:**", item["facebook_url"])
            if item.get("instagram_url"):
                st.write("**Instagram:**", item["instagram_url"])
            if item.get("phone_links"):
                st.write("**Published phone link(s):**", ", ".join(item["phone_links"]))
                st.caption("Recorded only; not used for outreach or reachability scoring.")
            if item.get("pages_checked"):
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


st.subheader("1. Search the live web for businesses")
with st.sidebar:
    st.header("Prospect search")
    niche = st.text_input("Business niche", value="HVAC contractor")
    metro = st.text_input("US city or metro area", placeholder="e.g. Dallas, TX")
    max_pages = st.slider("Pages to inspect per business", min_value=1, max_value=6, value=5)

tavily_key = get_tavily_key()
if not tavily_key:
    st.warning(
        "Live search is not connected yet. Create a free Tavily API key, then add it as "
        "TAVILY_API_KEY in your local environment or Streamlit secrets. Never commit the key to GitHub."
    )
else:
    st.success("Live web search is connected.")

if st.button("Search web for prospects", type="primary", disabled=not (tavily_key and metro.strip())):
    try:
        with st.spinner("Searching the public web..."):
            st.session_state["discovery_results"] = search_web_for_prospects(
                tavily_key, niche, metro, max_results_per_query=8
            )
        st.success(f"Found {len(st.session_state['discovery_results'])} candidate pages. Verify official business websites before scanning.")
    except Exception as exc:
        st.error(str(exc))

discovery_results = st.session_state.get("discovery_results", [])
if discovery_results:
    st.write("Search results are candidates, not verified companies. Directory pages and unrelated results may appear.")
    for index, item in enumerate(discovery_results, start=1):
        with st.expander(f"{index}. {item.get('title') or item.get('domain')}"):
            st.markdown(f"[Open result]({item.get('url')})")
            st.caption(item.get("domain", ""))
            st.write(item.get("snippet", ""))
            st.caption(f"Search relevance: {item.get('search_score', 0):.2f} · Query: {item.get('query', '')}")

    verified_options = {
        f"{item.get('title') or item.get('domain')} — {item.get('domain')}": item.get("url")
        for item in discovery_results
    }
    selected_labels = st.multiselect(
        "Select results you have confirmed are official company websites",
        options=list(verified_options.keys()),
        help="Do not select directory, social-network, or aggregator pages as company websites.",
    )
    if st.button("Inspect selected company websites", disabled=not selected_labels):
        scan_and_save([verified_options[label] for label in selected_labels], max_pages)

st.divider()
st.subheader("2. Or paste business websites manually")
urls_text = st.text_area(
    "Official website URLs, one per line",
    height=120,
    placeholder="https://example-hvac.com\nhttps://another-heating-company.com",
)
if st.button("Inspect pasted websites", disabled=not urls_text.strip()):
    raw_urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
    if len(raw_urls) > 30:
        st.warning("Only the first 30 unique URLs will be inspected.")
    scan_and_save(raw_urls, max_pages)

st.divider()
st.subheader("3. Qualified prospect list")
current_results = st.session_state.get("scan_results", [])
saved = load_prospects()
render_results(current_results if current_results else saved)

st.subheader("How to interpret reachability")
st.markdown(
    """
    - **High (7–10):** several digital contact signals were found on the scanned website.
    - **Medium (4–6):** at least one plausible digital route exists.
    - **Low (0–3):** few digital contact signals were detected.

    This is a prioritisation heuristic, not a probability of response or purchase.
    A published email is not proof that an inbox is monitored. A social link is not proof that a page is active.
    Manually verify the owner/manager, official website, and contact route before outreach.
    """
)

st.caption(
    "Safety and data boundaries: this app searches through Tavily's API, then inspects only selected public company URLs. "
    "It does not scrape Google Maps or social networks, bypass robots.txt, submit forms, send DMs/emails, or make calls."
)
