from __future__ import annotations

import re
from pathlib import Path

from src.collectors.api_sports import ODDS_MISSING_NOTE as API_SPORTS_ODDS_MISSING_NOTE
from src.collectors.api_sports import (
    ApiSportsCollectorError,
    load_report_input_from_api_sports_fixture,
)
from src.collectors.multisport_odds_mapper import (
    MISSING_H2H_MARKET_NOTE,
    MultiSportOddsMapperError,
    load_multisport_odds_fixture,
)
from src.collectors.multisport_odds_mapper import (
    NormalizedOddsEvent as MultiSportNormalizedOddsEvent,
)
from src.collectors.multisport_odds_mapper import (
    NormalizedOddsOutcome as MultiSportNormalizedOddsOutcome,
)
from src.collectors.odds_api import (
    NormalizedOddsEvent,
    OddsApiCollectorError,
    load_odds_api_events_fixture,
)
from src.config.sport_sources import get_source_by_league_key
from src.contracts.report_input import MarketProbability, ReportInput

ODDS_MATCH_SOURCE_NOTE = "Matched local The Odds API-like sample where team names aligned."
ODDS_ONLY_SOURCE_NOTE = "Built ReportInput from local The Odds API-like multisport event data."
REFERENCE_MISSING_NOTE = "Reference probability source is unavailable in this odds-only sample."
LINEUP_MISSING_NOTE = "Lineup data is unavailable in this odds-only sample."
INJURY_MISSING_NOTE = "Injury data is unavailable in this odds-only sample."
WEATHER_MISSING_NOTE = "Weather data is unavailable in this odds-only sample."
DRAW_NOTE_TEMPLATE = "Draw outcome was present in the h2h market at implied_probability {value}."
FALLBACK_SELECTION_NOTE = (
    "Home-team h2h outcome was unavailable, so the first measurable h2h outcome was used."
)


class ReportInputBuilderError(ValueError):
    """Raised when fixture sources cannot be combined into a valid ReportInput."""


def build_report_input_from_multisport_odds_fixture(
    odds_fixture_path: str | Path,
    *,
    region: str | None = None,
    sport_keys: list[str] | None = None,
) -> ReportInput:
    try:
        odds_events = load_multisport_odds_fixture(odds_fixture_path)
        return build_report_input_from_multisport_odds_events(
            odds_events,
            region=region,
            sport_keys=sport_keys,
        )
    except (MultiSportOddsMapperError, ValueError) as error:
        if isinstance(error, ReportInputBuilderError):
            raise
        raise ReportInputBuilderError(
            f"Could not build ReportInput from multisport odds fixture: {error}"
        ) from error


def build_report_input_from_multisport_odds_events(
    odds_events: list[MultiSportNormalizedOddsEvent] | list[dict],
    *,
    region: str | None = None,
    sport_keys: list[str] | None = None,
) -> ReportInput:
    normalized_events = _validate_multisport_odds_events(odds_events)
    filtered_events = _filter_multisport_events(
        normalized_events,
        region=region,
        sport_keys=sport_keys,
    )
    resolved_region = _resolve_multisport_region(filtered_events, requested_region=region)

    games_payload = [_build_game_input_from_multisport_event(event) for event in filtered_events]
    included_sport_keys = list(dict.fromkeys(event.sport_key for event in filtered_events))
    included_sports = list(
        dict.fromkeys(
            _get_region_metadata_for_sport_key(event.sport_key)[1] for event in filtered_events
        )
    )

    report_payload = {
        "report_id": f"multisport-odds-{resolved_region}-{len(games_payload)}-events",
        "region": resolved_region,
        "mode": "mock",
        "generated_at": filtered_events[0].commence_time,
        "report_name": f"Multisport Odds {resolved_region.title()} ReportInput Sample",
        "report_context": (
            "Odds-only local sample built from The Odds API-like multisport fixture data. "
            f"Included sports: {', '.join(included_sports)}."
        ),
        "source_notes": [
            ODDS_ONLY_SOURCE_NOTE,
            f"Included sport_keys: {', '.join(included_sport_keys)}.",
            REFERENCE_MISSING_NOTE,
        ],
        "missing_data": [
            REFERENCE_MISSING_NOTE,
            LINEUP_MISSING_NOTE,
            INJURY_MISSING_NOTE,
            WEATHER_MISSING_NOTE,
        ],
        "games": games_payload,
    }

    try:
        return ReportInput.model_validate(report_payload)
    except ValueError as error:
        raise ReportInputBuilderError(
            f"Multisport odds data failed ReportInput validation: {error}"
        ) from error


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


