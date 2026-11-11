from __future__ import annotations

import ipaddress
import json
import re
import socket
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "ProspectScout/0.1 (paced public website research)"
DEFAULT_DB = Path("data/prospects.sqlite")
MAX_PAGES_HARD_LIMIT = 6
REQUEST_DELAY_SECONDS = 0.45
SOCIAL_HOSTS = {
    "facebook": ("facebook.com", "fb.com"),
    "instagram": ("instagram.com",),
}
CONTACT_WORDS = re.compile(r"(contact|about|team|staff|leadership|service|estimate|quote|booking|book|schedule|location)", re.I)
CTA_WORDS = re.compile(r"\b(request (an? )?(estimate|quote)|get (an? )?(estimate|quote)|free estimate|book online|schedule (service|an? appointment)|request service)\b", re.I)
SERVICE_WORDS = re.compile(r"\b(hvac|heating|air conditioning|air conditioner|cooling|furnace|heat pump|ductless|ventilation)\b", re.I)
EMAIL_RE = re.compile(r"(?i)(?<![\w.+-])[\w.+-]{1,64}@[\w.-]+\.[a-z]{2,24}")
ROLE_NAME_RE = re.compile(
    r"\b(owner|founder|president|general manager|operations manager)\b"
    r"\s*(?:is|:|-|,)?\s*([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,2})"
)


def _is_public_host(hostname: str) -> bool:
    """Reject local/private destinations before making outbound requests."""
    try:
        literal = ipaddress.ip_address(hostname)
        return literal.is_global
    except ValueError:
        pass

    if not hostname or hostname.lower() in {"localhost", "localhost.localdomain"}:
        return False

    try:
        addresses = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    resolved = {item[4][0] for item in addresses}
    if not resolved:
        return False
    try:
        return all(ipaddress.ip_address(value).is_global for value in resolved)
    except ValueError:
        return False


def normalize_website(raw_url: str) -> str:
    """Normalize a user-supplied business website and reject unsafe targets."""
    value = (raw_url or "").strip()
    if not value:
        raise ValueError("Enter a website URL.")

    if "://" not in value:
        value = "https://" + value

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https websites are supported.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing usernames or passwords are not allowed.")
    if not parsed.hostname or "." not in parsed.hostname:
        raise ValueError("Enter a public business website domain.")

    hostname = parsed.hostname.lower().rstrip(".")
    if not _is_public_host(hostname):
        raise ValueError("This domain does not resolve to a public IP address.")

    netloc = hostname
    if parsed.port and not ((parsed.scheme == "https" and parsed.port == 443) or (parsed.scheme == "http" and parsed.port == 80)):
        netloc = f"{hostname}:{parsed.port}"

    path = parsed.path or "/"
    return urlunsplit((parsed.scheme, netloc, path, "", ""))


def _same_site(candidate: str, origin: str) -> bool:
    a, b = urlsplit(candidate), urlsplit(origin)
    return a.scheme in {"http", "https"} and a.netloc.lower() == b.netloc.lower()


def _robots_parser(client: httpx.Client, origin: str) -> tuple[RobotFileParser | None, str | None]:
    robots_url = urljoin(origin, "/robots.txt")
    try:
        response = client.get(robots_url)
    except httpx.HTTPError as exc:
        return None, f"Could not read robots.txt: {type(exc).__name__}"

    if response.status_code in {404, 410}:
        return None, None
    if response.status_code != 200:
        return None, f"Robots policy returned HTTP {response.status_code}; crawl stopped."

    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(response.text.splitlines())
    return parser, None


def _allowed(parser: RobotFileParser | None, url: str) -> bool:
    return parser is None or parser.can_fetch(USER_AGENT, url)


def _extract_candidate_links(html: str, page_url: str, origin: str, limit: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[tuple[int, str]] = []
    seen: set[str] = {page_url}

    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue

        absolute = urljoin(page_url, href)
        parsed = urlsplit(absolute)
        if parsed.scheme not in {"http", "https"} or not _same_site(absolute, origin):
            continue

        clean = urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))
        if clean in seen:
            continue
        seen.add(clean)

        signal = f"{anchor.get_text(' ', strip=True)} {parsed.path}"
        if CONTACT_WORDS.search(signal):
            priority = 0 if re.search(r"contact|estimate|quote|book|schedule", signal, re.I) else 1
            candidates.append((priority, clean))

    candidates.sort(key=lambda item: (item[0], item[1]))
    return [url for _, url in candidates[:limit]]


def score_reachability(
    emails: list[str],
    contact_form: bool,
    facebook: bool,
    instagram: bool,
    decision_maker_names: list[str],
    contact_page: bool,
) -> int:
    """Score usable non-phone business contact routes from 0 to 10."""
    score = 0
    if decision_maker_names:
        score += 2
    if emails:
        score += 3
    if contact_form:
        score += 2
    if facebook:
        score += 1
    if instagram:
        score += 1
    if contact_page:
        score += 1
    return min(score, 10)


