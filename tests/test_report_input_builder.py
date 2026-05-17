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
MULTISPORT_ODDS_FIXTURE_PATH = (
    PROJECT_ROOT / "tests" / "fixtures" / "odds_api_multisport_events_sample.json"
)


def load_builder_tools():
    builder_module = importlib.import_module("src.collectors.report_input_builder")
    contracts_module = importlib.import_module("src.contracts.report_input")
    mapper_module = importlib.import_module("src.collectors.multisport_odds_mapper")
    return (
        builder_module.build_report_input_from_fixture_sources,
        builder_module.build_report_input_from_multisport_odds_fixture,
        builder_module.build_report_input_from_multisport_odds_events,
        builder_module.ReportInputBuilderError,
        contracts_module.ReportInput,
        mapper_module.load_multisport_odds_fixture,
    )


def load_normalized_builder_tools():
    builder_module = importlib.import_module("src.collectors.report_input_builder")
    contracts_module = importlib.import_module("src.contracts.report_input")
    mapper_module = importlib.import_module("src.collectors.multisport_odds_mapper")
    return (
        builder_module.build_report_input_from_normalized_odds_events,
        builder_module.ReportInputBuilderError,
        contracts_module.ReportInput,
        mapper_module.load_multisport_odds_fixture,
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
    build_report_input_from_fixture_sources, _, _, _, ReportInput, _ = load_builder_tools()
    matching_odds_path = write_matching_odds_fixture(tmp_path)

    report_input = build_report_input_from_fixture_sources(
        API_SPORTS_FIXTURE_PATH,
        matching_odds_path,
    )

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "east"
    assert len(report_input.games) == 2


def test_matching_games_receive_market_probability_data(tmp_path) -> None:
    build_report_input_from_fixture_sources, _, _, _, _, _ = load_builder_tools()
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
    build_report_input_from_fixture_sources, _, _, _, _, _ = load_builder_tools()
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
    build_report_input_from_fixture_sources, _, _, _, _, _ = load_builder_tools()
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
    build_report_input_from_fixture_sources, _, _, ReportInputBuilderError, _, _ = (
        load_builder_tools()
    )
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
    build_report_input_from_fixture_sources, _, _, _, _, _ = load_builder_tools()
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
    build_report_input_from_fixture_sources, _, _, _, _, _ = load_builder_tools()
    matching_odds_path = write_matching_odds_fixture(tmp_path)

    report_input = build_report_input_from_fixture_sources(
        API_SPORTS_FIXTURE_PATH,
        matching_odds_path,
    )

    assert "Matched local The Odds API-like sample where team names aligned." in (
        report_input.source_notes
    )


def test_multisport_baseball_event_fixture_can_create_report_input() -> None:
    _, build_multisport_fixture, _, _, ReportInput, _ = load_builder_tools()

    report_input = build_multisport_fixture(
        MULTISPORT_ODDS_FIXTURE_PATH,
        region="west",
        sport_keys=["baseball_mlb"],
    )
    game = report_input.games[0]

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "west"
    assert game.game_id == "baseball-event-001"
    assert game.home_team == "New York Sample Club"
    assert game.away_team == "Boston Sample Club"
    assert game.match_time_local == "2026-05-17T23:05:00Z"
    assert game.market_probability.implied_probability == 0.5263
    assert "sport_key: baseball_mlb" in game.input_notes


def test_multisport_soccer_event_fixture_can_create_report_input_and_note_draw() -> None:
    _, build_multisport_fixture, _, _, _, _ = load_builder_tools()

    report_input = build_multisport_fixture(
        MULTISPORT_ODDS_FIXTURE_PATH,
        region="west",
        sport_keys=["soccer_epl"],
    )
    game = report_input.games[0]

    assert report_input.region == "west"
    assert game.game_id == "soccer-event-001"
    assert game.market_probability.implied_probability == 0.4762
    assert "sport_key: soccer_epl" in game.input_notes
    assert any("Draw outcome was present" in note for note in game.input_notes)


def test_multisport_basketball_event_fixture_can_create_report_input() -> None:
    _, build_multisport_fixture, _, _, _, _ = load_builder_tools()

    report_input = build_multisport_fixture(
        MULTISPORT_ODDS_FIXTURE_PATH,
        region="west",
        sport_keys=["basketball_nba"],
    )
    game = report_input.games[0]

    assert report_input.region == "west"
    assert game.game_id == "basketball-event-001"
    assert game.home_team == "LA Sample Hoops"
    assert game.away_team == "Chicago Sample Hoops"
    assert game.market_probability.implied_probability == 0.5882


def test_multisport_missing_bookmakers_and_missing_h2h_remain_explicit() -> None:
    _, build_multisport_fixture, _, _, _, _ = load_builder_tools()

    report_input = build_multisport_fixture(
        MULTISPORT_ODDS_FIXTURE_PATH,
        region="east",
        sport_keys=["baseball_npb", "soccer_korea_kleague1"],
    )

    npb_game = next(game for game in report_input.games if game.game_id == "baseball-event-002")
    kleague_game = next(game for game in report_input.games if game.game_id == "soccer-event-002")

    assert npb_game.market_probability.implied_probability is None
    assert "Event does not include bookmaker data." in npb_game.missing_data
    assert "Event does not include an h2h market." in npb_game.missing_data
    assert kleague_game.market_probability.implied_probability is None
    assert "Event does not include an h2h market." in kleague_game.missing_data


def test_multisport_unsupported_sport_key_fails_clearly() -> None:
    _, _, build_multisport_events, ReportInputBuilderError, _, _ = load_builder_tools()
    unsupported_event = {
        "game_id": "unsupported-event",
        "event_id": "unsupported-event",
        "sport_key": "hockey_nhl",
        "sport_title": "NHL",
        "commence_time": "2026-05-17T12:30:00Z",
        "home_team": "Sample Home",
        "away_team": "Sample Away",
        "bookmaker_summaries": (),
        "h2h_market": None,
        "missing_data": (),
    }

    with pytest.raises(ReportInputBuilderError, match="Unsupported sport_key"):
        build_multisport_events([unsupported_event])


def test_multisport_builder_requires_region_or_sport_key_filter_for_mixed_events() -> None:
    _, _, build_multisport_events, ReportInputBuilderError, _, load_multisport_odds_fixture = (
        load_builder_tools()
    )
    odds_events = load_multisport_odds_fixture(MULTISPORT_ODDS_FIXTURE_PATH)

    with pytest.raises(
        ReportInputBuilderError,
        match="Could not infer a single region from mixed multisport odds events",
    ):
        build_multisport_events(odds_events)


def test_normalized_baseball_event_can_become_report_input() -> None:
    (
        build_from_normalized_events,
        _,
        ReportInput,
        load_multisport_odds_fixture,
    ) = load_normalized_builder_tools()
    normalized_events = load_multisport_odds_fixture(MULTISPORT_ODDS_FIXTURE_PATH)

    report_input = build_from_normalized_events(
        normalized_events,
        region="west",
        mode="live",
        analysis_mode="fallback",
        sport_keys=["baseball_mlb"],
        report_slot="global_night_preview",
    )
    game = report_input.games[0]

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "west"
    assert report_input.mode == "live"
    assert game.game_id == "baseball-event-001"
    assert game.home_team == "New York Sample Club"
    assert game.away_team == "Boston Sample Club"
    assert game.match_time_local == "2026-05-17T23:05:00Z"
    assert game.market_probability.implied_probability == 0.5263
    assert "analysis_mode: fallback" in report_input.source_notes
    assert "report_slot: global_night_preview" in report_input.source_notes


def test_normalized_soccer_event_can_become_report_input_and_preserve_draw_note() -> None:
    (
        build_from_normalized_events,
        _,
        _,
        load_multisport_odds_fixture,
    ) = load_normalized_builder_tools()
    normalized_events = load_multisport_odds_fixture(MULTISPORT_ODDS_FIXTURE_PATH)

    report_input = build_from_normalized_events(
        normalized_events,
        region="west",
        mode="live",
        analysis_mode="fallback",
        sport_keys=["soccer_epl"],
    )
    game = report_input.games[0]

    assert game.game_id == "soccer-event-001"
    assert any("Draw outcome was present" in note for note in game.input_notes)


def test_multiple_normalized_events_can_become_one_report_input() -> None:
    (
        build_from_normalized_events,
        _,
        _,
        load_multisport_odds_fixture,
    ) = load_normalized_builder_tools()
    normalized_events = load_multisport_odds_fixture(MULTISPORT_ODDS_FIXTURE_PATH)

    report_input = build_from_normalized_events(
        normalized_events,
        region="west",
        mode="live",
        analysis_mode="fallback",
        sport_keys=["baseball_mlb", "basketball_nba", "soccer_epl"],
    )

    assert len(report_input.games) == 3
    assert [game.game_id for game in report_input.games] == [
        "soccer-event-001",
        "baseball-event-001",
        "basketball-event-001",
    ]


def test_normalized_sport_key_filter_excluding_all_events_fails_clearly() -> None:
    (
        build_from_normalized_events,
        ReportInputBuilderError,
        _,
        load_multisport_odds_fixture,
    ) = load_normalized_builder_tools()
    normalized_events = load_multisport_odds_fixture(MULTISPORT_ODDS_FIXTURE_PATH)

    with pytest.raises(
        ReportInputBuilderError,
        match="No multisport odds events matched the requested region and sport_keys filter.",
    ):
        build_from_normalized_events(
            normalized_events,
            region="west",
            mode="live",
            analysis_mode="fallback",
            sport_keys=["soccer_korea_kleague1"],
        )


def test_normalized_missing_data_remains_explicit() -> None:
    (
        build_from_normalized_events,
        _,
        _,
        load_multisport_odds_fixture,
    ) = load_normalized_builder_tools()
    normalized_events = load_multisport_odds_fixture(MULTISPORT_ODDS_FIXTURE_PATH)

    report_input = build_from_normalized_events(
        normalized_events,
        region="east",
        mode="live",
        analysis_mode="fallback",
        sport_keys=["baseball_npb", "soccer_korea_kleague1"],
    )

    npb_game = next(game for game in report_input.games if game.game_id == "baseball-event-002")
    kleague_game = next(game for game in report_input.games if game.game_id == "soccer-event-002")

    assert "Event does not include bookmaker data." in npb_game.missing_data
    assert "Event does not include an h2h market." in npb_game.missing_data
    assert "Event does not include an h2h market." in kleague_game.missing_data


def test_normalized_builder_rejects_unsupported_region_clearly() -> None:
    (
        build_from_normalized_events,
        ReportInputBuilderError,
        _,
        load_multisport_odds_fixture,
    ) = load_normalized_builder_tools()
    normalized_events = load_multisport_odds_fixture(MULTISPORT_ODDS_FIXTURE_PATH)

    with pytest.raises(ReportInputBuilderError, match="Unsupported region 'north'"):
        build_from_normalized_events(
            normalized_events,
            region="north",
            mode="live",
            analysis_mode="fallback",
        )
