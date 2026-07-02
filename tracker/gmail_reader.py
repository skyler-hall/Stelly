"""
Reads messages out of Gmail over IMAP.

Uses an app password rather than OAuth, this is a single user local
project running on hardware Skyler owns, so the OAuth consent flow and
token refresh dance would be overhead without much benefit. An app
password needs 2FA turned on for the Gmail account, generate one at
myaccount.google.com/apppasswords and put it in .env as
GMAIL_APP_PASSWORD.

This module only fetches and parses messages. Deciding which messages
are job applications, matching them to a company, and storing them all
happens in later tracker modules.
"""

import email
import imaplib
from email.header import decode_header

from config import settings

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993


def connect():
    """Log in to Gmail over IMAP and return the open connection.
    Caller is responsible for calling logout() when done."""
    address = settings.require(settings.GMAIL_ADDRESS, "GMAIL_ADDRESS")
    password = settings.require(settings.GMAIL_APP_PASSWORD, "GMAIL_APP_PASSWORD")

    connection = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    connection.login(address, password)
    return connection


def fetch_recent_messages(limit=20, search_query="ALL", mailbox="INBOX"):
    """Fetch the most recent messages matching an IMAP search query.

    search_query uses IMAP search syntax, some examples:
      'ALL'                     everything in the mailbox
      'UNSEEN'                  only unread messages
      'SUBJECT "application"'   subject contains a word
      'FROM "greenhouse.io"'    sender domain match

    Returns a list of dicts, newest first, each shaped like:
      {
        "message_id": str,   # RFC822 Message-ID header, stable and unique
        "sender": str,
        "subject": str,
        "date": str,
        "snippet": str,      # first bit of the plain text body
      }
    """
    connection = connect()
    try:
        connection.select(mailbox, readonly=True)

        status, data = connection.search(None, search_query)
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")

        all_ids = data[0].split()
        recent_ids = all_ids[-limit:] if limit else all_ids
        recent_ids.reverse()  # newest first

        messages = []
        for msg_id in recent_ids:
            status, msg_data = connection.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            fetch_part = msg_data[0]
            if not isinstance(fetch_part, tuple):
                continue

            raw_email = fetch_part[1]
            parsed = email.message_from_bytes(raw_email)

            messages.append({
                "message_id": parsed.get("Message-ID", "").strip(),
                "sender": _decode_header(parsed.get("From")),
                "subject": _decode_header(parsed.get("Subject")),
                "date": parsed.get("Date", ""),
                "snippet": _get_snippet(parsed),
            })

        return messages
    finally:
        connection.logout()


def _decode_header(value):
    """IMAP headers can come back as encoded word strings like
    =?UTF-8?B?...?=, this turns them into plain readable text."""
    if value is None:
        return ""
    decoded = ""
    for text, encoding in decode_header(value):
        if isinstance(text, bytes):
            decoded += text.decode(encoding or "utf-8", errors="replace")
        else:
            decoded += text
    return decoded


def _get_snippet(parsed_email, length=200):
    """Pull the first bit of plain text body. HTML only emails return
    an empty snippet for now, that can be filled in later if it matters."""
    if parsed_email.is_multipart():
        for part in parsed_email.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True)
                if body:
                    return body.decode(errors="replace").strip()[:length]
        return ""
    else:
        body = parsed_email.get_payload(decode=True)
        if body:
            return body.decode(errors="replace").strip()[:length]
        return ""


if __name__ == "__main__":
    # Quick manual check: run this file directly to print your 5 most
    # recent inbox messages and confirm the connection works.
    for msg in fetch_recent_messages(limit=5):
        print(msg["date"], "|", msg["sender"], "|", msg["subject"])
