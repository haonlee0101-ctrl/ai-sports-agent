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
    ApiSportsClient,
    LiveApiConfigurationError,
    OddsApiClient,
)
from src.collectors.report_input_loader import (  # noqa: E402
    ReportInputLoaderError,
    load_report_input_from_clients,
)
from src.contracts.report_input import ReportInput  # noqa: E402


def load_fixture(filename: str):
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_fake_clients_can_produce_east_report_input_data() -> None:
    api_sports_client = ApiSportsClient(
        fake_response=load_fixture("api_sports_fixtures_sample.json"),
    )
    odds_api_client = OddsApiClient(
        fake_response=load_fixture("odds_api_events_sample.json"),
    )

    report_input = load_report_input_from_clients(
        region="east",
        api_sports_client=api_sports_client,
        odds_api_client=odds_api_client,
    )

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "east"
    assert report_input.mode == "mock"
    assert len(report_input.games) == 2
    assert all(game.market_probability.implied_probability is None for game in report_input.games)
    assert any("odds data" in item.lower() for item in report_input.games[0].missing_data)


def test_fake_clients_can_produce_west_report_input_data() -> None:
    api_sports_client = ApiSportsClient(
        fake_response=load_fixture("api_sports_fixtures_west_sample.json"),
    )
    odds_api_client = OddsApiClient(
        fake_response=load_fixture("odds_api_events_west_sample.json"),
    )

    report_input = load_report_input_from_clients(
        region="west",
        api_sports_client=api_sports_client,
        odds_api_client=odds_api_client,
    )

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "west"
    assert len(report_input.games) == 2
    assert report_input.games[0].market_probability.implied_probability == pytest.approx(0.5714)
    assert report_input.games[0].data_quality.odds_status == "available"
    assert report_input.games[1].market_probability.implied_probability is None
    assert report_input.games[1].data_quality.odds_status == "missing"
    assert (
        "Matched local The Odds API-like sample where team names aligned."
        in report_input.source_notes
    )


def test_no_network_call_is_made_when_fake_response_clients_are_used() -> None:
    api_sports_transport_called = False
    odds_transport_called = False

    def raising_api_sports_transport(url, headers):
        nonlocal api_sports_transport_called
        api_sports_transport_called = True
        raise AssertionError("API-Sports transport should not be called in fake mode.")

    def raising_odds_transport(url, headers):
        nonlocal odds_transport_called
        odds_transport_called = True
        raise AssertionError("The Odds API transport should not be called in fake mode.")

    api_sports_client = ApiSportsClient(
        fake_response=load_fixture("api_sports_fixtures_sample.json"),
        transport=raising_api_sports_transport,
    )
    odds_api_client = OddsApiClient(
        fake_response=load_fixture("odds_api_events_sample.json"),
        transport=raising_odds_transport,
    )

    report_input = load_report_input_from_clients(
        region="east",
        api_sports_client=api_sports_client,
        odds_api_client=odds_api_client,
    )

    assert report_input.region == "east"
    assert api_sports_transport_called is False
    assert odds_transport_called is False


def test_requested_region_mismatch_fails_clearly() -> None:
    api_sports_client = ApiSportsClient(
        fake_response=load_fixture("api_sports_fixtures_sample.json"),
    )

    with pytest.raises(
        ReportInputLoaderError,
        match=re.escape(
            "Requested region does not match client-loaded ReportInput: expected west, got east."
        ),
    ):
        load_report_input_from_clients(
            region="west",
            api_sports_client=api_sports_client,
        )


def test_missing_odds_remain_explicit_not_fabricated() -> None:
    api_sports_client = ApiSportsClient(
        fake_response=load_fixture("api_sports_fixtures_sample.json"),
    )

    report_input = load_report_input_from_clients(
        region="east",
        api_sports_client=api_sports_client,
    )

    assert report_input.games[0].market_probability.implied_probability is None
    assert report_input.games[1].market_probability.implied_probability is None
    assert all(game.data_quality.odds_status == "missing" for game in report_input.games)
    assert all(game.market_probability.missing_data for game in report_input.games)


def test_missing_api_keys_are_not_needed_for_fake_mode() -> None:
    api_sports_client = ApiSportsClient(
        fake_response=load_fixture("api_sports_fixtures_west_sample.json"),
    )
    odds_api_client = OddsApiClient(
        fake_response=load_fixture("odds_api_events_west_sample.json"),
    )

    report_input = load_report_input_from_clients(
        region="west",
        api_sports_client=api_sports_client,
        odds_api_client=odds_api_client,
    )

    assert report_input.region == "west"


def test_live_mode_is_not_triggered_by_default() -> None:
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called when fake data is available.")

    api_sports_client = ApiSportsClient(
        api_key="unused-in-fake-mode",
        base_url="https://example.invalid",
        fake_response=load_fixture("api_sports_fixtures_sample.json"),
        transport=raising_transport,
    )

    report_input = load_report_input_from_clients(
        region="east",
        api_sports_client=api_sports_client,
    )

    assert report_input.region == "east"
    assert transport_called is False


def test_live_mode_missing_api_key_fails_before_any_network_call() -> None:
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called before API key validation.")

    api_sports_client = ApiSportsClient(
        base_url="https://example.invalid",
        transport=raising_transport,
    )

    with pytest.raises(
        LiveApiConfigurationError,
        match=re.escape("API-Sports live mode requires an explicit API key."),
    ):
        load_report_input_from_clients(
            region="east",
            api_sports_client=api_sports_client,
            use_live=True,
        )

    assert transport_called is False


def test_loader_uses_existing_parser_and_builder_output_contracts() -> None:
    api_sports_client = ApiSportsClient(
        fake_response=load_fixture("api_sports_fixtures_west_sample.json"),
    )
    odds_api_client = OddsApiClient(
        fake_response=load_fixture("odds_api_events_west_sample.json"),
    )

    report_input = load_report_input_from_clients(
        region="west",
        api_sports_client=api_sports_client,
        odds_api_client=odds_api_client,
    )

    assert isinstance(report_input, ReportInput)
    assert report_input.model_dump()["games"][0]["game_id"] == "api-sports-701001"
    assert report_input.games[0].market_probability.source_name == "SampleBook"
    assert report_input.games[0].market_probability.market_name == "h2h"


def test_loader_does_not_contain_hardcoded_secret_looking_values() -> None:
    loader_source = (PROJECT_ROOT / "src" / "collectors" / "report_input_loader.py").read_text(
        encoding="utf-8"
    )
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, loader_source) is None
