from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from tavily import TavilyClient

from prospect_scout import scan_website

SKIP_HOSTS = {
    "google.com", "bing.com", "duckduckgo.com",
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com",
    "yelp.com", "angi.com", "homeadvisor.com", "thumbtack.com",
    "bbb.org", "yellowpages.com", "mapquest.com", "nextdoor.com",
    "manta.com", "porch.com", "houzz.com", "buildzoom.com",
    "acca.org", "chamberofcommerce.com", "superpages.com",
}
SERVICE_SIGNAL = re.compile(
    r"\b(hvac|heating|air conditioning|air conditioner|cooling|furnace|heat pump|ductless)\b",
    re.I,
)


def domain_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().strip(".")
    return host[4:] if host.startswith("www.") else host


def is_excluded_domain(domain: str) -> bool:
    return any(domain == blocked or domain.endswith("." + blocked) for blocked in SKIP_HOSTS)


def discover_candidates(client: TavilyClient, niche: str, metro: str, limit: int) -> list[dict[str, Any]]:
    queries = [
        f'"{niche}" "{metro}" contractor official company website',
        f'independent {niche} companies serving "{metro}" official website contact',
        f'"{niche}" "{metro}" request service company',
    ]

    candidates: dict[str, dict[str, Any]] = {}
    for query in queries:
        response = client.search(
            query,
            search_depth="basic",
            max_results=10,
            include_answer=False,
            include_raw_content=False,
            include_images=False,
        )
        for result in response.get("results", []):
            url = str(result.get("url", "")).strip()
            if not url.startswith(("https://", "http://")):
                continue
            domain = domain_of(url)
            if not domain or is_excluded_domain(domain) or domain in candidates:
                continue

            title = str(result.get("title", "")).strip()
            snippet = re.sub(r"\s+", " ", str(result.get("content", "")).strip())
            if not SERVICE_SIGNAL.search(title + " " + snippet):
                continue

            candidates[domain] = {
                "search_title": title[:240],
                "search_url": url,
                "domain": domain,
                "search_snippet": snippet[:900],
                "search_relevance": round(float(result.get("score", 0.0) or 0.0), 4),
                "search_query": query,
                "source": "Tavily",
                "manual_review_required": True,
            }

    return sorted(
        candidates.values(),
        key=lambda item: item["search_relevance"],
        reverse=True,
    )[: max(1, min(limit, 20))]


def run(niche: str, metro: str, limit: int, pages: int, out_dir: Path) -> list[dict[str, Any]]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing TAVILY_API_KEY. Add it as a GitHub Actions repository secret.")

    client = TavilyClient(api_key=api_key)
    candidates = discover_candidates(client, niche, metro, limit)
    output: list[dict[str, Any]] = []

    for index, candidate in enumerate(candidates, start=1):
        print(f"[{index}/{len(candidates)}] Inspecting {candidate['search_url']}")
        try:
            findings = scan_website(candidate["search_url"], max_pages=pages)
        except Exception as exc:
            findings = {
                "website": candidate["search_url"],
                "domain": candidate["domain"],
                "status": "scan_error",
                "business_name": "",
                "emails": [],
                "phone_links": [],
                "facebook_url": "",
                "instagram_url": "",
                "decision_maker_mentions": [],
                "contact_form_detected": False,
                "contact_page_found": False,
                "quote_or_booking_cta": False,
                "service_relevance": False,
                "reachability_score": 0,
                "reachability_tier": "Low",
                "recommended_route": "Manual review required",
                "pages_checked": [],
                "observations": [f"Scan failed: {type(exc).__name__}"],
            }

        row = {**candidate, **findings}
        row["official_website_verified"] = False
        row["email_monitored_verified"] = False
        output.append(row)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prospects.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    csv_fields = [
        "search_title", "search_url", "domain", "search_relevance",
        "business_name", "website", "status", "service_relevance",
        "reachability_score", "reachability_tier", "recommended_route",
        "emails", "email_monitored_verified", "contact_form_detected",
        "facebook_url", "instagram_url", "decision_maker_mentions",
        "quote_or_booking_cta", "contact_page_found", "manual_review_required",
    ]
    with (out_dir / "prospects.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for row in output:
            flattened = dict(row)
            for field in ("emails", "decision_maker_mentions", "pages_checked", "observations"):
                value = flattened.get(field, [])
                flattened[field] = " | ".join(map(str, value)) if isinstance(value, list) else value
            writer.writerow(flattened)

    print(f"Saved {len(output)} candidate records to {out_dir}/prospects.csv and prospects.json")
    print("Reminder: search results and contact signals require human verification.")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover and qualify public business websites.")
    parser.add_argument("--niche", required=True)
    parser.add_argument("--metro", required=True)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--output", default="output")
    args = parser.parse_args()

    run(args.niche, args.metro, args.limit, args.pages, Path(args.output))
