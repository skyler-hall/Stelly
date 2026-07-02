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


def require(value, name):
    """Raise a clear error if a required setting is missing, instead of
    letting a None sneak downstream and fail somewhere confusing later."""
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to your .env file.")
    return value
