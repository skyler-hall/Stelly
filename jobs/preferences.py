"""
Skyler's job listing preferences: which new postings are worth a text.

Locked in directly with Skyler rather than guessed:

  categories  Software or Software Engineering from the Simplify feed,
              plus every posting from the Business Analyst feed (that
              source is already scoped to BA roles by construction, so it
              skips title keyword matching entirely, see below)
  keywords    software engineer, swe, software developer, backend,
              frontend, full stack, data scientist, machine learning,
              ml engineer, ai engineer, data engineer
  locations   Remote, or the DC-to-NYC corridor: Washington DC, Virginia,
              Maryland, Pennsylvania, Philadelphia, New Jersey, New York

A posting's title only gets keyword-checked when its category is one of
the general CATEGORIES. Business Analyst postings are exempt since every
row of that feed already is one, keyword narrowing would just be
re-checking something already true.
"""

import re

TITLE_KEYWORDS = [
    "software engineer",
    "swe",
    "software developer",
    "backend",
    "front end",
    "frontend",
    "full stack",
    "data scientist",
    "machine learning",
    "ml engineer",
    "ai engineer",
    "data engineer",
]

CATEGORIES = {"Software", "Software Engineering"}

BA_CATEGORY = "Business Analyst"

LOCATION_KEYWORDS = [
    "remote",
    "washington, dc",
    "washington dc",
    "dc",
    "virginia",
    "va",
    "maryland",
    "md",
    "pennsylvania",
    "pa",
    "philadelphia",
    "new jersey",
    "nj",
    "new york",
    "ny",
    "nyc",
]


def _contains_word(word, text):
    """Whole-word, case-insensitive match, so short tokens like "pa" or
    "ny" don't fire on unrelated substrings ("Spain", "Company")."""
    return re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is not None


def _location_matches(locations):
    text = " | ".join(locations or [])
    return any(_contains_word(keyword, text) for keyword in LOCATION_KEYWORDS)


def matches(listing):
    """True if a normalized listing (see simplify_source.normalize or
    ba_source._parse_row for the shape) fits Skyler's preferences."""
    if not _location_matches(listing.get("locations")):
        return False

    category = listing.get("category", "")
    if category == BA_CATEGORY:
        return True

    if category not in CATEGORIES:
        return False

    title = listing.get("title") or ""
    return any(_contains_word(keyword, title) for keyword in TITLE_KEYWORDS)