def reachability_tier(score: int) -> str:
    if score >= 7:
        return "High"
    if score >= 4:
        return "Medium"
    return "Low"


def recommended_route(emails: list[str], contact_form: bool, facebook: bool, instagram: bool) -> str:
    if emails:
        return "Published business email"
    if contact_form and (facebook or instagram):
        return "Website contact form, then active social page"
    if contact_form:
        return "Website contact form"
    if facebook or instagram:
        return "Active business social page"
    return "No clear non-phone route found"


def build_search_queries(niche: str, metro: str) -> list[str]:
    niche = (niche or "HVAC contractor").strip()
    metro = (metro or "").strip()
    if not metro:
        raise ValueError("Enter a US city or metro area to generate search links.")

    return [
        f'"{niche}" "{metro}" official website',
        f'"{niche}" "{metro}" contact us',
        f'"heating and air conditioning" "{metro}" company',
        f'"{niche}" "{metro}" owner company',
    ]


def _clean_emails(values: set[str]) -> list[str]:
    cleaned = {
        value.strip(".,;:()[]<>").lower()
        for value in values
        if value and "example." not in value.lower() and "sentry" not in value.lower()
    }
    return sorted(cleaned)


def scan_website(raw_url: str, max_pages: int = 5) -> dict[str, Any]:
    """Inspect a small number of public pages on one business website.

    The scanner does not search directories, scrape search engines, submit forms,
    log in, bypass access controls, or send messages. It follows same-site links
    only and obeys the site's robots.txt policy.
    """
    website = normalize_website(raw_url)
    parsed_home = urlsplit(website)
    origin = f"{parsed_home.scheme}://{parsed_home.netloc}"
    page_limit = max(1, min(int(max_pages), MAX_PAGES_HARD_LIMIT))

    result: dict[str, Any] = {
        "website": website,
        "domain": parsed_home.hostname or "",
        "status": "started",
        "pages_checked": [],
        "emails": [],
        "phone_links": [],
        "facebook_url": "",
        "instagram_url": "",
        "decision_maker_mentions": [],
        "contact_form_detected": False,
        "contact_page_found": False,
        "quote_or_booking_cta": False,
        "service_relevance": False,
        "business_name": "",
        "reachability_score": 0,
        "reachability_tier": "Low",
        "recommended_route": "",
        "observations": [],
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }

    timeout = httpx.Timeout(8.0, connect=5.0)
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    ) as client:
        robots, robots_error = _robots_parser(client, origin)
        if robots_error:
            result["status"] = "robots_blocked_or_unavailable"
            result["observations"].append(robots_error)
            return result

        if not _allowed(robots, website):
            result["status"] = "disallowed_by_robots"
            result["observations"].append("The site's robots.txt does not allow this page to be crawled.")
            return result

        try:
            home_response = client.get(website)
        except httpx.HTTPError as exc:
            result["status"] = "fetch_error"
            result["observations"].append(f"Homepage request failed: {type(exc).__name__}")
            return result

        if home_response.is_redirect:
            result["status"] = "redirect_not_followed"
            result["observations"].append("The homepage redirects. Open the website manually and scan its final public URL.")
            return result
        if home_response.status_code != 200:
            result["status"] = f"http_{home_response.status_code}"
            result["observations"].append(f"Homepage returned HTTP {home_response.status_code}.")
            return result
        if "html" not in home_response.headers.get("content-type", "").lower():
            result["status"] = "not_html"
            result["observations"].append("The homepage did not return HTML.")
            return result

        pages: list[tuple[str, str]] = [(website, home_response.text)]
        discovered = _extract_candidate_links(home_response.text, website, origin, page_limit - 1)

        for page_url in discovered:
            if len(pages) >= page_limit:
                break
            if not _allowed(robots, page_url):
                continue
            time.sleep(REQUEST_DELAY_SECONDS)
            try:
                response = client.get(page_url)
            except httpx.HTTPError:
                continue
            if response.status_code != 200 or response.is_redirect:
                continue
            if "html" not in response.headers.get("content-type", "").lower():
                continue
            pages.append((page_url, response.text))

        emails: set[str] = set()
        phones: set[str] = set()
        social: dict[str, str] = {"facebook": "", "instagram": ""}
        owner_names: set[str] = set()
        contact_form = False
        has_contact_page = False
        has_quote_cta = False
        has_service_content = False
        title_candidates: list[str] = []

        for page_url, html in pages:
            soup = BeautifulSoup(html, "html.parser")
            page_text = soup.get_text(" ", strip=True)
            title = soup.title.get_text(" ", strip=True) if soup.title else ""
            if title:
                title_candidates.append(title)

            result["pages_checked"].append(page_url)
            if re.search(r"contact|estimate|quote|book|schedule", urlsplit(page_url).path, re.I):
                has_contact_page = True

            emails.update(EMAIL_RE.findall(page_text))
            for anchor in soup.find_all("a", href=True):
                href = str(anchor.get("href", "")).strip()
                if href.lower().startswith("mailto:"):
                    emails.add(href[7:].split("?", 1)[0])
                elif href.lower().startswith("tel:"):
                    phones.add(href[4:].split("?", 1)[0])

                absolute = urljoin(page_url, href)
                host = (urlsplit(absolute).hostname or "").lower()
                for key, hostnames in SOCIAL_HOSTS.items():
                    if any(host == item or host.endswith("." + item) for item in hostnames):
                        social[key] = absolute

            for form in soup.find_all("form"):
                input_types = [str(x.get("type", "")).lower() for x in form.find_all("input")]
                field_names = " ".join(
                    str(x.get("name", "")) + " " + str(x.get("placeholder", ""))
                    for x in form.find_all(["input", "textarea"])
                ).lower()
                if "email" in input_types or form.find("textarea") or re.search(r"email|message|phone|name", field_names):
                    contact_form = True
                    break

            for match in ROLE_NAME_RE.findall(page_text):
                role, person = match
                owner_names.add(f"{person} ({role.lower()})")

            has_quote_cta = has_quote_cta or bool(CTA_WORDS.search(page_text))
            has_service_content = has_service_content or bool(SERVICE_WORDS.search(page_text))

    result["emails"] = _clean_emails(emails)
    result["phone_links"] = sorted(phones)
    result["facebook_url"] = social["facebook"]
    result["instagram_url"] = social["instagram"]
    result["decision_maker_mentions"] = sorted(owner_names)
    result["contact_form_detected"] = contact_form
    result["contact_page_found"] = has_contact_page
    result["quote_or_booking_cta"] = has_quote_cta
    result["service_relevance"] = has_service_content

    if title_candidates:
        result["business_name"] = re.split(r"\s[|–—-]\s", title_candidates[0])[0].strip()[:120]

    result["reachability_score"] = score_reachability(
        result["emails"],
        contact_form,
        bool(social["facebook"]),
        bool(social["instagram"]),
        result["decision_maker_mentions"],
        has_contact_page,
    )
    result["reachability_tier"] = reachability_tier(result["reachability_score"])
    result["recommended_route"] = recommended_route(
        result["emails"], contact_form, bool(social["facebook"]), bool(social["instagram"])
    )
    result["status"] = "scanned"

    if result["emails"]:
        result["observations"].append("A public email address appears on the scanned website. This does not confirm that the inbox is monitored.")
    else:
        result["observations"].append("No public email was found in the scanned pages. This does not prove the company has no email address.")
    if contact_form:
        result["observations"].append("A likely enquiry form was detected. The scanner did not submit it.")
    if social["facebook"] or social["instagram"]:
        result["observations"].append("A Facebook or Instagram link was found on the scanned website; verify that the page is active.")
    if has_quote_cta:
        result["observations"].append("Quote, estimate, booking, or service-request wording was found.")
    if has_service_content:
        result["observations"].append("The scanned pages contain HVAC/heating/cooling-related service wording.")
    if owner_names:
        result["observations"].append("A possible owner or manager name/role was found in page text. Verify it manually before using it.")
    if not has_contact_page:
        result["observations"].append("No contact/estimate page was discovered within the page limit. This is not proof that one does not exist.")

    return result


