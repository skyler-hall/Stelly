"""
Loads secrets from .env and exposes them as constants.

This is the only file in the whole project allowed to touch .env or
os.environ directly. Everything else imports from here.
"""

import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Which microphone Stelly listens through, as a piece of the device name,
# for example "eMeet" or "USB PnP". Empty means use the system default.
# Lives in .env because the right answer differs on every machine.
MIC_NAME = os.getenv("STELLY_MIC", "")

# Which system voice Stelly speaks with, as a piece of the voice name,
# for example "Zira" on Windows. Empty means the system default voice.
# STELLY_VOICE_RATE is words per minute, higher sounds more energetic.
VOICE_NAME = os.getenv("STELLY_VOICE", "")
VOICE_RATE = int(os.getenv("STELLY_VOICE_RATE", "185"))

# Privacy: when STELLY_PUSH_TO_TALK is on (1/true/yes), the microphone
# stays completely closed until Space is pressed in Stelly's window,
# and closes again as soon as one utterance is captured. When off,
# Stelly listens continuously while running, Siri style.
PUSH_TO_TALK = os.getenv("STELLY_PUSH_TO_TALK", "").strip().lower() in ("1", "true", "yes")


def require(value, name):
    """Raise a clear error if a required setting is missing, instead of
    letting a None sneak downstream and fail somewhere confusing later."""
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to your .env file.")
    return value
