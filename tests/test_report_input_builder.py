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

API_SPORTS_FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "api_sports_fixtures_sample.json"
ODDS_FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "odds_api_events_sample.json"


def load_builder_tools():
    builder_module = importlib.import_module("src.collectors.report_input_builder")
    contracts_module = importlib.import_module("src.contracts.report_input")
    return (
        builder_module.build_report_input_from_fixture_sources,
        builder_module.ReportInputBuilderError,
        contracts_module.ReportInput,
    )


def write_matching_odds_fixture(tmp_path: Path) -> Path:
    odds_payload = json.loads(ODDS_FIXTURE_PATH.read_text(encoding="utf-8"))
    odds_payload["events"][0]["home_team"] = "Seoul Fixture Club"
    odds_payload["events"][0]["away_team"] = "Busan Fixture Club"
    odds_payload["events"][0]["bookmakers"][0]["markets"][0]["outcomes"][0]["name"] = (
        "Seoul Fixture Club"
    )
    odds_payload["events"][0]["bookmakers"][0]["markets"][0]["outcomes"][1]["name"] = (
        "Busan Fixture Club"
    )

    output_path = tmp_path / "matching_odds_api_events_sample.json"
    output_path.write_text(
        json.dumps(odds_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def test_building_valid_report_input_from_api_sports_and_odds_fixtures(tmp_path) -> None:
    build_report_input_from_fixture_sources, _, ReportInput = load_builder_tools()
    matching_odds_path = write_matching_odds_fixture(tmp_path)

    report_input = build_report_input_from_fixture_sources(
        API_SPORTS_FIXTURE_PATH,
        matching_odds_path,
    )

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "east"
    assert len(report_input.games) == 2


def test_matching_games_receive_market_probability_data(tmp_path) -> None:
    build_report_input_from_fixture_sources, _, _ = load_builder_tools()
    matching_odds_path = write_matching_odds_fixture(tmp_path)

    report_input = build_report_input_from_fixture_sources(
        API_SPORTS_FIXTURE_PATH,
        matching_odds_path,
    )
    matched_game = report_input.games[0]

    assert matched_game.home_team == "Seoul Fixture Club"
    assert matched_game.market_probability.source_name == "SampleBook"
    assert matched_game.market_probability.selection == "Seoul Fixture Club"
    assert matched_game.market_probability.implied_probability == 0.5556
    assert matched_game.data_quality.odds_status == "available"


def test_games_without_odds_keep_missing_data_explicit(tmp_path) -> None:
    build_report_input_from_fixture_sources, _, _ = load_builder_tools()
    matching_odds_path = write_matching_odds_fixture(tmp_path)

    report_input = build_report_input_from_fixture_sources(
        API_SPORTS_FIXTURE_PATH,
        matching_odds_path,
    )
    unmatched_game = report_input.games[1]

    assert unmatched_game.home_team == "Tokyo Fixture Nine"
    assert unmatched_game.market_probability.implied_probability is None
    assert "API-Sports fixture sample does not include odds data." in unmatched_game.missing_data
    assert "API-Sports fixture sample does not include odds data." in (
        unmatched_game.market_probability.missing_data
    )


def test_unmatched_odds_do_not_create_fake_games(tmp_path) -> None:
    build_report_input_from_fixture_sources, _, _ = load_builder_tools()
    matching_odds_path = write_matching_odds_fixture(tmp_path)

    report_input = build_report_input_from_fixture_sources(
        API_SPORTS_FIXTURE_PATH,
        matching_odds_path,
    )

    assert len(report_input.games) == 2
    assert {game.game_id for game in report_input.games} == {
        "api-sports-501001",
        "api-sports-501002",
    }


def test_invalid_fixture_data_fails_clearly(tmp_path) -> None:
    build_report_input_from_fixture_sources, ReportInputBuilderError, _ = load_builder_tools()
    invalid_fixture_payload = {
        "region": "east",
        "generated_at": "2026-05-14 08:00 KST",
        "response": [
            {
                "fixture": {"id": 501999},
                "league": {"name": "KBO"},
                "teams": {
                    "home": {"name": "Broken Fixture Club"},
                    "away": {"name": "Broken Away Club"},
                },
            }
        ],
    }
    invalid_fixture_path = tmp_path / "invalid_api_sports_fixture.json"
    invalid_fixture_path.write_text(
        json.dumps(invalid_fixture_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(ReportInputBuilderError, match="missing required field 'date'"):
        build_report_input_from_fixture_sources(invalid_fixture_path, ODDS_FIXTURE_PATH)


def test_no_external_network_call_is_made(tmp_path, monkeypatch) -> None:
    build_report_input_from_fixture_sources, _, _ = load_builder_tools()
    matching_odds_path = write_matching_odds_fixture(tmp_path)
    monkeypatch.delenv("API_SPORTS_KEY", raising=False)
    monkeypatch.delenv("ODDS_API_KEY", raising=False)

    def fail_on_network(*args, **kwargs):
        raise AssertionError("External network access should not be used.")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)

    report_input = build_report_input_from_fixture_sources(
        API_SPORTS_FIXTURE_PATH,
        matching_odds_path,
    )

    assert report_input.report_id.startswith("api-sports-east-")


def test_no_secrets_are_required(tmp_path) -> None:
    build_report_input_from_fixture_sources, _, _ = load_builder_tools()
    matching_odds_path = write_matching_odds_fixture(tmp_path)

    report_input = build_report_input_from_fixture_sources(
        API_SPORTS_FIXTURE_PATH,
        matching_odds_path,
    )

    assert "Matched local The Odds API-like sample where team names aligned." in (
        report_input.source_notes
    )
