from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_mailer_tools():
    mailer_module = importlib.import_module("src.messaging.sendgrid_mailer")
    return (
        mailer_module.SendGridMailer,
        mailer_module.SendGridMailerError,
        mailer_module.load_sendgrid_settings,
    )


class FakeSendGridClient:
    def __init__(self):
        self.call_count = 0
        self.payloads: list[dict] = []
        self.api_keys: list[str] = []

    def send(self, *, payload: dict, api_key: str):
        self.call_count += 1
        self.payloads.append(payload)
        self.api_keys.append(api_key)
        return 202


def test_sendgrid_mailer_reads_required_env_vars() -> None:
    _, _, load_sendgrid_settings = load_mailer_tools()

    settings = load_sendgrid_settings(
        {
            "SENDGRID_API_KEY": "fake-key-for-tests",
            "REPORT_FROM_EMAIL": "sender@test.invalid",
            "REPORT_TO_EMAIL": "recipient@test.invalid",
        }
    )

    assert settings.api_key == "fake-key-for-tests"
    assert settings.from_email == "sender@test.invalid"
    assert settings.to_email == "recipient@test.invalid"


def test_sendgrid_mailer_fails_clearly_when_env_vars_are_missing() -> None:
    _, SendGridMailerError, load_sendgrid_settings = load_mailer_tools()

    try:
        load_sendgrid_settings({})
    except SendGridMailerError as error:
        assert "Missing SendGrid configuration" in str(error)
    else:
        raise AssertionError("Missing env vars should raise SendGridMailerError.")


def test_sendgrid_mailer_can_use_fake_client_without_real_api_calls() -> None:
    SendGridMailer, _, _ = load_mailer_tools()
    fake_client = FakeSendGridClient()
    mailer = SendGridMailer(
        client=fake_client,
        env={
            "SENDGRID_API_KEY": "fake-key-for-tests",
            "REPORT_FROM_EMAIL": "sender@test.invalid",
            "REPORT_TO_EMAIL": "recipient@test.invalid",
        },
    )

    result = mailer.send_report(
        subject="Mock Subject",
        html_content="<h1>Mock HTML</h1>",
        plain_text_content="Mock plain text",
    )

    assert result == 202
    assert fake_client.call_count == 1
    assert fake_client.api_keys == ["fake-key-for-tests"]
    assert fake_client.payloads[0]["from"]["email"] == "sender@test.invalid"
