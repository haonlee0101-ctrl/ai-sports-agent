from __future__ import annotations

import importlib
import json
import re
import socket
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "odds_api_multisport_events_sample.json"


def load_mapper_tools():
    mapper_module = importlib.import_module("src.collectors.multisport_odds_mapper")
    return (
        mapper_module.load_multisport_odds_fixture,
        mapper_module.map_odds_event,
        mapper_module.map_odds_events,
        mapper_module.decimal_odds_to_implied_probability,
        mapper_module.extract_h2h_market,
        mapper_module.summarize_bookmakers,
        mapper_module.MultiSportOddsMapperError,
        mapper_module.SUPPORTED_SPORT_KEYS,
        mapper_module.MISSING_BOOKMAKERS_NOTE,
        mapper_module.MISSING_H2H_MARKET_NOTE,
    )


def load_mapper_module():
    return importlib.import_module("src.collectors.multisport_odds_mapper")


def load_fixture_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_valid_soccer_event_maps_to_normalized_output() -> None:
    load_fixture, _, _, _, _, _, _, _, _, _ = load_mapper_tools()

    events = load_fixture(FIXTURE_PATH)
    soccer_event = events[0]

    assert soccer_event.sport_key == "soccer_epl"
    assert soccer_event.game_id == "soccer-event-001"
    assert soccer_event.home_team == "London Sample FC"
    assert soccer_event.away_team == "Liverpool Sample FC"
    assert soccer_event.h2h_market is not None
    assert soccer_event.h2h_market.source_bookmaker == "SampleBook"


def test_valid_baseball_event_maps_to_normalized_output() -> None:
    load_fixture, _, _, _, _, _, _, _, _, _ = load_mapper_tools()

    events = load_fixture(FIXTURE_PATH)
    baseball_event = events[1]

    assert baseball_event.sport_key == "baseball_mlb"
    assert baseball_event.game_id == "baseball-event-001"
    assert baseball_event.commence_time == "2026-05-17T23:05:00Z"


def test_valid_basketball_event_maps_to_normalized_output() -> None:
    load_fixture, _, _, _, _, _, _, _, _, _ = load_mapper_tools()

    events = load_fixture(FIXTURE_PATH)
    basketball_event = events[2]

    assert basketball_event.sport_key == "basketball_nba"
    assert basketball_event.bookmaker_summaries[0].bookmaker_name == "HoopsBook"


def test_event_id_becomes_stable_game_id() -> None:
    load_fixture, _, _, _, _, _, _, _, _, _ = load_mapper_tools()

    events = load_fixture(FIXTURE_PATH)

    assert events[0].game_id == events[0].event_id
    assert events[1].game_id == events[1].event_id


def test_sport_key_and_commence_time_are_preserved() -> None:
    load_fixture, _, _, _, _, _, _, _, _, _ = load_mapper_tools()

    events = load_fixture(FIXTURE_PATH)

    assert events[0].sport_key == "soccer_epl"
    assert events[0].commence_time == "2026-05-17T12:30:00Z"


def test_home_and_away_teams_are_preserved() -> None:
    load_fixture, _, _, _, _, _, _, _, _, _ = load_mapper_tools()

    events = load_fixture(FIXTURE_PATH)

    assert events[2].home_team == "LA Sample Hoops"
    assert events[2].away_team == "Chicago Sample Hoops"


def test_h2h_decimal_odds_produce_implied_probabilities() -> None:
    load_fixture, _, _, decimal_odds_to_implied_probability, _, _, _, _, _, _ = load_mapper_tools()

    events = load_fixture(FIXTURE_PATH)
    baseball_market = events[1].h2h_market

    assert baseball_market is not None
    assert decimal_odds_to_implied_probability(1.9) == 0.5263
    assert baseball_market.outcomes[0].implied_probability == 0.5263
    assert baseball_market.outcomes[1].implied_probability == 0.5


def test_soccer_draw_outcome_is_preserved_when_present() -> None:
    load_fixture, _, _, _, _, _, _, _, _, _ = load_mapper_tools()

    events = load_fixture(FIXTURE_PATH)
    soccer_market = events[0].h2h_market

    assert soccer_market is not None
    selections = [outcome.selection for outcome in soccer_market.outcomes]
    assert "Draw" in selections


