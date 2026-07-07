"""Tests for tracker/pipeline.py, the fetch-to-storage assembly line."""

import pytest

from tracker.pipeline import process_messages
from tracker.store import TrackerStore


@pytest.fixture
def store():
    s = TrackerStore(":memory:")
    yield s
    s.close()


def _msg(message_id, sender, subject="Thanks for applying!"):
    return {"message_id": message_id, "sender": sender,
            "subject": subject, "date": "", "snippet": ""}


def test_new_company_creates_application(store):
    summary = process_messages(store, [_msg("<m1>", "jobs@acme.com")])
    assert summary["new"] == 1
    apps = store.find_by_company("Acme")
    assert len(apps) == 1
    assert len(store.events_for(apps[0]["id"])) == 1


def test_second_email_from_same_company_matches(store):
    process_messages(store, [_msg("<m1>", "jobs@acme.com")])
    summary = process_messages(store, [_msg("<m2>", "recruiter@acme.com", "Interview!")])
    assert summary["matched"] == 1
    apps = store.find_by_company("Acme")
    assert len(apps) == 1  # still one application, two events
    assert len(store.events_for(apps[0]["id"])) == 2


def test_duplicate_message_id_is_skipped(store):
    process_messages(store, [_msg("<m1>", "jobs@acme.com")])
    summary = process_messages(store, [_msg("<m1>", "jobs@acme.com")])
    assert summary["skipped_seen"] == 1
    assert len(store.find_by_company("Acme")) == 1


def test_two_open_applications_flags_ambiguous(store):
    store.add_application("Acme", role="SWE")
    store.add_application("Acme", role="Data")
    summary = process_messages(store, [_msg("<m1>", "jobs@acme.com")])
    assert summary["ambiguous"] == 1
    assert len(store.needing_review()) == 1
    # Crucially: no third application was invented.
    assert len(store.find_by_company("Acme")) == 2


def test_unextractable_company_is_parked_for_review(store):
    summary = process_messages(store, [_msg("<m1>", "No Reply <no@linkedin.com>")])
    assert summary["unparseable"] == 1
    flagged = store.needing_review()
    assert len(flagged) == 1
    assert flagged[0]["company"] == "(unknown)"


def test_message_without_id_is_counted_not_stored(store):
    summary = process_messages(store, [_msg("", "jobs@acme.com")])
    assert summary["unparseable"] == 1
    assert store.all_applications() == []


def test_details_describe_what_happened(store):
    process_messages(store, [_msg("<m1>", "jobs@acme.com", "Thanks for applying!")])
    summary = process_messages(store, [_msg("<m2>", "hr@acme.com", "Interview invite")])
    assert summary["details"] == ["Update from Acme: Interview invite"]


def test_rerun_is_idempotent(store):
    messages = [_msg("<m1>", "jobs@acme.com"), _msg("<m2>", "hi@globex.com")]
    process_messages(store, messages)
    before = store.all_applications()
    process_messages(store, messages)
    assert store.all_applications() == before
