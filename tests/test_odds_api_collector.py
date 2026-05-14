from __future__ import annotations

import importlib
import json
import socket
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "odds_api_events_sample.json"


def load_odds_api_tools():
    collector_module = importlib.import_module("src.collectors.odds_api")
    contracts_module = importlib.import_module("src.contracts.report_input")
    return (
        collector_module.load_odds_api_events_fixture,
        collector_module.parse_odds_api_events_response,
        collector_module.decimal_odds_to_implied_probability,
        collector_module.OddsApiCollectorError,
        contracts_module.MarketProbability,
    )


def test_parsing_valid_odds_api_like_event_sample() -> None:
    load_fixture, _, _, _, _ = load_odds_api_tools()

    normalized_events = load_fixture(FIXTURE_PATH)

    assert len(normalized_events) == 2
    assert normalized_events[0].event_id == "odds-event-001"
    assert normalized_events[0].sport_title == "KBO"


def test_extracting_home_away_team_names_and_market_odds() -> None:
    load_fixture, _, _, _, _ = load_odds_api_tools()

    normalized_events = load_fixture(FIXTURE_PATH)
    first_event = normalized_events[0]
    first_market = first_event.markets[0]

    assert first_event.home_team == "Seoul Odds Club"
    assert first_event.away_team == "Busan Odds Club"
    assert first_market.bookmaker_name == "SampleBook"
    assert first_market.market_name == "h2h"
    assert first_market.outcomes[0].decimal_odds == 1.8
    assert first_market.outcomes[1].decimal_odds == 2.1


def test_converting_decimal_odds_into_implied_probabilities() -> None:
    load_fixture, _, decimal_odds_to_implied_probability, _, MarketProbability = (
        load_odds_api_tools()
    )

    normalized_events = load_fixture(FIXTURE_PATH)
    market_probabilities = normalized_events[0].as_market_probabilities()

    assert decimal_odds_to_implied_probability(1.8) == 0.5556
    assert market_probabilities[0].implied_probability == 0.5556
    assert market_probabilities[1].implied_probability == 0.4762
    assert isinstance(market_probabilities[0], MarketProbability)


def test_missing_odds_data_remains_explicit() -> None:
    load_fixture, _, _, _, _ = load_odds_api_tools()

    normalized_events = load_fixture(FIXTURE_PATH)
    second_event = normalized_events[1]

    assert second_event.markets == []
    assert (
        "The Odds API-like sample does not include bookmaker odds data."
        in second_event.missing_data
    )


def test_invalid_response_fails_clearly(tmp_path) -> None:
    load_fixture, _, _, OddsApiCollectorError, _ = load_odds_api_tools()
    invalid_payload = {
        "events": [
            {
                "id": "broken-event",
                "sport_key": "baseball_kbo",
                "sport_title": "KBO",
                "away_team": "Broken Away Club",
                "bookmakers": [],
            }
        ]
    }
    invalid_path = tmp_path / "invalid_odds_api_fixture.json"
    invalid_path.write_text(
        json.dumps(invalid_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(OddsApiCollectorError, match="missing required field 'home_team'"):
        load_fixture(invalid_path)


def test_no_external_network_call_is_made(monkeypatch) -> None:
    load_fixture, _, _, _, _ = load_odds_api_tools()
    monkeypatch.delenv("ODDS_API_KEY", raising=False)

    def fail_on_network(*args, **kwargs):
        raise AssertionError("External network access should not be used.")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)

    normalized_events = load_fixture(FIXTURE_PATH)

    assert normalized_events[0].event_id == "odds-event-001"


def test_no_secrets_are_required() -> None:
    load_fixture, _, _, _, _ = load_odds_api_tools()

    normalized_events = load_fixture(FIXTURE_PATH)

    assert normalized_events[0].markets[0].bookmaker_name == "SampleBook"
