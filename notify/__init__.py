"""
Outbound notifications, behind one tiny interface.

Callers use notify(text) and never know or care which channel delivers
it. Today that is Twilio SMS, texts that land in the iPhone Messages
app. Adding another channel later means one new module and one entry in
CHANNELS, callers do not change. Nothing configured means the message is
silently skipped, notify() is always safe to call.
"""

from notify import email_sms, twilio_sms

# First configured channel wins. email_sms is free (Gmail to a carrier
# text gateway), so it leads. Twilio stays as an optional paid upgrade.
CHANNELS = (email_sms, twilio_sms)


def notify(text):
    """Send a notification through the first configured channel.
    Returns True if a channel accepted the message."""
    for channel in CHANNELS:
        if channel.is_configured():
            return channel.send_message(text)
    return False
