"""
Fetches new-grad job postings from SimplifyJobs' New-Grad-Positions repo.

The dev branch keeps a machine readable listings.json (source of truth for
their README table), updated frequently by their own bot. Every entry has
a stable id, an active flag (postings get flipped to inactive rather than
removed, so the file only grows), and unix timestamps for when it was
posted and last updated.

fetch_new_since does the two things the job alert actually needs: drop
anything inactive, and drop anything already seen by a previous run, so
repeated calls only ever look at postings newer than the last one we
processed. That keeps the per-run work small despite the feed itself
being tens of thousands of entries.
"""

import requests

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/"
    "dev/.github/scripts/listings.json"
)
REQUEST_TIMEOUT_SECONDS = 30


def fetch_raw():
    """The full listings.json, parsed, exactly as SimplifyJobs publishes it."""
    response = requests.get(LISTINGS_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def normalize(raw):
    """One raw listings.json entry -> the shared listing shape every
    source in this package produces: id, title, company, locations,
    category, date_posted, url, active. The id is namespaced so it can
    never collide with an id from another source in the notified store."""
    return {
        "id": "simplify:" + str(raw.get("id", "")),
        "title": raw.get("title", ""),
        "company": raw.get("company_name", ""),
        "locations": raw.get("locations") or [],
        "category": raw.get("category", ""),
        "date_posted": int(raw.get("date_posted") or 0),
        "url": raw.get("url", ""),
        "active": bool(raw.get("active")),
    }


def fetch_new_since(cutoff_ts):
    """Active postings with date_posted after cutoff_ts, normalized.

    Returns (new_listings, new_cutoff_ts). new_cutoff_ts is the highest
    date_posted seen among what was returned (or cutoff_ts unchanged if
    nothing new came in), the value the caller should persist and pass
    back in as cutoff_ts next time."""
    raw_listings = fetch_raw()

    new_listings = []
    new_cutoff = cutoff_ts
    for raw in raw_listings:
        if not raw.get("active"):
            continue
        posted = int(raw.get("date_posted") or 0)
        if posted <= cutoff_ts:
            continue
        new_listings.append(normalize(raw))
        if posted > new_cutoff:
            new_cutoff = posted

    return new_listings, new_cutoff


if __name__ == "__main__":
    # Quick manual check: how many active postings exist right now.
    listings = fetch_raw()
    active = sum(1 for item in listings if item.get("active"))
    print(f"{len(listings)} total entries, {active} active")
