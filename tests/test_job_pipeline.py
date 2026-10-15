"""Tests for jobs/pipeline.py: combining both sources with dedup and
preference filtering. Both sources are mocked, only the wiring is
under test here."""

from unittest.mock import patch

import pytest

from jobs import pipeline
from jobs.store import JobAlertStore


@pytest.fixture
def store():
    s = JobAlertStore(":memory:")
    yield s
    s.close()


def _listing(id_, title="Software Engineer", category="Software Engineering",
             locations=None):
    return {
        "id": id_,
        "title": title,
        "company": "Acme",
        "category": category,
        "locations": locations or ["Remote"],
        "date_posted": 100,
        "url": "https://example.com",
        "active": True,
    }


def test_matches_from_both_sources_are_combined(store):
    simplify_listing = _listing("simplify:a")
    ba_listing = _listing("ba:b", title="Business Analyst",
                           category="Business Analyst")
    with patch("jobs.pipeline.simplify_source.fetch_new_since",
               return_value=([simplify_listing], 200)), \
         patch("jobs.pipeline.ba_source.fetch_normalized",
               return_value=[ba_listing]):
        matched, new_cutoff = pipeline.find_new_matches(store, 0)
    assert {item["id"] for item in matched} == {"simplify:a", "ba:b"}
    assert new_cutoff == 200


def test_already_notified_listing_is_excluded(store):
    store.mark_notified("simplify:a")
    with patch("jobs.pipeline.simplify_source.fetch_new_since",
               return_value=([_listing("simplify:a")], 100)), \
         patch("jobs.pipeline.ba_source.fetch_normalized", return_value=[]):
        matched, _ = pipeline.find_new_matches(store, 0)
    assert matched == []


def test_non_matching_preferences_are_excluded(store):
    off_pref = _listing("simplify:a", category="Hardware")
    with patch("jobs.pipeline.simplify_source.fetch_new_since",
               return_value=([off_pref], 100)), \
         patch("jobs.pipeline.ba_source.fetch_normalized", return_value=[]):
        matched, _ = pipeline.find_new_matches(store, 0)
    assert matched == []


def test_cutoff_passes_through_from_simplify_source(store):
    with patch("jobs.pipeline.simplify_source.fetch_new_since",
               return_value=([], 12345)) as fetch_since, \
         patch("jobs.pipeline.ba_source.fetch_normalized", return_value=[]):
        _, new_cutoff = pipeline.find_new_matches(store, 999)
    fetch_since.assert_called_once_with(999)
    assert new_cutoff == 12345
