"""
Stelly's ears.

Always-on listening, Siri style but without a wake word yet: the mic
stream runs continuously, and a simple energy gate decides when Skyler
started and stopped talking. When a complete utterance is captured it
gets transcribed locally with faster-whisper and returned as text.

How the energy gate works: at startup the listener spends a moment
measuring the room's ambient noise level, then sets the speech threshold
a comfortable margin above that. Audio arrives in short blocks. A few
consecutive loud blocks means speech started. A stretch of quiet blocks
means it ended. A small rolling pre-roll buffer is always kept so the
first syllable does not get clipped off the front of the recording.

A wake word ("Hey Stelly") can slot in later as a filter in front of
listen() without changing anything downstream.
"""

import collections
import time

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from config import settings

SAMPLE_RATE = 16000          # what Whisper expects, mono
BLOCK_SECONDS = 0.03         # 30ms per block, standard for voice detection
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_SECONDS)

CALIBRATION_SECONDS = 1.0    # how long to measure room noise at startup
THRESHOLD_MULTIPLIER = 3.0   # speech must be this many times louder than the room
THRESHOLD_FLOOR = 0.01       # never let the threshold drop below this in a silent room

START_BLOCKS = 4             # consecutive loud blocks before we call it speech
END_SILENCE_SECONDS = 1.2    # this much quiet ends the utterance
PRE_ROLL_SECONDS = 0.4       # audio kept from just before speech started
MAX_UTTERANCE_SECONDS = 20   # safety cap so a loud fan cannot record forever
MIN_UTTERANCE_SECONDS = 0.4  # anything shorter is a door slam, not a sentence

WHISPER_MODEL = "base.en"    # good speed and accuracy tradeoff on CPU


def _find_input_device():
    """Pick which microphone to use.

    If STELLY_MIC is set in .env, find the first input device whose name
    contains that text (case insensitive). Otherwise, or if nothing
    matches, None means let the system default decide.
    """
    wanted = settings.MIC_NAME.strip().lower()
    if not wanted:
        return None
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0 and wanted in device["name"].lower():
            print(f"Using microphone {index}: {device['name']}")
            return index
    print(f"No mic matching '{settings.MIC_NAME}' found, using system default.")
    return None


class VoiceInput:
    def __init__(self, model_name=WHISPER_MODEL):
        # int8 keeps the model small and fast on CPU, both PC and Pi.
        # First run downloads the model, later runs load from local cache.
        print("Loading speech model, first time takes a minute...")
        self._model = WhisperModel(model_name, device="cpu", compute_type="int8")
        self._threshold = None
        self._device = _find_input_device()
        print("Speech model ready.")

    # ---- microphone side ----

    def _read_block(self, stream):
        """One block of mic audio as float32 in [-1, 1]."""
        block, _overflowed = stream.read(BLOCK_SIZE)
        return block[:, 0]

    @staticmethod
    def _energy(block):
        """Root mean square loudness of one block."""
        return float(np.sqrt(np.mean(np.square(block))))

    def _calibrate(self, stream):
        """Measure ambient room noise and set the speech threshold above it."""
        blocks = int(CALIBRATION_SECONDS / BLOCK_SECONDS)
        levels = [self._energy(self._read_block(stream)) for _ in range(blocks)]
        ambient = float(np.median(levels))
        self._threshold = max(ambient * THRESHOLD_MULTIPLIER, THRESHOLD_FLOOR)
        print(f"Mic calibrated. Room noise {ambient:.4f}, speech threshold {self._threshold:.4f}")

    def _record_utterance(self, stream, should_abort=None, timeout_seconds=None):
        """Block until one full utterance is captured, return it as audio.

        should_abort is an optional callable checked between blocks. When
        it returns True (for example because Stelly started speaking and
        would hear himself), recording stops and None comes back.

        timeout_seconds, if set, caps how long to wait for speech to
        begin. Push to talk uses this so a Space press with no words
        after it closes the mic instead of holding it open forever.
        """
        pre_roll = collections.deque(maxlen=int(PRE_ROLL_SECONDS / BLOCK_SECONDS))
        loud_streak = 0
        deadline = None if timeout_seconds is None else time.time() + timeout_seconds

        # Phase 1: wait for speech to start.
        while True:
            if should_abort and should_abort():
                return None
            if deadline and time.time() > deadline:
                return None
            block = self._read_block(stream)
            pre_roll.append(block)
            if self._energy(block) >= self._threshold:
                loud_streak += 1
                if loud_streak >= START_BLOCKS:
                    break
            else:
                loud_streak = 0

        # Phase 2: record until enough trailing silence.
        recording = list(pre_roll)
        quiet_streak = 0
        end_blocks = int(END_SILENCE_SECONDS / BLOCK_SECONDS)
        max_blocks = int(MAX_UTTERANCE_SECONDS / BLOCK_SECONDS)

        while len(recording) < max_blocks:
            if should_abort and should_abort():
                return None
            block = self._read_block(stream)
            recording.append(block)
            if self._energy(block) < self._threshold:
                quiet_streak += 1
                if quiet_streak >= end_blocks:
                    break
            else:
                quiet_streak = 0

        audio = np.concatenate(recording)
        if len(audio) / SAMPLE_RATE < MIN_UTTERANCE_SECONDS + PRE_ROLL_SECONDS:
            return None  # too short to be words
        return audio

    # ---- transcription side ----

    def _transcribe(self, audio):
        """Run faster-whisper on captured audio, return the text."""
        segments, _info = self._model.transcribe(audio, language="en", vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text

    # ---- public API ----

    def listen(self, should_abort=None, timeout_seconds=None):
        """Wait for the next thing Skyler says and return it as text.

        Returns None when nothing usable was heard (silence, a noise too
        short to be speech, or Whisper hearing no words in it), so the
        caller can just loop. Opens a fresh stream each call, which keeps
        the mic fully released while Stelly is thinking, speaking, or, in
        push to talk mode, whenever Space has not been pressed.
        """
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            blocksize=BLOCK_SIZE, device=self._device) as stream:
            if self._threshold is None:
                self._calibrate(stream)
            audio = self._record_utterance(stream, should_abort, timeout_seconds)

        if audio is None:
            return None
        text = self._transcribe(audio)
        return text or None


if __name__ == "__main__":
    # Quick manual check: run this file directly, say things, see the
    # transcripts print. Ctrl+C to quit.
    ears = VoiceInput()
    print("Listening. Say something. Ctrl+C to quit.")
    try:
        while True:
            heard = ears.listen()
            if heard:
                print(f"Heard: {heard}")
    except KeyboardInterrupt:
        print("\nDone listening. Bye!")
