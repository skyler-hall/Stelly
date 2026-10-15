"""
Assembles a job listing alert: fetch both sources, keep only postings
Skyler hasn't already been texted about that fit his preferences.

Only the Simplify source uses the cutoff timestamp. It is a genuinely
large feed (tens of thousands of entries, only growing), so skipping
anything already accounted for saves real work. The BA source is small
and only ever shows roughly a week of postings, so it needs no cutoff of
its own, every row gets checked against the notified store directly.

Matched listings are not marked notified here. Whether a posting counts
as "already alerted" is decided by whether the text actually went out,
which this module has no visibility into, so that marking happens in
reminders/checks.py after notify() succeeds.
"""

from jobs import ba_source, preferences, simplify_source


def find_new_matches(store, cutoff_ts):
    """Returns (matched_listings, new_cutoff_ts).

    matched_listings is every posting, from either source, that Skyler
    hasn't been notified about and that fits his preferences. new_cutoff_ts
    is where the Simplify fetch should resume from next time."""
    simplify_new, new_cutoff = simplify_source.fetch_new_since(cutoff_ts)
    ba_new = ba_source.fetch_normalized()

    matched = []
    for listing in simplify_new + ba_new:
        if store.is_notified(listing["id"]):
            continue
        if not preferences.matches(listing):
            continue
        matched.append(listing)

    return matched, new_cutoff
