"""
Free notifications through Gmail: email to text message gateways.

Every US carrier runs (or ran) an address that turns email into SMS.
Send to <number>@<gateway> from any mailbox and it lands as a normal
text. Combined with the Gmail app password already in .env, this makes
Stelly's texts completely free, no Twilio, no fees, no registration.

Gateway addresses (use the 10 digit number, no +1):
  T-Mobile:  5551234567@tmomail.net
  Verizon:   5551234567@vtext.com
  AT&T:      shut their gateway down in 2025, use another option
  Metro:     5551234567@mymetropcs.com
  Cricket:   5551234567@mms.cricketwireless.net

Carriers are gradually retiring these, so if texts stop arriving one
day, point NOTIFY_EMAIL_TO at your regular email address instead, the
same channel then delivers as plain email, still free.

.env:
  NOTIFY_EMAIL_TO=5551234567@tmomail.net   (or any email address)

By default this sends from GMAIL_ADDRESS (Skyler's own account). To make
texts arrive from Stelly's own identity instead, two options:

Option A, alias (works immediately): in Skyler's Gmail, Settings, See
all settings, Accounts and Import, "Send mail as", add Stelly's address
and confirm the verification email. Then set only:

  NOTIFY_EMAIL_FROM=stelly.assistant@gmail.com

Sending still logs in as GMAIL_ADDRESS, but Gmail stamps the alias as
the From. (Without the alias setup Gmail silently rewrites From back to
the real account, so do the settings step first.)

Option B, separate account: once Stelly's own account is old enough for
Google to allow app passwords, set both values and the login itself
moves over:

  NOTIFY_EMAIL_FROM=stelly.assistant@gmail.com
  NOTIFY_EMAIL_PASSWORD=thataccountsapppassword

The job tracker keeps reading Skyler's inbox with GMAIL_ADDRESS either
way, the credentials are independent.

send_message never raises: a lost notification must never crash Stelly.
"""

import smtplib
from email.message import EmailMessage

from config import settings

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
TIMEOUT_SECONDS = 15


def _credentials():
    """Returns (login_address, password, from_address).

    Stelly's own account handles login only when it has its own password
    (option B). Otherwise login stays with Skyler's account, and
    NOTIFY_EMAIL_FROM, if set, rides along as an alias From (option A)."""
    if settings.NOTIFY_EMAIL_FROM and settings.NOTIFY_EMAIL_PASSWORD:
        login = settings.NOTIFY_EMAIL_FROM
        password = settings.NOTIFY_EMAIL_PASSWORD
    else:
        login = settings.GMAIL_ADDRESS
        password = settings.GMAIL_APP_PASSWORD
    from_address = settings.NOTIFY_EMAIL_FROM or login
    return login, password, from_address


def is_configured():
    login, password, _ = _credentials()
    return bool(settings.NOTIFY_EMAIL_TO and login and password)


def send_message(text):
    """Send text to NOTIFY_EMAIL_TO through Gmail. Returns True on success."""
    if not is_configured():
        print("(email notifications not configured, skipped)")
        return False
    if not text:
        return False

    login, password, from_address = _credentials()
    message = EmailMessage()
    message["From"] = from_address
    message["To"] = settings.NOTIFY_EMAIL_TO
    message["Subject"] = ""  # gateways show the subject inline, empty is cleaner
    message.set_content(text)

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT,
                              timeout=TIMEOUT_SECONDS) as server:
            server.login(login, password)
            server.send_message(message)
        return True
    except Exception as error:
        print(f"(email notification failed: {error})")
        return False


if __name__ == "__main__":
    # Quick manual check once .env has NOTIFY_EMAIL_TO and the Gmail values.
    sent = send_message("Stelly can text you for free now!")
    print("sent!" if sent else "not sent, check the setup notes in this file")
