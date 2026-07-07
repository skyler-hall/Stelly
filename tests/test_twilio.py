"""Tests for notify/twilio_sms.py and channel preference in notify(),
all network mocked."""

from unittest.mock import MagicMock, patch

import notify
from notify import twilio_sms


def _configured(monkeypatch):
    monkeypatch.setattr("config.settings.TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setattr("config.settings.TWILIO_AUTH_TOKEN", "tok")
    monkeypatch.setattr("config.settings.TWILIO_FROM_NUMBER", "+15550001111")
    monkeypatch.setattr("config.settings.TWILIO_TO_NUMBER", "+15552223333")


def _unconfigured(monkeypatch):
    for name in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
                 "TWILIO_FROM_NUMBER", "TWILIO_TO_NUMBER"):
        monkeypatch.setattr(f"config.settings.{name}", "")


def _ok_response():
    response = MagicMock()
    response.ok = True
    return response


def test_unconfigured_send_returns_false(monkeypatch):
    _unconfigured(monkeypatch)
    assert twilio_sms.send_message("hello") is False


def test_partially_configured_is_not_configured(monkeypatch):
    _configured(monkeypatch)
    monkeypatch.setattr("config.settings.TWILIO_TO_NUMBER", "")
    assert twilio_sms.is_configured() is False


def test_successful_send_posts_the_right_things(monkeypatch):
    _configured(monkeypatch)
    with patch("notify.twilio_sms.requests.post", return_value=_ok_response()) as post:
        assert twilio_sms.send_message("hello") is True
    args, kwargs = post.call_args
    assert "AC123" in args[0]
    assert kwargs["auth"] == ("AC123", "tok")
    assert kwargs["data"]["Body"] == "hello"
    assert kwargs["data"]["To"] == "+15552223333"


def test_api_rejection_returns_false(monkeypatch):
    _configured(monkeypatch)
    rejected = MagicMock()
    rejected.ok = False
    rejected.status_code = 401
    rejected.json.return_value = {"message": "auth error"}
    with patch("notify.twilio_sms.requests.post", return_value=rejected):
        assert twilio_sms.send_message("hello") is False


def test_network_error_returns_false_not_raise(monkeypatch):
    _configured(monkeypatch)
    with patch("notify.twilio_sms.requests.post", side_effect=OSError("offline")):
        assert twilio_sms.send_message("hello") is False


def test_empty_text_is_not_sent(monkeypatch):
    _configured(monkeypatch)
    with patch("notify.twilio_sms.requests.post") as post:
        assert twilio_sms.send_message("") is False
    post.assert_not_called()


def test_notify_delivers_through_twilio(monkeypatch):
    _configured(monkeypatch)
    # Silence the email channel so notify() reaches twilio and no test
    # ever attempts a real SMTP login against someone's actual .env.
    monkeypatch.setattr("config.settings.NOTIFY_EMAIL_TO", "")
    with patch("notify.twilio_sms.requests.post", return_value=_ok_response()) as post:
        assert notify.notify("hello") is True
    post.assert_called_once()
    assert "api.twilio.com" in post.call_args[0][0]


def test_notify_skips_quietly_when_unconfigured(monkeypatch):
    _unconfigured(monkeypatch)
    monkeypatch.setattr("config.settings.NOTIFY_EMAIL_TO", "")
    assert notify.notify("hello") is False