def test_missing_bookmakers_remains_explicit() -> None:
    load_fixture, _, _, _, _, _, _, _, missing_bookmakers_note, missing_h2h_note = (
        load_mapper_tools()
    )

    events = load_fixture(FIXTURE_PATH)
    missing_bookmakers_event = events[3]

    assert missing_bookmakers_event.bookmaker_summaries == ()
    assert missing_bookmakers_event.h2h_market is None
    assert missing_bookmakers_note in missing_bookmakers_event.missing_data
    assert missing_h2h_note in missing_bookmakers_event.missing_data


def test_missing_h2h_market_remains_explicit() -> None:
    load_fixture, _, _, _, _, _, _, _, _, missing_h2h_note = load_mapper_tools()

    events = load_fixture(FIXTURE_PATH)
    missing_h2h_event = events[4]

    assert missing_h2h_event.h2h_market is None
    assert missing_h2h_note in missing_h2h_event.missing_data
    assert missing_h2h_event.bookmaker_summaries[0].market_keys == ("totals",)


def test_missing_home_team_fails_clearly() -> None:
    _, map_odds_event, _, _, _, _, mapper_error, _, _, _ = load_mapper_tools()
    event = {
        "id": "broken-event",
        "sport_key": "soccer_epl",
        "sport_title": "Premier League",
        "commence_time": "2026-05-17T12:30:00Z",
        "away_team": "Missing Home FC",
        "bookmakers": [],
    }

    with pytest.raises(mapper_error, match="home_team"):
        map_odds_event(event)


def test_missing_away_team_fails_clearly() -> None:
    _, map_odds_event, _, _, _, _, mapper_error, _, _, _ = load_mapper_tools()
    event = {
        "id": "broken-event",
        "sport_key": "soccer_epl",
        "sport_title": "Premier League",
        "commence_time": "2026-05-17T12:30:00Z",
        "home_team": "Missing Away FC",
        "bookmakers": [],
    }

    with pytest.raises(mapper_error, match="away_team"):
        map_odds_event(event)


def test_unsupported_sport_key_fails_clearly() -> None:
    _, map_odds_event, _, _, _, _, mapper_error, _, _, _ = load_mapper_tools()
    event = {
        "id": "unsupported-event",
        "sport_key": "hockey_nhl",
        "sport_title": "NHL",
        "commence_time": "2026-05-17T12:30:00Z",
        "home_team": "Sample Home",
        "away_team": "Sample Away",
        "bookmakers": [],
    }

    with pytest.raises(mapper_error, match="Unsupported sport_key"):
        map_odds_event(event)


def test_map_odds_events_handles_multiple_events_deterministically() -> None:
    _, _, map_odds_events, _, _, _, _, _, _, _ = load_mapper_tools()
    payload = load_fixture_payload()

    mapped_events = map_odds_events(payload["events"])

    assert [event.game_id for event in mapped_events] == [
        "soccer-event-001",
        "baseball-event-001",
        "basketball-event-001",
        "baseball-event-002",
        "soccer-event-002",
    ]


def test_extract_h2h_market_and_bookmaker_summary_are_preserved() -> None:
    _, map_odds_event, _, _, extract_h2h_market, summarize_bookmakers, _, _, _, _ = (
        load_mapper_tools()
    )
    payload = load_fixture_payload()

    event = payload["events"][0]
    mapped_event = map_odds_event(event)
    extracted_market = extract_h2h_market(event)
    bookmaker_summaries = summarize_bookmakers(event)

    assert extracted_market is not None
    assert extracted_market.market_key == "h2h"
    assert bookmaker_summaries[0].market_keys == ("h2h",)
    assert bookmaker_summaries == mapped_event.bookmaker_summaries


@pytest.mark.parametrize(
    "sport_key",
    [
        "baseball_mlb",
        "baseball_kbo",
        "baseball_npb",
        "basketball_nba",
        "soccer_epl",
        "soccer_korea_kleague1",
        "soccer_japan_j_league",
        "soccer_uefa_champs_league",
    ],
)
def test_supported_sport_keys_are_accepted(sport_key: str) -> None:
    _, map_odds_event, _, _, _, _, _, supported_sport_keys, _, _ = load_mapper_tools()
    base_event = {
        "id": f"event-{sport_key}",
        "sport_key": sport_key,
        "sport_title": "Sample Sport",
        "commence_time": "2026-05-17T12:30:00Z",
        "home_team": "Sample Home",
        "away_team": "Sample Away",
        "bookmakers": [],
    }

    mapped_event = map_odds_event(base_event)

    assert sport_key in supported_sport_keys
    assert mapped_event.sport_key == sport_key


