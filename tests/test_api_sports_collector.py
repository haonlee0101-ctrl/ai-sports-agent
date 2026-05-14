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

FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "api_sports_fixtures_sample.json"


def load_api_sports_tools():
    collector_module = importlib.import_module("src.collectors.api_sports")
    contracts_module = importlib.import_module("src.contracts.report_input")
    return (
        collector_module.load_report_input_from_api_sports_fixture,
        collector_module.parse_api_sports_fixture_response,
        collector_module.ApiSportsCollectorError,
        contracts_module.ReportInput,
    )


def test_parsing_valid_api_sports_like_fixture_sample_into_report_input() -> None:
    load_fixture, _, _, ReportInput = load_api_sports_tools()

    report_input = load_fixture(FIXTURE_PATH)

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "east"
    assert report_input.mode == "mock"
    assert len(report_input.games) == 2
    assert report_input.games[0].game_id == "api-sports-501001"


def test_missing_odds_data_remains_explicit() -> None:
    load_fixture, _, _, _ = load_api_sports_tools()

    report_input = load_fixture(FIXTURE_PATH)
    first_game = report_input.games[0]

    assert first_game.market_probability.implied_probability is None
    assert "API-Sports fixture sample does not include odds data." in first_game.missing_data
    assert "API-Sports fixture sample does not include odds data." in (
        first_game.market_probability.missing_data
    )
    assert first_game.data_quality.odds_status == "missing"


def test_invalid_response_fails_clearly(tmp_path) -> None:
    load_fixture, _, ApiSportsCollectorError, _ = load_api_sports_tools()
    invalid_payload = {
        "region": "east",
        "generated_at": "2026-05-14 08:00 KST",
        "response": [
            {
                "fixture": {"id": 12345},
                "league": {"name": "KBO"},
                "teams": {"home": {"name": "Broken Home"}, "away": {"name": "Broken Away"}},
            }
        ],
    }
    invalid_path = tmp_path / "invalid_api_sports_fixture.json"
    invalid_path.write_text(
        json.dumps(invalid_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with pytest.raises(ApiSportsCollectorError, match="missing required field 'date'"):
        load_fixture(invalid_path)


def test_no_external_network_call_is_made(monkeypatch) -> None:
    load_fixture, _, _, _ = load_api_sports_tools()
    monkeypatch.delenv("API_SPORTS_KEY", raising=False)

    def fail_on_network(*args, **kwargs):
        raise AssertionError("External network access should not be used.")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)

    report_input = load_fixture(FIXTURE_PATH)

    assert report_input.report_id.startswith("api-sports-east-")


def test_no_secrets_are_required() -> None:
    load_fixture, _, _, _ = load_api_sports_tools()

    report_input = load_fixture(FIXTURE_PATH)

    assert report_input.source_notes == ["Parsed from a local API-Sports-like fixture sample only."]
