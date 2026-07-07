"""Tests for reminders/checks.py: the leetcode nag, job alerts, toggles,
and once-per-day dedup. Network, gmail, and notify are all mocked."""

from datetime import datetime
from unittest.mock import patch

import pytest

from brain.memory_manager import MemoryManager
from reminders import checks
from tracker.store import TrackerStore


@pytest.fixture
def memory():
    m = MemoryManager(":memory:")
    yield m
    m.close()


@pytest.fixture
def store():
    s = TrackerStore(":memory:")
    yield s
    s.close()


EVENING = datetime(2026, 7, 7, 20, 0)
TODAY_TS = str(int(EVENING.timestamp()))
LAST_WEEK_TS = str(int(datetime(2026, 6, 30, 12, 0).timestamp()))


# ---- solved_leetcode_today ----

def test_solved_today_true(monkeypatch):
    monkeypatch.setattr("config.settings.LEETCODE_USERNAME", "Ghostellor")
    with patch("brain.tools.leetcode._get",
               return_value={"submission": [{"title": "Two Sum", "timestamp": TODAY_TS}]}):
        assert checks.solved_leetcode_today(EVENING) is True


def test_solved_today_false_when_only_old(monkeypatch):
    monkeypatch.setattr("config.settings.LEETCODE_USERNAME", "Ghostellor")
    with patch("brain.tools.leetcode._get",
               return_value={"submission": [{"title": "Old", "timestamp": LAST_WEEK_TS}]}):
        assert checks.solved_leetcode_today(EVENING) is False


def test_solved_today_none_when_api_down(monkeypatch):
    monkeypatch.setattr("config.settings.LEETCODE_USERNAME", "Ghostellor")
    with patch("brain.tools.leetcode._get", side_effect=OSError("down")):
        assert checks.solved_leetcode_today(EVENING) is None


def test_solved_today_none_without_username(monkeypatch):
    monkeypatch.setattr("config.settings.LEETCODE_USERNAME", "")
    assert checks.solved_leetcode_today(EVENING) is None


# ---- leetcode_reminder ----

def test_reminder_sent_when_not_solved(memory):
    with patch("reminders.checks.solved_leetcode_today", return_value=False), \
         patch("reminders.checks._daily_suggestion", return_value=""), \
         patch("reminders.checks.notify", return_value=True) as sent:
        result = checks.leetcode_reminder(memory, EVENING)
    assert result == "reminder sent"
    sent.assert_called_once()
    assert "LeetCode" in sent.call_args[0][0]


def test_no_reminder_when_solved(memory):
    with patch("reminders.checks.solved_leetcode_today", return_value=True), \
         patch("reminders.checks.notify") as sent:
        result = checks.leetcode_reminder(memory, EVENING)
    assert "no reminder needed" in result
    sent.assert_not_called()


def test_reminder_only_once_per_day(memory):
    with patch("reminders.checks.solved_leetcode_today", return_value=False), \
         patch("reminders.checks._daily_suggestion", return_value=""), \
         patch("reminders.checks.notify", return_value=True) as sent:
        checks.leetcode_reminder(memory, EVENING)
        result = checks.leetcode_reminder(memory, EVENING)
    assert result == "already reminded today"
    assert sent.call_count == 1


def test_reminder_respects_toggle_off(memory):
    memory.set_state(checks.PREF_LEETCODE, "off")
    with patch("reminders.checks.notify") as sent:
        result = checks.leetcode_reminder(memory, EVENING)
    assert result == "leetcode reminders are off"
    sent.assert_not_called()


def test_failed_send_does_not_mark_sent(memory):
    with patch("reminders.checks.solved_leetcode_today", return_value=False), \
         patch("reminders.checks._daily_suggestion", return_value=""), \
         patch("reminders.checks.notify", return_value=False):
        checks.leetcode_reminder(memory, EVENING)
    assert memory.get_state(checks.LAST_SENT_KEY) == ""


def test_api_down_skips_quietly(memory):
    with patch("reminders.checks.solved_leetcode_today", return_value=None), \
         patch("reminders.checks.notify") as sent:
        result = checks.leetcode_reminder(memory, EVENING)
    assert "skipped" in result
    sent.assert_not_called()


# ---- job_application_alert ----

def _msg(message_id, sender, subject):
    return {"message_id": message_id, "sender": sender,
            "subject": subject, "date": "", "snippet": ""}


def test_job_alert_texts_new_applications(memory, store):
    fetch = lambda: [_msg("<m1>", "jobs@acme.com", "Thanks for applying")]
    with patch("reminders.checks.notify", return_value=True) as sent:
        result = checks.job_application_alert(memory, store, fetch)
    assert "1 item" in result
    assert "Acme" in sent.call_args[0][0]


def test_job_alert_silent_when_nothing_new(memory, store):
    fetch = lambda: [_msg("<m1>", "jobs@acme.com", "Thanks")]
    with patch("reminders.checks.notify", return_value=True):
        checks.job_application_alert(memory, store, fetch)
    # Same message again: seen set swallows it, no second text.
    with patch("reminders.checks.notify") as sent:
        result = checks.job_application_alert(memory, store, fetch)
    assert result == "nothing new"
    sent.assert_not_called()


def test_job_alert_respects_toggle_off(memory, store):
    memory.set_state(checks.PREF_JOBS, "off")
    with patch("reminders.checks.notify") as sent:
        result = checks.job_application_alert(memory, store, lambda: [])
    assert result == "job alerts are off"
    sent.assert_not_called()


def test_job_alert_survives_gmail_failure(memory, store):
    def broken_fetch():
        raise RuntimeError("imap down")
    result = checks.job_application_alert(memory, store, broken_fetch)
    assert "could not read gmail" in result


# ---- run_due_checks timing ----

def test_leetcode_skipped_before_evening(memory):
    noon = datetime(2026, 7, 7, 12, 0)
    with patch("reminders.checks.job_application_alert", return_value="nothing new"):
        results = checks.run_due_checks(memory, noon)
    assert "too early" in results["leetcode"]


def test_leetcode_runs_in_the_evening(memory):
    with patch("reminders.checks.job_application_alert", return_value="nothing new"), \
         patch("reminders.checks.leetcode_reminder", return_value="reminder sent") as nag:
        results = checks.run_due_checks(memory, EVENING)
    nag.assert_called_once()
    assert results["leetcode"] == "reminder sent"
