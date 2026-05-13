from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Mapping
from urllib import error, request


@dataclass(frozen=True)
class SendGridSettings:
    api_key: str
    from_email: str
    to_email: str


class SendGridMailerError(ValueError):
    """Raised when SendGrid configuration or sending fails."""


def load_sendgrid_settings(env: Mapping[str, str] | None = None) -> SendGridSettings:
    source = os.environ if env is None else env
    missing = [
        key
        for key in ("SENDGRID_API_KEY", "REPORT_FROM_EMAIL", "REPORT_TO_EMAIL")
        if not source.get(key, "").strip()
    ]
    if missing:
        raise SendGridMailerError("Missing SendGrid configuration: " + ", ".join(missing))

    return SendGridSettings(
        api_key=source["SENDGRID_API_KEY"].strip(),
        from_email=source["REPORT_FROM_EMAIL"].strip(),
        to_email=source["REPORT_TO_EMAIL"].strip(),
    )


class SendGridMailer:
    def __init__(self, client=None, env: Mapping[str, str] | None = None):
        self.client = client or _SendGridApiClient()
        self.env = os.environ if env is None else env

    def send_report(
        self,
        *,
        subject: str,
        html_content: str,
        plain_text_content: str,
    ):
        settings = load_sendgrid_settings(self.env)
        payload = _build_sendgrid_payload(
            settings=settings,
            subject=subject,
            html_content=html_content,
            plain_text_content=plain_text_content,
        )

        try:
            return self.client.send(payload=payload, api_key=settings.api_key)
        except Exception as error_message:
            raise SendGridMailerError(f"SendGrid send failed: {error_message}") from error_message


def _build_sendgrid_payload(
    *,
    settings: SendGridSettings,
    subject: str,
    html_content: str,
    plain_text_content: str,
) -> dict:
    return {
        "personalizations": [
            {
                "to": [{"email": settings.to_email}],
                "subject": subject,
            }
        ],
        "from": {"email": settings.from_email},
        "content": [
            {"type": "text/plain", "value": plain_text_content},
            {"type": "text/html", "value": html_content},
        ],
    }


class _SendGridApiClient:
    endpoint = "https://api.sendgrid.com/v3/mail/send"

    def send(self, *, payload: dict, api_key: str) -> int:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req) as response:
                return response.status
        except error.HTTPError as http_error:
            response_body = http_error.read().decode("utf-8", errors="replace")
            raise SendGridMailerError(
                f"SendGrid API returned HTTP {http_error.code}: {response_body}"
            ) from http_error
        except error.URLError as url_error:
            raise SendGridMailerError(
                f"Could not reach SendGrid API: {url_error.reason}"
            ) from url_error
