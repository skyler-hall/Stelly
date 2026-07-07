"""Tests for tracker/store.py using throwaway in-memory databases."""

import pytest

from tracker.store import TrackerStore


@pytest.fixture
def store():
    s = TrackerStore(":memory:")
    yield s
    s.close()


def test_unseen_message_is_not_seen(store):
    assert store.is_seen("<msg1@mail>") is False


def test_marked_message_is_seen(store):
    store.mark_seen("<msg1@mail>")
    assert store.is_seen("<msg1@mail>") is True


def test_marking_twice_is_harmless(store):
    store.mark_seen("<msg1@mail>")
    store.mark_seen("<msg1@mail>")
    assert store.is_seen("<msg1@mail>") is True


def test_add_and_find_application_by_company(store):
    app_id = store.add_application("Acme", role="SWE Intern")
    found = store.find_by_company("Acme")
    assert len(found) == 1
    assert found[0]["id"] == app_id
    assert found[0]["role"] == "SWE Intern"


def test_company_lookup_is_case_insensitive(store):
    store.add_application("Acme")
    assert len(store.find_by_company("acme")) == 1
    assert len(store.find_by_company("ACME")) == 1


def test_update_status(store):
    app_id = store.add_application("Acme")
    store.update_status(app_id, "interview")
    assert store.find_by_company("Acme")[0]["status"] == "interview"


def test_flag_for_review(store):
    app_id = store.add_application("Acme")
    store.flag_for_review(app_id, "two open applications")
    flagged = store.needing_review()
    assert len(flagged) == 1
    assert flagged[0]["review_reason"] == "two open applications"


def test_events_attach_to_application(store):
    app_id = store.add_application("Acme")
    store.add_event(app_id, message_id="<m1>", subject="Thanks for applying")
    events = store.events_for(app_id)
    assert len(events) == 1
    assert events[0]["subject"] == "Thanks for applying"
