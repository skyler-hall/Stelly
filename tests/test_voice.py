"""Tests for the VoiceLab engine in output/audio_output.py and the voice
switching tools in brain/tools/voice.py. VoiceLab itself is replaced by a
small fake, so no voice files are needed and no sound is played."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
import types

import numpy as np
import pytest

import output.audio_output as audio
from brain import tools
from brain.memory_manager import MemoryManager
from brain.tools import voice


class FakeVoiceLab:
    """Just enough of voicelab.py: a catalog, readiness, render, play."""

    def __init__(self, presets, ready):
        self.presets = presets
        self.ready = set(ready)
        self.rendered = []
        self.played = []

    def load_catalog(self):
        return {"presets": {name: {"settings": {"voice": name}} for name in self.presets}}

    def preset_ready(self, name):
        if name not in self.presets:
            raise KeyError(name)
        return name in self.ready

    def get_preset(self, name):
        return {"voice": name}

    def render_stereo(self, settings, text):
        self.rendered.append((settings["voice"], text))
        return np.zeros((10, 2), dtype=np.float32), 22050

    def play(self, audio_data, sample_rate, wait=True):
        self.played.append(len(self.rendered))  # how many renders existed when this played


@pytest.fixture
def memory(monkeypatch):
    m = MemoryManager(":memory:")
    monkeypatch.setattr("brain.memory_manager.get_manager", lambda: m)
    monkeypatch.setattr("brain.tools.voice.get_manager", lambda: m)
    yield m
    m.close()


@pytest.fixture
def fake_lab(monkeypatch, memory):
    lab = FakeVoiceLab(["Stelly V1", "The Henchman", "The Deep Voice", "Deep Robot Voice"],
                       ready=["Stelly V1", "The Henchman", "Deep Robot Voice"])
    monkeypatch.setattr(audio, "_voicelab", lab)
    monkeypatch.setattr(audio, "_voicelab_checked", True)
    monkeypatch.setattr(audio, "_engine", None)
    monkeypatch.setattr("config.settings.VOICE_PRESET", "Stelly V1")
    monkeypatch.setitem(sys.modules, "sounddevice", types.SimpleNamespace(wait=lambda: None))
    yield lab
    audio._engine = None


@pytest.fixture
def no_lab(monkeypatch, memory):
    monkeypatch.setattr(audio, "_voicelab", None)
    monkeypatch.setattr(audio, "_voicelab_checked", True)
    monkeypatch.setattr(audio, "_engine", None)
    yield
    audio._engine = None


# ---- splitting replies into sentences ----

def test_split_keeps_long_sentences_apart():
    text = "Stelly checked your LeetCode today. No problem solved yet, one little problem before bed?"
    assert audio.split_sentences(text) == [
        "Stelly checked your LeetCode today.",
        "No problem solved yet, one little problem before bed?",
    ]


def test_split_joins_short_exclamations_to_the_next_sentence():
    chunks = audio.split_sentences("Oh! You are home! Stelly is so happy to see you today.")
    assert chunks[0].startswith("Oh! You are home!")
    assert all(len(c) >= audio.MIN_CHUNK_CHARS for c in chunks[:-1])


def test_split_handles_empty_and_no_punctuation():
    assert audio.split_sentences("") == []
    assert audio.split_sentences("hello there") == ["hello there"]


# ---- engine choice ----

def test_voicelab_is_preferred_when_preset_is_ready(fake_lab):
    assert isinstance(audio._get_engine(), audio.VoiceLabEngine)


def test_falls_back_when_starting_preset_is_not_synced(fake_lab, monkeypatch):
    monkeypatch.setattr("config.settings.VOICE_PRESET", "The Deep Voice")  # in catalog, files missing
    monkeypatch.setattr("config.settings.PIPER_EXE", "")
    monkeypatch.setattr("config.settings.PIPER_VOICE", "")
    assert not isinstance(audio._get_engine(), audio.VoiceLabEngine)


def test_falls_back_without_voicelab(no_lab, monkeypatch):
    monkeypatch.setattr("config.settings.PIPER_EXE", "")
    monkeypatch.setattr("config.settings.PIPER_VOICE", "")
    assert isinstance(audio._get_engine(), audio.Pyttsx3Engine)


def test_ready_presets_lists_only_synced_voices(fake_lab):
    assert audio.ready_presets() == ["Stelly V1", "The Henchman", "Deep Robot Voice"]


def test_ready_presets_empty_without_voicelab(no_lab):
    assert audio.ready_presets() == []


# ---- speaking ----

def test_say_renders_ahead_of_playback(fake_lab):
    audio.VoiceLabEngine().say("Stelly checked the clock for you. It is daytime, nice and bright.")
    assert [t for _, t in fake_lab.rendered] == [
        "Stelly checked the clock for you.",
        "It is daytime, nice and bright.",
    ]
    # The first sentence played after one render, and the second was
    # rendered while it played, before the second play started.
    assert fake_lab.played == [1, 2]


def test_say_uses_the_chosen_voice(fake_lab, memory):
    memory.set_state(audio.VOICE_STATE_KEY, "The Henchman")
    audio.VoiceLabEngine().say("Good evening, Skyler.")
    assert fake_lab.rendered[0][0] == "The Henchman"


def test_chosen_voice_not_synced_falls_back_to_starting_voice(fake_lab, memory):
    memory.set_state(audio.VOICE_STATE_KEY, "The Deep Voice")
    assert audio.current_preset() == "Stelly V1"


def _wait_for(condition, seconds=2.0):
    import time
    end = time.time() + seconds
    while time.time() < end and not condition():
        time.sleep(0.01)
    return condition()


def test_warm_up_loads_the_voice_in_the_background(fake_lab):
    audio.warm_up()
    assert _wait_for(lambda: fake_lab.rendered == [("Stelly V1", "Hi.")])
    assert fake_lab.played == []  # silent


def test_warm_up_without_voicelab_does_nothing(no_lab):
    audio.warm_up()  # must not raise


# ---- the set_voice and list_voices tools ----

@pytest.mark.parametrize("asked", ["The Henchman", "henchman", "the henchman", "HENCHMAN voice"])
def test_set_voice_matches_loose_names(fake_lab, memory, asked):
    reply = voice.set_voice(asked)
    assert "The Henchman" in reply
    assert memory.get_state(audio.VOICE_STATE_KEY) == "The Henchman"


def test_set_voice_persists_and_is_used(fake_lab, memory):
    voice.set_voice("deep robot")
    assert audio.current_preset() == "Deep Robot Voice"


def test_set_voice_rejects_unknown(fake_lab, memory):
    reply = voice.set_voice("pirate")
    assert "doesn't have a voice called pirate" in reply
    assert "The Henchman" in reply
    assert memory.get_state(audio.VOICE_STATE_KEY) == ""


def test_set_voice_skips_voices_not_synced_here(fake_lab, memory):
    reply = voice.set_voice("The Deep Voice")
    assert "doesn't have a voice called" in reply


def test_ambiguous_partial_match_is_rejected(fake_lab):
    assert voice.match_voice("deep", ["The Deep Voice", "Deep Robot Voice"]) is None


def test_set_voice_default_goes_back_to_normal(fake_lab, memory):
    voice.set_voice("henchman")
    reply = voice.set_voice("default")
    assert "normal voice" in reply
    assert audio.current_preset() == "Stelly V1"


def test_set_voice_without_voicelab(no_lab):
    assert "isn't set up" in voice.set_voice("henchman")


def test_list_voices_marks_current(fake_lab, memory):
    voice.set_voice("henchman")
    report = voice.list_voices()
    assert "The Henchman (using now)" in report
    assert "Stelly V1" in report
    assert "The Deep Voice" not in report  # not synced here


def test_voice_tools_are_registered():
    assert "set_voice" in tools.TOOL_FUNCTIONS
    assert "list_voices" in tools.TOOL_FUNCTIONS
    names = [t["name"] for t in tools.TOOL_DEFINITIONS]
    assert "set_voice" in names and "list_voices" in names
