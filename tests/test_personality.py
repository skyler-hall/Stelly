"""Tests for brain/stelly_personality.py prompt building."""

from brain import stelly_personality as sp


def test_known_mood_is_in_prompt():
    prompt = sp.get_system_prompt("happy")
    assert sp.MOOD_MODIFIERS["happy"] in prompt


def test_unknown_mood_falls_back_to_default():
    prompt = sp.get_system_prompt("confuzzled")
    assert sp.MOOD_MODIFIERS[sp.DEFAULT_MOOD] in prompt


def test_prompt_demands_mood_tag():
    prompt = sp.get_system_prompt()
    assert "[neutral]" in prompt and "[happy]" in prompt


def test_memories_are_woven_in_when_given():
    prompt = sp.get_system_prompt("neutral", memories=["Skyler likes robots"])
    assert "Skyler likes robots" in prompt


def test_no_memories_section_when_none():
    prompt = sp.get_system_prompt("neutral", memories=[])
    assert "Things you remember" not in prompt
