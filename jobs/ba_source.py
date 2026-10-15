"""
Fetches new-grad Business Analyst postings from jobright.ai's README feed.

Unlike SimplifyJobs, this repo publishes no JSON, just a markdown table in
README.md that their bot regenerates daily, showing only postings from
roughly the last 7 days. There is no id field, no active flag, and dates
are day-and-month only ("Aug 18", no year), so this module does more work
than simplify_source.py to reach the same normalized shape:

  id          the job detail page's own id, pulled out of its URL, the
              only stable unique thing each row has
  active      always True, the source itself only lists live postings
              and simply drops a row once it ages out
  date_posted parsed from "Aug 18" plus a year guessed from how far the
              result lands from "now" (handles the December/January
              rollover, the one case a bare year assumption gets wrong)

Every row is already a Business Analyst posting by construction (that is
the whole point of this repo), so category is hardcoded rather than read
from anywhere, and jobs/preferences.py skips title keyword matching for
this source for the same reason.

Rows that share one company get shown once, with later rows using a small
arrow in place of the company name, each still its own posting at its own
location with its own link, so parsing forward-fills the company name
onto those rows rather than treating them as duplicates.
"""

import re
from datetime import datetime, timedelta

import requests

README_URL = (
    "https://raw.githubusercontent.com/jobright-ai/"
    "2026-Business-Analyst-New-Grad/master/README.md"
)
REQUEST_TIMEOUT_SECONDS = 30
CATEGORY = "Business Analyst"

_LINK_RE = re.compile(r"\[(.*?)\]\((.*?)\)")
_ID_RE = re.compile(r"jobs/info/([A-Za-z0-9]+)")
_FUTURE_TOLERANCE = timedelta(days=3)
_YEAR_ROLLOVER_TOLERANCE = timedelta(days=350)


def fetch_raw():
    """The README's raw markdown text."""
    response = requests.get(README_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text


def _parse_date(text, reference=None):
    """"Aug 18" -> a unix timestamp, guessing the year from reference (the
    moment we're fetching at). Returns None for anything unparseable,
    callers should skip that row rather than guess further."""
    reference = reference or datetime.now()
    try:
        # A placeholder leap year keeps Feb 29 parseable; the real year is
        # substituted right after, so the placeholder never leaks out.
        parsed = datetime.strptime(f"{text.strip()} 2000", "%b %d %Y").replace(year=reference.year)
    except ValueError:
        return None

    if parsed > reference + _FUTURE_TOLERANCE:
        parsed = parsed.replace(year=parsed.year - 1)
    elif parsed < reference - _YEAR_ROLLOVER_TOLERANCE:
        parsed = parsed.replace(year=parsed.year + 1)

    return int(parsed.timestamp())


def _parse_row(cells, last_company, reference):
    """One table row's cells -> (listing_or_None, company_for_next_row)."""
    company_cell, title_cell, location, work_model, date_str = cells[:5]

    company_match = _LINK_RE.search(company_cell)
    if company_match:
        last_company = company_match.group(1).strip()

    title_match = _LINK_RE.search(title_cell)
    if not title_match:
        return None, last_company
    title, url = title_match.group(1).strip(), title_match.group(2).strip()

    id_match = _ID_RE.search(url)
    if not id_match:
        return None, last_company

    posted = _parse_date(date_str, reference)
    if posted is None:
        return None, last_company

    locations = [location] if location else []
    if work_model.strip().lower() == "remote" and "remote" not in [l.lower() for l in locations]:
        locations.append("Remote")

    listing = {
        "id": "ba:" + id_match.group(1),
        "title": title,
        "company": last_company,
        "locations": locations,
        "category": CATEGORY,
        "date_posted": posted,
        "url": url.split("?")[0],
        "active": True,
    }
    return listing, last_company


def parse_table(markdown_text, reference=None):
    """The README's job table -> a list of normalized listings. Malformed
    or header/separator rows are skipped rather than raised on, one bad
    row from a source we don't control shouldn't sink the whole fetch."""
    listings = []
    last_company = ""

    for line in markdown_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= {"-", " ", ":"}:
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 5 or cells[0].lower() == "company":
            continue

        listing, last_company = _parse_row(cells, last_company, reference)
        if listing:
            listings.append(listing)

    return listings


def fetch_normalized():
    """Fetch and parse in one step, the entry point pipeline.py uses."""
    return parse_table(fetch_raw())


if __name__ == "__main__":
    # Quick manual check: how many BA postings are on the board right now.
    rows = fetch_normalized()
    print(f"{len(rows)} postings")
