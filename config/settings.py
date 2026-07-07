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

# LeetCode progress tracking via alfa-leetcode-api. The default URL is
# the public instance (free tier, sleeps when idle, rate limited).
# Point LEETCODE_API_URL at a self hosted docker copy for speed.
LEETCODE_USERNAME = os.getenv("LEETCODE_USERNAME", "")
LEETCODE_API_URL = os.getenv("LEETCODE_API_URL", "https://alfa-leetcode-api.onrender.com")

# Free texts through Gmail: an email to text gateway address like
# 5551234567@tmomail.net, or any plain email address. Uses the Gmail
# credentials above. See notify/email_sms.py for gateway addresses.
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO", "")

# Optional separate sending identity so texts arrive "from Stelly"
# instead of from Skyler's own Gmail. Empty means send with the
# GMAIL_ADDRESS credentials above.
NOTIFY_EMAIL_FROM = os.getenv("NOTIFY_EMAIL_FROM", "")
NOTIFY_EMAIL_PASSWORD = os.getenv("NOTIFY_EMAIL_PASSWORD", "")

# Twilio SMS, optional paid alternative. Setup steps are documented in
# notify/twilio_sms.py. All empty means the channel is skipped.
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
TWILIO_TO_NUMBER = os.getenv("TWILIO_TO_NUMBER", "")

# IMAP search used by the job tracker when scanning for application
# emails. Refine per machine in .env as classification needs grow.
TRACKER_QUERY = os.getenv("TRACKER_QUERY", 'SUBJECT "application"')


def require(value, name):
    """Raise a clear error if a required setting is missing, instead of
    letting a None sneak downstream and fail somewhere confusing later."""
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to your .env file.")
    return value
