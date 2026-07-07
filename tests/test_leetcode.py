"""Tests for brain/tools/leetcode.py with the HTTP layer mocked."""

from unittest.mock import patch

import requests

from brain.tools import leetcode


SOLVED = {"solvedProblem": 54, "easySolved": 49, "mediumSolved": 5, "hardSolved": 0}
RECENT = {"submission": [
    {"title": "Two Sum", "lang": "python3"},
    {"title": "Valid Anagram", "lang": "python3"},
]}
DAILY = {
    "questionTitle": "Find the Safest Path in a Grid",
    "difficulty": "Medium",
    "questionLink": "https://leetcode.com/problems/find-the-safest-path-in-a-grid/",
    "topicTags": [{"name": "Array"}, {"name": "Matrix"}],
}


def test_progress_without_username(monkeypatch):
    monkeypatch.setattr("config.settings.LEETCODE_USERNAME", "")
    result = leetcode.get_leetcode_progress()
    assert "LEETCODE_USERNAME" in result


def test_progress_formats_counts(monkeypatch):
    monkeypatch.setattr("config.settings.LEETCODE_USERNAME", "Ghostellor")
    with patch("brain.tools.leetcode._get", side_effect=[SOLVED, RECENT]):
        result = leetcode.get_leetcode_progress()
    assert "Total solved: 54" in result
    assert "Easy: 49" in result
    assert "Two Sum" in result


def test_progress_timeout_is_friendly(monkeypatch):
    monkeypatch.setattr("config.settings.LEETCODE_USERNAME", "Ghostellor")
    with patch("brain.tools.leetcode._get",
               side_effect=requests.exceptions.Timeout()):
        result = leetcode.get_leetcode_progress()
    assert "waking up" in result


def test_progress_error_is_contained(monkeypatch):
    monkeypatch.setattr("config.settings.LEETCODE_USERNAME", "Ghostellor")
    with patch("brain.tools.leetcode._get", side_effect=RuntimeError("boom")):
        result = leetcode.get_leetcode_progress()
    assert "Could not reach" in result


def test_daily_formats_question():
    with patch("brain.tools.leetcode._get", return_value=DAILY):
        result = leetcode.get_leetcode_daily()
    assert "Find the Safest Path in a Grid" in result
    assert "Medium" in result
    assert "Array" in result
    assert "leetcode.com/problems" in result


def test_daily_timeout_is_friendly():
    with patch("brain.tools.leetcode._get",
               side_effect=requests.exceptions.Timeout()):
        result = leetcode.get_leetcode_daily()
    assert "waking up" in result
