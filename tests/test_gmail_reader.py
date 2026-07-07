"""Tests for the pure parsing helpers in tracker/gmail_reader.py.
Network and IMAP login are deliberately not tested here, those get
verified manually against the real inbox."""

from email.message import EmailMessage

from tracker.gmail_reader import _decode_header, _get_snippet


def test_plain_header_passes_through():
    assert _decode_header("Acme Careers <jobs@acme.com>") == "Acme Careers <jobs@acme.com>"


def test_none_header_becomes_empty_string():
    assert _decode_header(None) == ""


def test_encoded_utf8_header_is_decoded():
    # "=?utf-8?b?...?=" is base64 of 'Séb at Acme'
    assert _decode_header("=?utf-8?b?U8OpYiBhdCBBY21l?=") == "Séb at Acme"


def _plain_email(body):
    msg = EmailMessage()
    msg["From"] = "a@b.com"
    msg["Subject"] = "hi"
    msg.set_content(body)
    return msg


def test_snippet_from_plain_email():
    msg = _plain_email("Thanks for applying to Acme!")
    assert _get_snippet(msg).startswith("Thanks for applying")


def test_snippet_is_length_capped():
    msg = _plain_email("x" * 500)
    assert len(_get_snippet(msg, length=200)) <= 200


def test_snippet_from_multipart_prefers_plain_text():
    msg = EmailMessage()
    msg["From"] = "a@b.com"
    msg.set_content("plain body here")
    msg.add_alternative("<p>html body here</p>", subtype="html")
    assert "plain body here" in _get_snippet(msg)
