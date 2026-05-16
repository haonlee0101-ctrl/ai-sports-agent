from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.api_clients import (  # noqa: E402
    ApiResponseFormatError,
    ApiSportsClient,
    LiveApiConfigurationError,
    OddsApiClient,
)


def load_fixture(filename: str):
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_api_sports_client_can_return_injected_fake_fixture_response() -> None:
    fake_response = load_fixture("api_sports_fixtures_sample.json")
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Network transport should not be called in fake-response mode.")

    client = ApiSportsClient(
        fake_response=fake_response,
        transport=raising_transport,
    )

    response = client.fetch_fixtures()

    assert transport_called is False
    assert response == fake_response
    assert response["region"] == "east"
    assert response["response"][0]["teams"]["home"]["name"] == "Seoul Fixture Club"


def test_odds_api_client_can_return_injected_fake_odds_response() -> None:
    fake_response = load_fixture("odds_api_events_sample.json")
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Network transport should not be called in fake-response mode.")

    client = OddsApiClient(
        fake_response=fake_response,
        transport=raising_transport,
    )

    response = client.fetch_events()

    assert transport_called is False
    assert response == fake_response
    assert response["events"][0]["home_team"] == "Seoul Odds Club"
    assert response["events"][1]["bookmakers"] == []


@pytest.mark.parametrize(
    ("client_factory", "provider_name"),
    [
        (
            lambda transport: ApiSportsClient(
                base_url="https://example.invalid",
                transport=transport,
            ),
            "API-Sports",
        ),
        (
            lambda transport: OddsApiClient(
                base_url="https://example.invalid",
                transport=transport,
            ),
            "The Odds API",
        ),
    ],
)
def test_missing_api_key_fails_clearly_only_when_live_mode_is_requested(
    client_factory,
    provider_name: str,
) -> None:
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called before API key validation.")

    client = client_factory(raising_transport)

    with pytest.raises(
        LiveApiConfigurationError,
        match=re.escape(f"{provider_name} live mode requires an explicit API key."),
    ):
        if provider_name == "API-Sports":
            client.fetch_fixtures(use_live=True)
        else:
            client.fetch_events(use_live=True)

    assert transport_called is False


def test_fake_response_mode_does_not_require_api_keys() -> None:
    api_sports_response = load_fixture("api_sports_fixtures_sample.json")
    odds_response = load_fixture("odds_api_events_sample.json")

    api_sports_client = ApiSportsClient(fake_response=api_sports_response)
    odds_client = OddsApiClient(fake_response=odds_response)

    assert api_sports_client.fetch_fixtures()["response"][1]["league"]["name"] == "NPB"
    assert odds_client.fetch_events()["events"][1]["home_team"] == "Tokyo Odds Nine"


def test_invalid_fake_responses_fail_clearly() -> None:
    api_sports_client = ApiSportsClient(fake_response={"region": "east"})
    odds_client = OddsApiClient(fake_response={"events": ["not-a-json-object"]})

    with pytest.raises(
        ApiResponseFormatError,
        match=re.escape("API-Sports fake response must include a 'response' list."),
    ):
        api_sports_client.fetch_fixtures()

    with pytest.raises(
        ApiResponseFormatError,
        match=re.escape("The Odds API fake response must use JSON objects inside 'events'."),
    ):
        odds_client.fetch_events()


def test_api_clients_do_not_contain_hardcoded_secret_looking_values() -> None:
    client_source = (PROJECT_ROOT / "src" / "collectors" / "api_clients.py").read_text(
        encoding="utf-8"
    )
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, client_source) is None
