from __future__ import annotations

import re
from pathlib import Path

from src.collectors.api_sports import ODDS_MISSING_NOTE as API_SPORTS_ODDS_MISSING_NOTE
from src.collectors.api_sports import (
    ApiSportsCollectorError,
    load_report_input_from_api_sports_fixture,
)
from src.collectors.odds_api import (
    NormalizedOddsEvent,
    OddsApiCollectorError,
    load_odds_api_events_fixture,
)
from src.contracts.report_input import MarketProbability, ReportInput

ODDS_MATCH_SOURCE_NOTE = "Matched local The Odds API-like sample where team names aligned."


class ReportInputBuilderError(ValueError):
    """Raised when fixture sources cannot be combined into a valid ReportInput."""


def build_report_input_from_fixture_sources(
    api_sports_fixture_path: str | Path,
    odds_api_fixture_path: str | Path,
) -> ReportInput:
    try:
        fixture_report_input = load_report_input_from_api_sports_fixture(api_sports_fixture_path)
        odds_events = load_odds_api_events_fixture(odds_api_fixture_path)
        return build_report_input_from_parsed_sources(fixture_report_input, odds_events)
    except (ApiSportsCollectorError, OddsApiCollectorError, ValueError) as error:
        if isinstance(error, ReportInputBuilderError):
            raise
        raise ReportInputBuilderError(
            f"Could not build ReportInput from fixture sources: {error}"
        ) from error


def build_report_input_from_parsed_sources(
    fixture_report_input: ReportInput | dict,
    odds_events: list[NormalizedOddsEvent] | list[dict],
) -> ReportInput:
    report = (
        fixture_report_input
        if isinstance(fixture_report_input, ReportInput)
        else ReportInput.model_validate(fixture_report_input)
    )
    normalized_events = _validate_odds_events(odds_events)

    report_payload = report.model_dump()
    odds_by_matchup = {
        _build_matchup_key(event.home_team, event.away_team): event for event in normalized_events
    }

    for game_payload in report_payload["games"]:
        _apply_matched_odds_to_game(game_payload, odds_by_matchup)

    report_payload["source_notes"] = _deduplicate_strings(
        [
            *report_payload["source_notes"],
            ODDS_MATCH_SOURCE_NOTE,
        ]
    )
    report_payload["missing_data"] = _update_report_missing_data(
        report_payload["games"],
        report_payload["missing_data"],
    )

    try:
        return ReportInput.model_validate(report_payload)
    except ValueError as error:
        raise ReportInputBuilderError(
            f"Combined fixture data failed ReportInput validation: {error}"
        ) from error


def _validate_odds_events(
    odds_events: list[NormalizedOddsEvent] | list[dict],
) -> list[NormalizedOddsEvent]:
    normalized_events: list[NormalizedOddsEvent] = []
    for item in odds_events:
        if isinstance(item, NormalizedOddsEvent):
            normalized_events.append(item)
            continue
        normalized_events.append(NormalizedOddsEvent.model_validate(item))
    return normalized_events


def _apply_matched_odds_to_game(
    game_payload: dict, odds_by_matchup: dict[str, NormalizedOddsEvent]
) -> None:
    matchup_key = _build_matchup_key(game_payload["home_team"], game_payload["away_team"])
    matched_event = odds_by_matchup.get(matchup_key)
    if matched_event is None:
        return

    selected_probability = _select_market_probability(
        matched_event,
        preferred_selection=game_payload["home_team"],
    )
    if selected_probability is None:
        return

    game_payload["market_probability"] = selected_probability.model_dump()
    game_payload["missing_data"] = _remove_value(
        game_payload["missing_data"],
        API_SPORTS_ODDS_MISSING_NOTE,
    )
    game_payload["input_notes"] = _deduplicate_strings(
        [
            *game_payload["input_notes"],
            (
                "Matched market probability from The Odds API-like sample for "
                f"{selected_probability.selection}."
            ),
        ]
    )

    data_quality = game_payload["data_quality"]
    data_quality["odds_status"] = "available"
    data_quality["missing_data"] = _remove_value(
        data_quality["missing_data"],
        API_SPORTS_ODDS_MISSING_NOTE,
    )
    data_quality["notes"] = _deduplicate_strings(
        [
            *data_quality["notes"],
            (
                "Matched market sample from "
                f"{selected_probability.source_name} ({selected_probability.market_name})."
            ),
        ]
    )


def _select_market_probability(
    odds_event: NormalizedOddsEvent,
    *,
    preferred_selection: str,
) -> MarketProbability | None:
    all_probabilities = odds_event.as_market_probabilities()
    measurable_probabilities = [
        probability
        for probability in all_probabilities
        if probability.implied_probability is not None
    ]
    if not measurable_probabilities:
        return None

    for probability in measurable_probabilities:
        if _normalize_name(probability.selection) == _normalize_name(preferred_selection):
            return probability

    return measurable_probabilities[0]


def _update_report_missing_data(games: list[dict], report_missing_data: list[str]) -> list[str]:
    has_missing_market_probability = any(
        game["market_probability"]["implied_probability"] is None for game in games
    )
    if has_missing_market_probability:
        return _deduplicate_strings(report_missing_data)
    return _remove_value(report_missing_data, API_SPORTS_ODDS_MISSING_NOTE)


def _build_matchup_key(home_team: str, away_team: str) -> str:
    return f"{_normalize_name(home_team)}::{_normalize_name(away_team)}"


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _remove_value(values: list[str], target: str) -> list[str]:
    return [value for value in values if value != target]


def _deduplicate_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value.strip()))
