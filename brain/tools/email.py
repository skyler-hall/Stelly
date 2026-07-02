"""
Email tool. Lets Stelly check Skyler's inbox for recent messages without
Skyler having to open a laptop. Wraps tracker/gmail_reader.py rather than
touching IMAP directly, so there is one place that knows how to talk to
Gmail.
"""

from tracker import gmail_reader


def check_email(limit: int = 5) -> str:
    """Fetch the most recent inbox messages and return a short spoken
    summary Stelly can read out loud."""
    try:
        messages = gmail_reader.fetch_recent_messages(limit=limit)
    except RuntimeError as error:
        return f"Stelly could not check email: {error}"

    if not messages:
        return "Stelly checked, nothing new in the inbox."

    lines = [f"{msg['sender']} about {msg['subject']}" for msg in messages]
    return f"Stelly found {len(messages)} recent emails: " + "; ".join(lines)


CHECK_EMAIL_TOOL = {
    "name": "check_email",
    "description": (
        "Check Skyler's Gmail inbox for the most recent messages and summarize "
        "who they are from and what they are about. Use this when Skyler asks "
        "about email, messages, or his inbox."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "How many recent messages to check, defaults to 5.",
            },
        },
        "required": [],
    },
}
