# Agent 09 — Prospect Scout

An evidence-first prospect research workspace for finding reachable small-business prospects. Live web discovery uses Tavily's keyless mode by default (with shared limits) or an optional personal Tavily API key.

**Initial focus:** independent US HVAC contractors and their non-phone digital contact routes.

## Why this exists

A business can be a good customer on paper and still be a poor prospect if there is no reliable way to reach its decision-maker.

Prospect Scout separates two questions:

1. **Business relevance:** does the public website show signs that the business belongs to the target niche?
2. **Digital reachability:** does the official website publish an email, enquiry form, or social page that can be checked manually?

The app does not claim that an email inbox is monitored, that a social page is active, or that a company will buy. It records observable evidence and leaves uncertain findings for human review.

## What it does

- Searches the public web through Tavily for a niche and US metro area.
- Displays source URLs, snippets, and search relevance for manual review.
- Accepts confirmed official business website URLs from search results or manual input.
- Checks a maximum of six pages on each same-site domain.
- Reads the site's robots.txt policy before crawling.
- Extracts publicly displayed business email addresses and mailto links.
- Detects likely enquiry forms without submitting them.
- Finds Facebook and Instagram links published on the business website.
- Records possible owner/manager name-and-role mentions for manual verification.
- Detects HVAC-related wording and quote/estimate/booking phrases.
- Scores digital reachability from 0 to 10.
- Stores results locally in SQLite and exports CSV.

## What it deliberately does not do

- It does not scrape Google Maps, directory search-result pages, or social networks.
- It does not bypass logins, paywalls, CAPTCHAs, robots.txt, or access controls.
- It does not send emails, DMs, texts, or connection requests.
- It does not submit contact forms.
- It does not verify whether an inbox is monitored or whether a person opened a message.
- It does not infer private personal email addresses or guess email patterns.
- It does not claim the absence of a signal when a limited scan simply failed to find it.

Search-engine results and directory entries should be reviewed by a human. Paste only the company's official public website into the scanner.

## Quick start — Windows

Install Python 3.10 or newer, then open PowerShell in this folder.

~~~powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m streamlit run app.py
~~~

Open the local URL printed by Streamlit, usually http://localhost:8501.

### Enable live web search

Live web search works by default using Tavily's shared keyless mode, which has fair-use limits and may be rate-limited. You do not need an API key to try the initial workflow.

For higher or more predictable capacity, create a Tavily account at https://www.tavily.com/, copy your API key, and add it as `TAVILY_API_KEY` to your local environment or Streamlit Community Cloud secrets. Never paste the key into source code, commit it to GitHub, or share it in a chat.

For a local Windows run, set the key before starting the app:

~~~powershell
$env:TAVILY_API_KEY = "tvly-your-key-here"
py -m streamlit run app.py
~~~

Prospect Scout makes two basic search requests per discovery run; website scanning is separate from Tavily search credits.

## How to use it

1. In the sidebar, enter a niche such as HVAC contractor.
2. Enter one US city or metro, such as Dallas, TX.
3. Open the generated search links and identify candidate companies.
4. Visit each business's official website and copy its URL.
5. Paste up to 30 URLs into the app, one per line.
6. Click **Scan websites**.
7. Review the evidence, score, and recommended digital route.
8. Download the results as CSV.

The web-discovery step is powered by Tavily's Search API. The app sends two targeted queries per search run, displays the returned pages, and lets you select the results you have confirmed are official company websites. Search results may include directories or irrelevant pages, so review them before scanning. The scanner then inspects only the selected public websites.

## Reachability score

| Signal found on official website | Points |
|---|---:|
| Possible owner/manager name and role | 2 |
| Public business email address | 3 |
| Likely enquiry form | 2 |
| Facebook page link | 1 |
| Instagram page link | 1 |
| Contact/estimate page discovered | 1 |
| **Maximum** | **10** |

| Score | Tier |
|---:|---|
| 7–10 | High |
| 4–6 | Medium |
| 0–3 | Low |

A phone link is recorded as public website information but is not counted in the score, because this workflow is designed for a researcher who cannot make US calls.

The score is only a prioritisation heuristic. It is not a response-rate estimate, lead-quality guarantee, or purchase probability. Verify every contact route manually.

## Data and privacy

- Prospect data is stored locally in data/prospects.sqlite.
- CSV export is available from the dashboard.
- The scanner makes limited HTTP requests to public websites, follows same-site links only, does not follow redirects, and uses a short delay between page requests.
- It checks the target's robots.txt and stops when the policy cannot be read or disallows crawling.
- Do not scan websites where you do not have a legitimate reason to review publicly available business information.
- Do not use the tool to build a bulk unsolicited messaging list. Respect each site's terms and applicable email/privacy laws.

## Project structure

~~~text
.
├── app.py
├── prospect_scout.py
├── requirements.txt
├── run_windows.bat
└── tests/
    └── test_prospect_scout.py
~~~

## Tests

~~~powershell
py -m pytest
~~~

## Roadmap

- [x] Manual search-link generation without API keys
- [x] Bounded official-website scanning
- [x] Public digital contact-route extraction
- [x] Reachability scoring and CSV export
- [ ] Add a review queue with manual verification status
- [ ] Connect a compliant search provider if a free/low-cost API option becomes available
- [ ] Add optional website-audit report generation using the existing Website Revenue Leak Auditor project
- [ ] Add a Buffer content workflow for publishing educational posts that attract inbound prospects

## Important

This is an MVP research assistant, not a fully autonomous prospecting agent. It helps answer: "Can I find a legitimate way to reach this company, and what did its own website actually show?" A person must still verify the business, its decision-maker, and whether the contact route is monitored.


## Run live prospect discovery on GitHub's cloud compute

The repository includes a GitHub Actions workflow. After adding the secret once, GitHub's hosted runner will search the web, inspect candidate company websites, and provide CSV/JSON output as a downloadable workflow artifact.

### One-time secret setup

1. Revoke any Tavily key that has been shared in a chat or other public place.
2. Generate a replacement key in your Tavily dashboard.
3. Open this repository's **Settings → Secrets and variables → Actions**.
4. Select **New repository secret**.
5. Name it exactly TAVILY_API_KEY and paste the replacement key as its value.
6. Save. The key is encrypted by GitHub and is not written into repository files.

### Run the cloud research job

1. Open the repository's **Actions** tab.
2. Select **Prospect discovery**.
3. Click **Run workflow**.
4. Enter the niche and US metro area, then choose the number of candidates and pages.
5. After the workflow completes, open the run and download the prospects artifact.

The workflow uses GitHub-hosted compute. It does not run on your PC. Search candidates and contact-route findings are leads requiring human review; a published email is not verified as monitored. The workflow does not send outreach or submit enquiry forms.
