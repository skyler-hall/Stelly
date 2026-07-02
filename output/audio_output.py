"""
Stelly's voice.

speak(text) says the words out loud and blocks until done, which is
exactly what the main loop wants, it flips the face into talking mode,
calls speak, and flips it back when speak returns.

The engine behind speak is swappable. Today that is pyttsx3, which uses
whatever the operating system already has: SAPI voices on Windows,
NSSpeechSynthesizer on Mac, espeak on Linux. Nothing to download, works
everywhere for development. On the Pi the plan is Piper for a much nicer
custom voice, and that lands here as one more engine class, nothing
outside this file changes.

pyttsx3 quirk worth knowing: reusing one engine across many runAndWait
calls is unreliable on some platforms (the second call sometimes never
speaks). Building a fresh engine per utterance costs a few milliseconds
and sidesteps the whole bug class.
"""

import pyttsx3

SPEECH_RATE = 175        # words per minute, slightly quicker than default
VOICE_PREFERENCE = ""    # substring of a voice name to prefer, e.g. "Zira", empty picks default


class Pyttsx3Engine:
    """Cross-platform system voices via pyttsx3."""

    def say(self, text):
        engine = pyttsx3.init()  # fresh engine per call, see module docstring
        engine.setProperty("rate", SPEECH_RATE)
        if VOICE_PREFERENCE:
            for voice in engine.getProperty("voices"):
                if VOICE_PREFERENCE.lower() in voice.name.lower():
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


# Future: class PiperEngine with the same say(text) shape, chosen first
# when a Piper voice model is configured. That is the Pi upgrade path.

_engine = None


def _get_engine():
    """Pick the best engine available, once per process."""
    global _engine
    if _engine is None:
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
    # Quick manual check: run this file directly to hear the voice.
    speak("Hello! Stelly can talk now. Stelly is very excited about this!")
