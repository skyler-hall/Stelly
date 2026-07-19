"""
Stelly's voice.

speak(text) says the words out loud and blocks until done, which is
exactly what the main loop wants: it flips the face into talking mode,
calls speak, and flips it back when speak returns.

One real voice, everywhere: Piper, a neural TTS that runs fully local
and identical on Windows, Mac, and the Pi, so Stelly sounds like
himself on every machine with no cloud, no keys, no cost. Two knobs
shape the character:

  STELLY_PIPER_PITCH  playback rate trick, above 1.0 is smaller and
                      younger (and slightly faster), 1.15 to 1.3 is the
                      companion-robot zone.
  STELLY_ROBOT_FX     ring modulation mix, 0.0 natural to 1.0 full
                      robot. Multiplying the voice by a low sine wave
                      is the classic hardware robot-voice trick (it is
                      literally how old sci-fi did it), around 0.2 to
                      0.35 adds a digital game-console shimmer without
                      hurting clarity.

Pyttsx3Engine stays as the fallback when Piper is not configured, using
whatever voice the operating system has, so Stelly is never mute.

pyttsx3 quirk worth knowing: reusing one engine across many runAndWait
calls is unreliable on some platforms, so it builds a fresh engine per
utterance, a few milliseconds that dodge a whole bug class.
"""

import subprocess
import tempfile
import time
import wave
from pathlib import Path

import numpy as np
import pygame
import pyttsx3

from config import settings

PIPER_TIMEOUT_SECONDS = 60
ROBOT_CARRIER_HZ = 55  # ring mod carrier, lower hums, higher rings metallic


def robotize(samples, sample_rate, mix, carrier_hz=ROBOT_CARRIER_HZ):
    """Blend a ring modulated copy into the voice. samples is int16
    mono audio as a numpy array, mix runs 0.0 (untouched) to 1.0 (full
    effect). Pure function so it is easy to test and easy to tune."""
    if mix <= 0:
        return samples
    voice = samples.astype(np.float32)
    t = np.arange(len(voice)) / sample_rate
    carrier = np.sin(2 * np.pi * carrier_hz * t).astype(np.float32)
    blended = (1.0 - mix) * voice + mix * (voice * carrier)
    return np.clip(blended, -32768, 32767).astype(np.int16)


class PiperEngine:
    """Stelly's real voice: local neural TTS plus the character knobs."""

    def _build_command(self, wav_path):
        """The piper invocation. Text goes in over stdin, wav comes out.
        Noise and length shape the delivery (flatness and pacing),
        speaker picks a voice inside multi-speaker models."""
        command = [settings.PIPER_EXE,
                   "--model", settings.PIPER_VOICE,
                   "--output_file", str(wav_path),
                   "--noise_scale", str(settings.PIPER_NOISE),
                   "--length_scale", str(settings.PIPER_LENGTH)]
        if settings.PIPER_SPEAKER:
            command += ["--speaker", settings.PIPER_SPEAKER]
        return command

    def say(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "stelly_says.wav"
            subprocess.run(
                self._build_command(wav_path),
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=PIPER_TIMEOUT_SECONDS,
                check=True,
            )
            self._apply_effects(wav_path)
            self._play(wav_path)

    @staticmethod
    def _apply_effects(wav_path):
        """Run the robot effect over the rendered wav, in place."""
        if settings.ROBOT_FX <= 0:
            return
        with wave.open(str(wav_path), "rb") as wav:
            params = wav.getparams()
            frames = wav.readframes(params.nframes)
        samples = np.frombuffer(frames, dtype=np.int16)
        processed = robotize(samples, params.framerate, settings.ROBOT_FX,
                             carrier_hz=settings.ROBOT_CARRIER)
        with wave.open(str(wav_path), "wb") as wav:
            wav.setparams(params)
            wav.writeframes(processed.tobytes())

    @staticmethod
    def _play(wav_path):
        """Play a wav through pygame's mixer at a pitched-up rate.

        The mixer gets reinitialized per utterance at the wav's sample
        rate times the pitch factor. pygame does not resample sounds to
        match the mixer, which is normally a gotcha and here is exactly
        the feature: a 22050Hz wav on a 25400Hz mixer plays higher.
        """
        with wave.open(str(wav_path), "rb") as wav:
            rate = wav.getframerate()

        pygame.mixer.quit()
        pygame.mixer.init(frequency=int(rate * settings.PIPER_PITCH))
        sound = pygame.mixer.Sound(str(wav_path))
        channel = sound.play()
        while channel.get_busy():
            time.sleep(0.05)

    @staticmethod
    def available():
        return bool(settings.PIPER_EXE and settings.PIPER_VOICE
                    and Path(settings.PIPER_EXE).exists()
                    and Path(settings.PIPER_VOICE).exists())


class Pyttsx3Engine:
    """Cross-platform system voices via pyttsx3, the zero-setup fallback.

    Voice choice and speed come from .env (STELLY_VOICE, STELLY_VOICE_RATE)
    since the installed voices differ on every machine.
    """

    def say(self, text):
        engine = pyttsx3.init()  # fresh engine per call, see module docstring
        engine.setProperty("rate", settings.VOICE_RATE)
        if settings.VOICE_NAME:
            for voice in engine.getProperty("voices"):
                if settings.VOICE_NAME.lower() in voice.name.lower():
                    engine.setProperty("voice", voice.id)
                    break
        engine.say(text)
        engine.runAndWait()
        engine.stop()

    @staticmethod
    def available():
        try:
            pyttsx3.init().stop()
            return True
        except Exception:
            return False


_engine = None


def _get_engine():
    """Pick the best engine available, once per process. Piper when
    configured, system voice otherwise."""
    global _engine
    if _engine is None:
        if PiperEngine.available():
            print("(voice: piper)")
            _engine = PiperEngine()
        else:
            print("(voice: system fallback, configure Piper for the real voice)")
            _engine = Pyttsx3Engine()
    return _engine


def speak(text):
    """Say text out loud. Blocks until the audio finishes.

    Never raises: a broken audio device should mute Stelly, not crash
    him. The text still gets printed by the caller either way.
    """
    if not text:
        return
    try:
        _get_engine().say(text)
    except Exception as error:
        print(f"(voice failed: {error})")


if __name__ == "__main__":
    # Manual check. With Piper configured this speaks a Stelly line in
    # the real voice with the current pitch and robot settings, so tune
    # .env and rerun until he sounds right. Otherwise it auditions the
    # system voices so you can pick a fallback (STELLY_VOICE=name).
    TEST_LINE = ("Oh! You are home! Stelly is so happy to see you! "
                 "Stelly learned something today. Stelly wants to remember this one forever.")

    if PiperEngine.available():
        print(f"Piper voice: {settings.PIPER_VOICE}")
        print(f"pitch {settings.PIPER_PITCH}, robot fx {settings.ROBOT_FX}")
        speak(TEST_LINE)
    else:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        engine.stop()
        print(f"Piper not configured. {len(voices)} system voices installed:\n")
        for voice in voices:
            print(f"  {voice.name}")
        print("\nAuditioning each one...")
        for voice in voices:
            print(f"Now speaking: {voice.name}")
            one = pyttsx3.init()
            one.setProperty("rate", settings.VOICE_RATE)
            one.setProperty("voice", voice.id)
            one.say(TEST_LINE)
            one.runAndWait()
            one.stop()
        print("\nPick a fallback and put part of its name in .env, e.g. STELLY_VOICE=Zira")
        print("For Stelly's real voice, set up Piper, see this file's docstring.")