def save_prospects(records: list[dict[str, Any]], db_path: Path = DEFAULT_DB) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS prospects (
                domain TEXT PRIMARY KEY,
                website TEXT NOT NULL,
                business_name TEXT,
                reachability_score INTEGER NOT NULL,
                scanned_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        for record in records:
            connection.execute(
                """
                INSERT INTO prospects(domain, website, business_name, reachability_score, scanned_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    website=excluded.website,
                    business_name=excluded.business_name,
                    reachability_score=excluded.reachability_score,
                    scanned_at=excluded.scanned_at,
                    payload_json=excluded.payload_json
                """,
                (
                    record.get("domain", ""),
                    record.get("website", ""),
                    record.get("business_name", ""),
                    int(record.get("reachability_score", 0)),
                    record.get("scanned_at", ""),
                    json.dumps(record, ensure_ascii=False),
                ),
            )


def load_prospects(db_path: Path = DEFAULT_DB) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as connection:
        try:
            rows = connection.execute("SELECT payload_json FROM prospects ORDER BY reachability_score DESC, scanned_at DESC").fetchall()
        except sqlite3.OperationalError:
            return []
    return [json.loads(row[0]) for row in rows]


def make_csv(records: list[dict[str, Any]]) -> str:
    import csv
    import io

    output = io.StringIO()
    fields = [
        "business_name", "website", "domain", "reachability_score", "reachability_tier",
        "recommended_route", "emails", "contact_form_detected", "facebook_url",
        "instagram_url", "decision_maker_mentions", "quote_or_booking_cta",
        "service_relevance", "status", "scanned_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in records:
        flattened = dict(row)
        for key in ("emails", "decision_maker_mentions", "phone_links"):
            flattened[key] = "; ".join(row.get(key, []))
        writer.writerow(flattened)
    return output.getvalue()
