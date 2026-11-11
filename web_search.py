from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

import httpx

TAVILY_ENDPOINT = "https://api.tavily.com/search"
DEFAULT_MAX_RESULTS = 8
MAX_TOTAL_RESULTS = 30


def build_prospect_queries(niche: str, metro: str) -> list[str]:
    """Create targeted search queries for public business websites."""
    niche = (niche or "HVAC contractor").strip()
    metro = (metro or "").strip()
    if not metro:
        raise ValueError("Enter a US city or metro area.")

    return [
        f'"{niche}" companies "{metro}" official website contact',
        f'independent "{niche}" contractor "{metro}" company website',
    ]


def _normalise_domain(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().strip(".")
    return host[4:] if host.startswith("www.") else host


def _is_web_url(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)


def search_web_for_prospects(
    api_key: str,
    niche: str,
    metro: str,
    max_results_per_query: int = DEFAULT_MAX_RESULTS,
) -> list[dict[str, Any]]:
    """Search the public web using Tavily and return deduplicated candidate pages.

    Search results are leads, not verified business records. The app does not
    crawl search result pages, submit forms, scrape social networks, or send
    messages. A person must confirm that a result is the company's official site.
    """
    if not api_key or not api_key.strip():
        raise ValueError("TAVILY_API_KEY is missing. Add your key to the local environment or Streamlit secrets.")

    queries = build_prospect_queries(niche, metro)
    limit = max(1, min(int(max_results_per_query), DEFAULT_MAX_RESULTS))
    timeout = httpx.Timeout(20.0, connect=8.0)
    candidates: dict[str, dict[str, Any]] = {}

    with httpx.Client(timeout=timeout) as client:
        for query in queries:
            try:
                response = client.post(
                    TAVILY_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {api_key.strip()}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "search_depth": "basic",
                        "topic": "general",
                        "max_results": limit,
                        "include_answer": False,
                        "include_raw_content": False,
                        "include_images": False,
                        "include_favicon": False,
                        "country": None,
                        "language": "en",
                    },
                )
            except httpx.TimeoutException as exc:
                raise RuntimeError("Tavily search timed out. Try again with a shorter query.") from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Could not reach Tavily: {type(exc).__name__}") from exc

            if response.status_code == 401:
                raise RuntimeError("Tavily rejected the API key. Check that TAVILY_API_KEY is correct.")
            if response.status_code == 429:
                raise RuntimeError("Tavily rate limit reached. Wait before searching again.")
            if response.status_code in {432, 433, 434}:
                raise RuntimeError("Tavily usage limit reached. Check your account's remaining credits.")
            if response.status_code >= 400:
                raise RuntimeError(f"Tavily returned HTTP {response.status_code}: {response.text[:300]}")

            payload = response.json()
            for row in payload.get("results", []):
                url = str(row.get("url", "")).strip()
                if not _is_web_url(url):
                    continue

                domain = _normalise_domain(url)
                if not domain or domain in candidates:
                    continue

                candidates[domain] = {
                    "title": str(row.get("title", "")).strip()[:240],
                    "url": url,
                    "domain": domain,
                    "snippet": re.sub(r"\s+", " ", str(row.get("content", "")).strip())[:900],
                    "search_score": float(row.get("score", 0.0) or 0.0),
                    "published_date": row.get("published_date"),
                    "query": query,
                    "source": "Tavily web search",
                    "official_website_verified": False,
                }

    ordered = sorted(
        candidates.values(),
        key=lambda item: item.get("search_score", 0.0),
        reverse=True,
    )
    return ordered[:MAX_TOTAL_RESULTS]
