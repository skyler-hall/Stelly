"""Tests for jobs/store.py using a throwaway in-memory database."""

import pytest

from jobs.store import JobAlertStore


@pytest.fixture
def store():
    s = JobAlertStore(":memory:")
    yield s
    s.close()


def test_unnotified_job_is_not_notified(store):
    assert store.is_notified("simplify:abc") is False


def test_marked_job_is_notified(store):
    store.mark_notified("simplify:abc")
    assert store.is_notified("simplify:abc") is True


def test_marking_twice_is_harmless(store):
    store.mark_notified("simplify:abc")
    store.mark_notified("simplify:abc")
    assert store.is_notified("simplify:abc") is True


def test_ids_from_different_sources_are_independent(store):
    store.mark_notified("simplify:abc")
    assert store.is_notified("ba:abc") is False
