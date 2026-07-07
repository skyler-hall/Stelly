"""Tests for the mood tag parser in brain/ai_handler.py."""

from brain.ai_handler import _split_mood


def test_valid_tag_is_split_off():
    text, mood = _split_mood("[happy] Stelly is glad!")
    assert text == "Stelly is glad!"
    assert mood == "happy"


def test_tag_is_case_insensitive():
    text, mood = _split_mood("[EXCITED] Ooh!")
    assert text == "Ooh!"
    assert mood == "excited"


def test_leading_whitespace_is_tolerated():
    text, mood = _split_mood("  [sad] oh.")
    assert text == "oh."
    assert mood == "sad"


def test_missing_tag_keeps_fallback_mood():
    text, mood = _split_mood("no tag here", fallback="sleepy")
    assert text == "no tag here"
    assert mood == "sleepy"


def test_unknown_mood_is_not_stripped():
    text, mood = _split_mood("[bogus] hmm", fallback="neutral")
    assert text == "[bogus] hmm"
    assert mood == "neutral"


def test_every_valid_mood_parses():
    from brain.stelly_personality import VALID_MOODS
    for valid in VALID_MOODS:
        text, mood = _split_mood(f"[{valid}] words")
        assert mood == valid
        assert text == "words"