def test_no_real_api_calls_are_made(monkeypatch) -> None:
    load_fixture, _, _, _, _, _, _, _, _, _ = load_mapper_tools()

    def fail_on_network(*args, **kwargs):
        raise AssertionError("External network access should not be used.")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)

    events = load_fixture(FIXTURE_PATH)

    assert len(events) == 5


def test_no_api_keys_are_required() -> None:
    load_fixture, _, _, _, _, _, _, _, _, _ = load_mapper_tools()

    events = load_fixture(FIXTURE_PATH)

    assert events[0].sport_key == "soccer_epl"


def test_live_baseball_event_normalizes_successfully() -> None:
    mapper_module = load_mapper_module()
    payload = load_fixture_payload()

    normalized_events = mapper_module.normalize_live_odds_events_for_sport_key(
        "baseball_mlb",
        [payload["events"][1]],
    )

    assert len(normalized_events) == 1
    assert normalized_events[0].game_id == "baseball-event-001"
    assert normalized_events[0].sport_key == "baseball_mlb"
    assert normalized_events[0].home_team == "New York Sample Club"


def test_live_soccer_event_normalizes_successfully() -> None:
    mapper_module = load_mapper_module()
    payload = load_fixture_payload()

    normalized_events = mapper_module.normalize_live_odds_events_for_sport_key(
        "soccer_epl",
        [payload["events"][0]],
    )

    assert len(normalized_events) == 1
    assert normalized_events[0].game_id == "soccer-event-001"
    assert normalized_events[0].sport_key == "soccer_epl"
    assert any(outcome.selection == "Draw" for outcome in normalized_events[0].h2h_market.outcomes)


def test_live_basketball_event_normalizes_successfully() -> None:
    mapper_module = load_mapper_module()
    payload = load_fixture_payload()

    normalized_events = mapper_module.normalize_live_odds_events_for_sport_key(
        "basketball_nba",
        [payload["events"][2]],
    )

    assert len(normalized_events) == 1
    assert normalized_events[0].game_id == "basketball-event-001"
    assert normalized_events[0].sport_key == "basketball_nba"
    assert normalized_events[0].away_team == "Chicago Sample Hoops"


def test_live_events_for_multiple_sport_keys_normalize_to_combined_output() -> None:
    mapper_module = load_mapper_module()
    payload = load_fixture_payload()

    normalized_events = mapper_module.normalize_live_odds_events(
        {
            "baseball_mlb": [payload["events"][1]],
            "soccer_epl": [payload["events"][0]],
            "basketball_nba": [payload["events"][2]],
        }
    )

    assert [event.game_id for event in normalized_events] == [
        "baseball-event-001",
        "soccer-event-001",
        "basketball-event-001",
    ]


def test_live_missing_outcomes_remain_explicit() -> None:
    mapper_module = load_mapper_module()
    event = {
        "id": "soccer-live-002",
        "sport_key": "soccer_epl",
        "sport_title": "Premier League",
        "commence_time": "2026-05-17T12:30:00Z",
        "home_team": "Sample Home",
        "away_team": "Sample Away",
        "bookmakers": [{"title": "SampleBook", "markets": [{"key": "h2h", "outcomes": []}]}],
    }

    normalized_events = mapper_module.normalize_live_odds_events_for_sport_key(
        "soccer_epl",
        [event],
    )

    assert len(normalized_events) == 1
    assert normalized_events[0].h2h_market is not None
    assert normalized_events[0].h2h_market.missing_data == (
        "The h2h market does not include any outcomes.",
    )


def test_live_missing_probability_remains_explicit() -> None:
    mapper_module = load_mapper_module()
    event = {
        "id": "baseball-live-002",
        "sport_key": "baseball_mlb",
        "sport_title": "MLB",
        "commence_time": "2026-05-17T23:05:00Z",
        "home_team": "Sample Home",
        "away_team": "Sample Away",
        "bookmakers": [
            {
                "title": "SampleBook",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Sample Home", "price": None},
                            {"name": "Sample Away", "price": 2.2},
                        ],
                    }
                ],
            }
        ],
    }

    normalized_events = mapper_module.normalize_live_odds_events_for_sport_key(
        "baseball_mlb",
        [event],
    )

    assert len(normalized_events) == 1
    assert normalized_events[0].h2h_market is not None
    assert normalized_events[0].h2h_market.outcomes[0].implied_probability is None
    assert normalized_events[0].h2h_market.outcomes[0].missing_data == (
        "Outcome does not include decimal odds.",
    )


