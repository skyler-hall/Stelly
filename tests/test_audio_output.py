"""Tests for engine selection, piper plumbing, and the robot effect in
output/audio_output.py. No sound is played, everything external is
mocked or checked as pure logic."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import patch

import numpy as np

import output.audio_output as audio
from output.audio_output import PiperEngine, robotize


def _piper_configured(monkeypatch, tmp_path):
    exe = tmp_path / "piper.exe"
    model = tmp_path / "voice.onnx"
    exe.write_bytes(b"x")
    model.write_bytes(b"x")
    monkeypatch.setattr("config.settings.PIPER_EXE", str(exe))
    monkeypatch.setattr("config.settings.PIPER_VOICE", str(model))


# ---- engine availability and selection ----

def test_piper_unavailable_when_unconfigured(monkeypatch):
    monkeypatch.setattr("config.settings.PIPER_EXE", "")
    monkeypatch.setattr("config.settings.PIPER_VOICE", "")
    assert PiperEngine.available() is False


def test_piper_unavailable_when_files_missing(monkeypatch):
    monkeypatch.setattr("config.settings.PIPER_EXE", "C:/nope/piper.exe")
    monkeypatch.setattr("config.settings.PIPER_VOICE", "C:/nope/voice.onnx")
    assert PiperEngine.available() is False


def test_piper_available_when_both_files_exist(monkeypatch, tmp_path):
    _piper_configured(monkeypatch, tmp_path)
    assert PiperEngine.available() is True


def test_build_command_shape(monkeypatch, tmp_path):
    _piper_configured(monkeypatch, tmp_path)
    monkeypatch.setattr("config.settings.PIPER_SPEAKER", "")
    command = PiperEngine()._build_command("out.wav")
    assert command[0].endswith("piper.exe")
    assert "--model" in command
    assert "--output_file" in command
    assert "--noise_scale" in command
    assert "--length_scale" in command
    assert "--speaker" not in command  # only for multi-speaker models


def test_build_command_includes_speaker_when_set(monkeypatch, tmp_path):
    _piper_configured(monkeypatch, tmp_path)
    monkeypatch.setattr("config.settings.PIPER_SPEAKER", "42")
    command = PiperEngine()._build_command("out.wav")
    assert "--speaker" in command
    assert "42" in command


def test_engine_choice_prefers_piper(monkeypatch, tmp_path):
    _piper_configured(monkeypatch, tmp_path)
    monkeypatch.setattr(audio, "_engine", None)
    assert isinstance(audio._get_engine(), PiperEngine)
    monkeypatch.setattr(audio, "_engine", None)  # reset for other tests


def test_engine_choice_falls_back_without_piper(monkeypatch):
    monkeypatch.setattr("config.settings.PIPER_EXE", "")
    monkeypatch.setattr("config.settings.PIPER_VOICE", "")
    monkeypatch.setattr(audio, "_engine", None)
    engine = audio._get_engine()
    assert isinstance(engine, audio.Pyttsx3Engine)
    monkeypatch.setattr(audio, "_engine", None)


# ---- the robot effect ----

def _tone(seconds=0.1, rate=22050, hz=440, amplitude=10000):
    t = np.arange(int(seconds * rate)) / rate
    return (amplitude * np.sin(2 * np.pi * hz * t)).astype(np.int16), rate


def test_robotize_zero_mix_returns_input_unchanged():
    samples, rate = _tone()
    out = robotize(samples, rate, mix=0.0)
    assert np.array_equal(out, samples)


def test_robotize_changes_the_audio():
    samples, rate = _tone()
    out = robotize(samples, rate, mix=0.5)
    assert out.dtype == np.int16
    assert len(out) == len(samples)
    assert not np.array_equal(out, samples)


def test_robotize_full_mix_is_ring_modulated():
    samples, rate = _tone()
    out = robotize(samples, rate, mix=1.0)
    # Ring modulation by a sine passes through zero, so the output must
    # dip to silence at the carrier's zero crossings even mid-tone.
    assert out.min() < samples.min() or abs(out).min() < abs(samples).max() * 0.05


def test_robotize_never_clips_out_of_int16():
    loud = np.full(1000, 32767, dtype=np.int16)
    out = robotize(loud, 22050, mix=1.0)
    assert out.max() <= 32767 and out.min() >= -32768


def test_robotize_is_deterministic():
    samples, rate = _tone()
    assert np.array_equal(robotize(samples, rate, 0.3), robotize(samples, rate, 0.3))


# ---- speak() safety net ----

def test_speak_never_raises(monkeypatch):
    monkeypatch.setattr(audio, "_engine", None)
    with patch.object(audio, "_get_engine", side_effect=RuntimeError("no audio")):
        audio.speak("hello")  # must swallow the error, not raise


def test_speak_ignores_empty_text(monkeypatch):
    with patch.object(audio, "_get_engine") as get:
        audio.speak("")
    get.assert_not_called()
