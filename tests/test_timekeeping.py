"""Tests for config/timekeeping.py, the shared day/night logic."""

from datetime import datetime

from config import timekeeping as tk


def test_noon_is_daytime():
    assert tk.is_daytime(datetime(2026, 7, 1, 12, 0)) is True


def test_just_before_day_starts_is_night():
    assert tk.is_daytime(datetime(2026, 7, 1, 6, 59)) is False


def test_day_start_boundary_is_day():
    assert tk.is_daytime(datetime(2026, 7, 1, 7, 0)) is True


def test_night_start_boundary_is_night():
    assert tk.is_daytime(datetime(2026, 7, 1, 19, 0)) is False


def test_next_transition_from_midday_is_tonight():
    assert tk.next_transition(datetime(2026, 7, 1, 12, 0)) == datetime(2026, 7, 1, 19, 0)


def test_next_transition_from_evening_is_tomorrow_morning():
    assert tk.next_transition(datetime(2026, 7, 1, 20, 0)) == datetime(2026, 7, 2, 7, 0)


def test_next_transition_from_early_morning_is_this_morning():
    assert tk.next_transition(datetime(2026, 7, 1, 3, 0)) == datetime(2026, 7, 1, 7, 0)


def test_next_transition_is_always_in_the_future():
    moments = [datetime(2026, 7, 1, h, 30) for h in range(24)]
    for moment in moments:
        assert tk.next_transition(moment) > moment