def test_live_missing_bookmakers_and_h2h_remain_explicit() -> None:
    mapper_module = load_mapper_module()
    _, _, _, _, _, _, _, _, missing_bookmakers_note, missing_h2h_note = load_mapper_tools()
    payload = load_fixture_payload()

    normalized_events = mapper_module.normalize_live_odds_events_for_sport_key(
        "baseball_npb",
        [payload["events"][3]],
    )

    assert len(normalized_events) == 1
    assert missing_bookmakers_note in normalized_events[0].missing_data
    assert missing_h2h_note in normalized_events[0].missing_data


def test_live_missing_h2h_market_remains_explicit() -> None:
    mapper_module = load_mapper_module()
    _, _, _, _, _, _, _, _, _, missing_h2h_note = load_mapper_tools()
    payload = load_fixture_payload()

    normalized_events = mapper_module.normalize_live_odds_events_for_sport_key(
        "soccer_korea_kleague1",
        [payload["events"][4]],
    )

    assert len(normalized_events) == 1
    assert missing_h2h_note in normalized_events[0].missing_data


def test_live_missing_draw_is_left_uninvented_when_not_present() -> None:
    mapper_module = load_mapper_module()
    event = {
        "id": "soccer-live-003",
        "sport_key": "soccer_epl",
        "sport_title": "Premier League",
        "commence_time": "2026-05-17T12:30:00Z",
        "home_team": "Sample Home",
        "away_team": "Sample Away",
        "bookmakers": [
            {
                "title": "SampleBook",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Sample Home", "price": 2.1},
                            {"name": "Sample Away", "price": 3.5},
                        ],
                    }
                ],
            }
        ],
    }

    normalized_events = mapper_module.normalize_live_odds_events_for_sport_key(
        "soccer_epl",
        [event],
    )

    assert len(normalized_events) == 1
    assert normalized_events[0].h2h_market is not None
    assert [outcome.selection for outcome in normalized_events[0].h2h_market.outcomes] == [
        "Sample Home",
        "Sample Away",
    ]


def test_malformed_live_event_payload_fails_clearly() -> None:
    mapper_module = load_mapper_module()
    _, _, _, _, _, _, mapper_error, _, _, _ = load_mapper_tools()

    with pytest.raises(
        mapper_error,
        match="Live odds events for sport_key 'baseball_mlb' must be provided as a list.",
    ):
        mapper_module.normalize_live_odds_events_for_sport_key(
            "baseball_mlb",
            {"id": "not-a-list"},
        )

    with pytest.raises(
        mapper_error,
        match="Live odds event at index 0 does not match requested sport_key 'baseball_mlb'.",
    ):
        mapper_module.normalize_live_odds_events_for_sport_key(
            "baseball_mlb",
            [
                {
                    "id": "wrong-sport",
                    "sport_key": "soccer_epl",
                    "sport_title": "Premier League",
                    "commence_time": "2026-05-17T12:30:00Z",
                    "home_team": "Sample Home",
                    "away_team": "Sample Away",
                    "bookmakers": [],
                }
            ],
        )

    with pytest.raises(
        mapper_error,
        match="Live odds events must be grouped by sport_key in a JSON object.",
    ):
        mapper_module.normalize_live_odds_events([{"sport_key": "baseball_mlb"}])


def test_no_secrets_are_hardcoded() -> None:
    mapper_source = (PROJECT_ROOT / "src" / "collectors" / "multisport_odds_mapper.py").read_text(
        encoding="utf-8"
    )
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"https?://[^\\s\"']+[?&](?:api_?key|key|token)=",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, mapper_source) is None


def test_run_report_file_is_unchanged_in_supported_shape() -> None:
    run_report_text = (PROJECT_ROOT / "run_report.py").read_text(encoding="utf-8")

    assert "--report-slot" in run_report_text
    assert "REPORT_SLOT_REGION_MAP" in run_report_text


def test_workflow_file_is_unchanged_in_supported_shape() -> None:
    workflow_text = (PROJECT_ROOT / ".github" / "workflows" / "report.yml").read_text(
        encoding="utf-8"
    )

    assert 'cron: "0 16 * * *"' in workflow_text
    assert 'cron: "0 4 * * *"' in workflow_text
    assert '--report-slot "${REPORT_SLOT}"' in workflow_text


def test_sport_sources_file_is_unchanged_in_supported_shape() -> None:
    sport_sources_text = (PROJECT_ROOT / "src" / "config" / "sport_sources.py").read_text(
        encoding="utf-8"
    )

    assert "asia_day_preview" in sport_sources_text
    assert "global_night_preview" in sport_sources_text
    assert "soccer_uefa_champs_league" in sport_sources_text