def _validate_multisport_odds_events(
    odds_events: list[MultiSportNormalizedOddsEvent] | list[dict],
) -> list[MultiSportNormalizedOddsEvent]:
    normalized_events: list[MultiSportNormalizedOddsEvent] = []
    for item in odds_events:
        if isinstance(item, MultiSportNormalizedOddsEvent):
            normalized_events.append(item)
            continue
        normalized_events.append(MultiSportNormalizedOddsEvent(**item))
    return normalized_events


def _filter_multisport_events(
    odds_events: list[MultiSportNormalizedOddsEvent],
    *,
    region: str | None = None,
    sport_keys: list[str] | None = None,
) -> list[MultiSportNormalizedOddsEvent]:
    requested_sport_keys = {value.strip() for value in sport_keys or [] if value.strip()}
    filtered_events: list[MultiSportNormalizedOddsEvent] = []

    for event in odds_events:
        event_region, _ = _get_region_metadata_for_sport_key(event.sport_key)
        if region is not None and event_region != region:
            continue
        if requested_sport_keys and event.sport_key not in requested_sport_keys:
            continue
        filtered_events.append(event)

    if not filtered_events:
        raise ReportInputBuilderError(
            "No multisport odds events matched the requested region and sport_keys filter."
        )
    return filtered_events


def _resolve_multisport_region(
    odds_events: list[MultiSportNormalizedOddsEvent],
    *,
    requested_region: str | None = None,
) -> str:
    derived_regions = {
        _get_region_metadata_for_sport_key(event.sport_key)[0] for event in odds_events
    }
    if requested_region is not None:
        if requested_region not in derived_regions and len(derived_regions) == 1:
            raise ReportInputBuilderError(
                "Requested region does not match the filtered multisport odds events: "
                f"expected {requested_region}, got {next(iter(derived_regions))}."
            )
        if len(derived_regions) > 1:
            raise ReportInputBuilderError(
                "Mixed east and west multisport odds events require an explicit sport_keys filter."
            )
        return requested_region

    if len(derived_regions) > 1:
        raise ReportInputBuilderError(
            "Could not infer a single region from mixed multisport odds events. "
            "Provide region or sport_keys explicitly."
        )

    return next(iter(derived_regions))


def _build_game_input_from_multisport_event(event: MultiSportNormalizedOddsEvent) -> dict:
    selected_probability, probability_missing_data, used_fallback_selection = (
        _select_multisport_market_probability(event)
    )
    market_payload = _build_multisport_market_probability_payload(
        event,
        selected_probability=selected_probability,
        probability_missing_data=probability_missing_data,
    )

    input_notes = [
        f"sport_key: {event.sport_key}",
        f"sport_title: {event.sport_title}",
        _summarize_multisport_bookmakers(event),
    ]
    if used_fallback_selection:
        input_notes.append(FALLBACK_SELECTION_NOTE)

    draw_note = _build_draw_note(event)
    if draw_note is not None:
        input_notes.append(draw_note)

    missing_data = _deduplicate_strings(
        [
            *event.missing_data,
            *market_payload["missing_data"],
            LINEUP_MISSING_NOTE,
            INJURY_MISSING_NOTE,
            WEATHER_MISSING_NOTE,
            REFERENCE_MISSING_NOTE,
        ]
    )
    game_notes = _deduplicate_strings([note for note in input_notes if note.strip()])
    odds_status = _determine_multisport_odds_status(
        event=event,
        selected_probability=selected_probability,
    )

    return {
        "game_id": event.game_id,
        "league": event.sport_title,
        "match_time_local": event.commence_time,
        "home_team": event.home_team,
        "away_team": event.away_team,
        "market_probability": market_payload,
        "reference_probability": {
            "source_name": "odds_only_reference_unavailable",
            "selection": event.home_team,
            "win_probability": None,
            "trust_level": "low",
            "missing_data": [REFERENCE_MISSING_NOTE],
        },
        "data_quality": {
            "trust_level": "medium" if selected_probability is not None else "low",
            "odds_status": odds_status,
            "lineup_status": "missing",
            "injury_status": "missing",
            "weather_status": "missing",
            "missing_data": missing_data,
            "notes": game_notes,
        },
        "input_notes": game_notes,
        "missing_data": missing_data,
    }


