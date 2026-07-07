"""Tests for the voice toggle tools in brain/tools/preferences.py."""

import pytest

from brain import tools
from brain.memory_manager import MemoryManager
from brain.tools import preferences


@pytest.fixture
def memory(monkeypatch):
    m = MemoryManager(":memory:")
    monkeypatch.setattr("brain.tools.preferences.get_manager", lambda: m)
    yield m
    m.close()


def test_turning_off_persists(memory):
    preferences.set_notification_preference("leetcode_reminders", False)
    assert memory.get_state("pref_leetcode_reminders") == "off"


def test_turning_back_on_persists(memory):
    preferences.set_notification_preference("job_alerts", False)
    preferences.set_notification_preference("job_alerts", True)
    assert memory.get_state("pref_job_alerts") == "on"


def test_reply_is_speakable(memory):
    reply = preferences.set_notification_preference("leetcode_reminders", False)
    assert "leetcode reminders" in reply
    assert "off" in reply


def test_unknown_feature_is_rejected(memory):
    reply = preferences.set_notification_preference("carrier_pigeon", True)
    assert "Unknown feature" in reply


def test_status_report_lists_both(memory):
    preferences.set_notification_preference("leetcode_reminders", False)
    report = preferences.get_notification_preferences()
    assert "leetcode reminders: off" in report
    assert "job alerts: on" in report


def test_tools_are_registered():
    assert "set_notification_preference" in tools.TOOL_FUNCTIONS
    assert "get_notification_preferences" in tools.TOOL_FUNCTIONS
    names = [t["name"] for t in tools.TOOL_DEFINITIONS]
    assert "set_notification_preference" in names
