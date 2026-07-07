"""
Sends real text messages to Skyler's iPhone through Twilio SMS.

They arrive in the regular Messages app (green bubble, since iMessage
itself has no public API). Plain REST with basic auth, no Twilio SDK
needed for one endpoint.

Setup, one time:

  1. Sign up at twilio.com (free trial works).
  2. In the Twilio console, get a phone number (trial includes one).
  3. On a trial account, verify your personal number under Phone Numbers
     -> Verified Caller IDs (trial can only text verified numbers, and
     prefixes messages with a trial notice).
  4. Copy the Account SID and Auth Token from the console dashboard
     into .env:
       TWILIO_ACCOUNT_SID=ACxxxxxxxx
       TWILIO_AUTH_TOKEN=xxxxxxxx
       TWILIO_FROM_NUMBER=+15551234567   (your Twilio number)
       TWILIO_TO_NUMBER=+15557654321     (your iPhone)

Costs roughly a penny per message after the trial credit runs out.
send_message never raises: a failed text should never crash Stelly.
"""

import requests

from config import settings

TIMEOUT_SECONDS = 15


def is_configured():
    return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN
                and settings.TWILIO_FROM_NUMBER and settings.TWILIO_TO_NUMBER)


def send_message(text):
    """Text Skyler's phone. Returns True on success."""
    if not is_configured():
        print("(twilio not configured, sms skipped)")
        return False
    if not text:
        return False

    url = (f"https://api.twilio.com/2010-04-01/Accounts/"
           f"{settings.TWILIO_ACCOUNT_SID}/Messages.json")
    try:
        response = requests.post(
            url,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            data={
                "From": settings.TWILIO_FROM_NUMBER,
                "To": settings.TWILIO_TO_NUMBER,
                "Body": text,
            },
            timeout=TIMEOUT_SECONDS,
        )
        if response.ok:
            return True
        detail = response.json().get("message", response.status_code)
        print(f"(twilio rejected the message: {detail})")
        return False
    except Exception as error:
        print(f"(twilio send failed: {error})")
        return False


if __name__ == "__main__":
    # Quick manual check once .env has the four TWILIO_ values.
    sent = send_message("Stelly can text your phone now!")
    print("sent!" if sent else "not sent, check the setup steps in this file")