def _select_multisport_market_probability(
    event: MultiSportNormalizedOddsEvent,
) -> tuple[MultiSportNormalizedOddsOutcome | None, list[str], bool]:
    if event.h2h_market is None:
        return None, [MISSING_H2H_MARKET_NOTE], False

    measurable_outcomes = [
        outcome for outcome in event.h2h_market.outcomes if outcome.implied_probability is not None
    ]
    if not measurable_outcomes:
        missing_data = list(event.h2h_market.missing_data) or [MISSING_H2H_MARKET_NOTE]
        return None, missing_data, False

    for outcome in measurable_outcomes:
        if _normalize_name(outcome.selection) == _normalize_name(event.home_team):
            return outcome, list(outcome.missing_data), False

    selected_outcome = measurable_outcomes[0]
    return selected_outcome, list(selected_outcome.missing_data), True


def _build_multisport_market_probability_payload(
    event: MultiSportNormalizedOddsEvent,
    *,
    selected_probability: MultiSportNormalizedOddsOutcome | None,
    probability_missing_data: list[str],
) -> dict:
    if event.h2h_market is None or selected_probability is None:
        return {
            "source_name": (
                event.bookmaker_summaries[0].bookmaker_name
                if event.bookmaker_summaries
                else "The Odds API-like multisport sample"
            ),
            "market_name": "h2h",
            "selection": event.home_team,
            "implied_probability": None,
            "confidence_level": "low",
            "missing_data": _deduplicate_strings(
                [
                    *event.missing_data,
                    *probability_missing_data,
                ]
            ),
        }

    return {
        "source_name": event.h2h_market.source_bookmaker,
        "market_name": event.h2h_market.market_key,
        "selection": selected_probability.selection,
        "implied_probability": selected_probability.implied_probability,
        "confidence_level": "medium",
        "missing_data": _deduplicate_strings(probability_missing_data),
    }


def _build_draw_note(event: MultiSportNormalizedOddsEvent) -> str | None:
    if event.h2h_market is None:
        return None

    for outcome in event.h2h_market.outcomes:
        if _normalize_name(outcome.selection) != "draw":
            continue
        if outcome.implied_probability is None:
            return (
                "Draw outcome was present in the h2h market but its implied "
                "probability was missing."
            )
        return DRAW_NOTE_TEMPLATE.format(value=outcome.implied_probability)
    return None


def _summarize_multisport_bookmakers(event: MultiSportNormalizedOddsEvent) -> str:
    if not event.bookmaker_summaries:
        return "Bookmakers: none"

    summaries = [
        (
            f"{summary.bookmaker_name}["
            f"{', '.join(summary.market_keys) if summary.market_keys else 'none'}]"
        )
        for summary in event.bookmaker_summaries
    ]
    return f"Bookmakers: {', '.join(summaries)}"


def _determine_multisport_odds_status(
    *,
    event: MultiSportNormalizedOddsEvent,
    selected_probability: MultiSportNormalizedOddsOutcome | None,
) -> str:
    if event.h2h_market is None:
        return "missing"
    if selected_probability is None:
        return "partial"
    return "available"


def _get_region_metadata_for_sport_key(sport_key: str) -> tuple[str, str]:
    try:
        source = get_source_by_league_key(sport_key)
    except KeyError as error:
        raise ReportInputBuilderError(
            f"Unsupported sport_key for ReportInput builder: {sport_key}."
        ) from error
    region = "east" if source.report_slot == "asia_day_preview" else "west"
    return region, source.sport


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
