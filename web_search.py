from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from tavily import TavilyClient, TavilyKeylessLimitError


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
    api_key: str | None,
    niche: str,
    metro: str,
    max_results_per_query: int = DEFAULT_MAX_RESULTS,
) -> list[dict[str, Any]]:
    """Search the public web using Tavily's keyless or authenticated SDK.

    Without an API key, Tavily's shared keyless search quota applies. Search
    results are leads, not verified business records. A person must confirm
    that a result is the company's official website before scanning it.
    """
    queries = build_prospect_queries(niche, metro)
    limit = max(1, min(int(max_results_per_query), DEFAULT_MAX_RESULTS))
    client = TavilyClient(api_key=api_key.strip()) if api_key and api_key.strip() else TavilyClient()
    candidates: dict[str, dict[str, Any]] = {}

    try:
        for query in queries:
            payload = client.search(
                query,
                search_depth="basic",
                max_results=limit,
                include_answer=False,
                include_raw_content=False,
                include_images=False,
            )

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
    except TavilyKeylessLimitError as exc:
        raise RuntimeError(
            "Tavily's shared keyless search limit has been reached. "
            "Try again later or add your own TAVILY_API_KEY for a separate quota."
        ) from exc
    except Exception as exc:
        message = str(exc)
        if "401" in message or "unauthorized" in message.lower():
            raise RuntimeError("Tavily rejected the API key. Check TAVILY_API_KEY.") from exc
        if "429" in message or "rate limit" in message.lower():
            raise RuntimeError("Tavily rate limit reached. Wait before searching again.") from exc
        raise RuntimeError(f"Tavily search failed: {type(exc).__name__}: {message[:220]}") from exc

    ordered = sorted(
        candidates.values(),
        key=lambda item: item.get("search_score", 0.0),
        reverse=True,
    )
    return ordered[:MAX_TOTAL_RESULTS]
