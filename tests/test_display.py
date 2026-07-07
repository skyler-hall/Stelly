"""Tests for the pure logic in output/display.py, run headless with
SDL dummy drivers so no window or audio device is needed."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from output.display import Face, MOOD_EXPRESSIONS


@pytest.fixture(scope="module")
def face():
    f = Face()
    yield f


def test_every_mood_has_an_expression():
    for mood in ("neutral", "happy", "excited", "sad", "sleepy", "worried"):
        assert mood in MOOD_EXPRESSIONS


def test_unknown_mood_is_ignored(face):
    face.set_mood("happy")
    face.set_mood("gibberish")
    assert face.mood == "happy"


def test_quiet_face_shows_resting_expression(face):
    face.set_mood("neutral")
    face.set_talking(False)
    assert face._current_expression() == "smile"


def test_talking_face_alternates_mouth(face):
    face.set_mood("neutral")
    face.set_talking(True)
    seen = set()
    original = face.start_time
    try:
        # Sample the flap at both phases of its cycle by shifting the clock.
        face.start_time -= 0.0
        seen.add(face._current_expression())
        face.start_time -= 0.16
        seen.add(face._current_expression())
    finally:
        face.start_time = original
        face.set_talking(False)
    assert "gulp" in seen and "smile" in seen


def test_talking_gulp_mood_still_alternates(face):
    face.set_mood("happy")  # resting expression is gulp
    face.set_talking(True)
    original = face.start_time
    try:
        seen = set()
        seen.add(face._current_expression())
        face.start_time -= 0.16
        seen.add(face._current_expression())
    finally:
        face.start_time = original
        face.set_talking(False)
    assert seen == {"gulp", "smile"}


def test_manual_theme_sets_override(face):
    face.set_theme("dark")
    assert face.theme_name == "dark"
    assert face._override_until is not None


def test_tick_runs_headless(face):
    for _ in range(3):
        assert face.tick() is True
