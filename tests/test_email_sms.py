"""Tests for notify/email_sms.py, the free Gmail-to-text channel,
with SMTP fully mocked."""

from unittest.mock import MagicMock, patch

import notify
from notify import email_sms


def _configured(monkeypatch):
    monkeypatch.setattr("config.settings.NOTIFY_EMAIL_TO", "5551234567@tmomail.net")
    monkeypatch.setattr("config.settings.GMAIL_ADDRESS", "me@gmail.com")
    monkeypatch.setattr("config.settings.GMAIL_APP_PASSWORD", "apppass")
    monkeypatch.setattr("config.settings.NOTIFY_EMAIL_FROM", "")
    monkeypatch.setattr("config.settings.NOTIFY_EMAIL_PASSWORD", "")


def _unconfigured(monkeypatch):
    monkeypatch.setattr("config.settings.NOTIFY_EMAIL_TO", "")
    monkeypatch.setattr("config.settings.TWILIO_ACCOUNT_SID", "")


def _smtp_pair():
    """A mocked SMTP_SSL context manager and the server it yields."""
    server = MagicMock()
    smtp = MagicMock()
    smtp.__enter__ = MagicMock(return_value=server)
    smtp.__exit__ = MagicMock(return_value=False)
    return server, smtp


def test_unconfigured_send_returns_false(monkeypatch):
    _unconfigured(monkeypatch)
    assert email_sms.send_message("hello") is False


def test_missing_gmail_password_is_not_configured(monkeypatch):
    _configured(monkeypatch)
    monkeypatch.setattr("config.settings.GMAIL_APP_PASSWORD", "")
    assert email_sms.is_configured() is False


def test_successful_send_logs_in_and_sends(monkeypatch):
    _configured(monkeypatch)
    server, smtp = _smtp_pair()
    with patch("notify.email_sms.smtplib.SMTP_SSL", return_value=smtp):
        assert email_sms.send_message("hello") is True
    server.login.assert_called_once_with("me@gmail.com", "apppass")
    sent = server.send_message.call_args[0][0]
    assert sent["To"] == "5551234567@tmomail.net"
    assert "hello" in sent.get_content()


def test_smtp_failure_returns_false_not_raise(monkeypatch):
    _configured(monkeypatch)
    with patch("notify.email_sms.smtplib.SMTP_SSL", side_effect=OSError("smtp down")):
        assert email_sms.send_message("hello") is False


def test_empty_text_is_not_sent(monkeypatch):
    _configured(monkeypatch)
    with patch("notify.email_sms.smtplib.SMTP_SSL") as smtp:
        assert email_sms.send_message("") is False
    smtp.assert_not_called()


def test_stelly_own_account_handles_login_when_it_has_a_password(monkeypatch):
    _configured(monkeypatch)
    monkeypatch.setattr("config.settings.NOTIFY_EMAIL_FROM", "stelly@gmail.com")
    monkeypatch.setattr("config.settings.NOTIFY_EMAIL_PASSWORD", "stellypass")
    server, smtp = _smtp_pair()
    with patch("notify.email_sms.smtplib.SMTP_SSL", return_value=smtp):
        assert email_sms.send_message("hello") is True
    server.login.assert_called_once_with("stelly@gmail.com", "stellypass")
    assert server.send_message.call_args[0][0]["From"] == "stelly@gmail.com"


def test_alias_mode_logs_in_as_skyler_but_sends_as_stelly(monkeypatch):
    _configured(monkeypatch)
    monkeypatch.setattr("config.settings.NOTIFY_EMAIL_FROM", "stelly@gmail.com")
    # No NOTIFY_EMAIL_PASSWORD: login must stay with Skyler's account.
    server, smtp = _smtp_pair()
    with patch("notify.email_sms.smtplib.SMTP_SSL", return_value=smtp):
        assert email_sms.send_message("hello") is True
    server.login.assert_called_once_with("me@gmail.com", "apppass")
    assert server.send_message.call_args[0][0]["From"] == "stelly@gmail.com"


def test_notify_uses_email_channel_first(monkeypatch):
    _configured(monkeypatch)
    server, smtp = _smtp_pair()
    with patch("notify.email_sms.smtplib.SMTP_SSL", return_value=smtp):
        assert notify.notify("hello") is True
    server.send_message.assert_called_once()
