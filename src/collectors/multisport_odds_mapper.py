from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

SUPPORTED_SPORT_KEYS = (
    "baseball_mlb",
    "baseball_kbo",
    "baseball_npb",
    "basketball_nba",
    "soccer_epl",
    "soccer_korea_kleague1",
    "soccer_japan_j_league",
    "soccer_uefa_champs_league",
)

MISSING_BOOKMAKERS_NOTE = "Event does not include bookmaker data."
MISSING_H2H_MARKET_NOTE = "Event does not include an h2h market."
MISSING_OUTCOMES_NOTE = "The h2h market does not include any outcomes."
MISSING_HOME_TEAM_NOTE = "Event is missing required field 'home_team'."
MISSING_AWAY_TEAM_NOTE = "Event is missing required field 'away_team'."
MISSING_DECIMAL_ODDS_NOTE = "Outcome does not include decimal odds."


class MultiSportOddsMapperError(ValueError):
    """Raised when a local The Odds API-like sample cannot be mapped safely."""


@dataclass(frozen=True, slots=True)
class NormalizedOddsOutcome:
    selection: str
    decimal_odds: float | None
    implied_probability: float | None
    missing_data: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedOddsMarket:
    source_bookmaker: str
    market_key: str
    outcomes: tuple[NormalizedOddsOutcome, ...]
    missing_data: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BookmakerSummary:
    bookmaker_name: str
    market_keys: tuple[str, ...]
    has_h2h_market: bool


@dataclass(frozen=True, slots=True)
class NormalizedOddsEvent:
    game_id: str
    event_id: str
    sport_key: str
    sport_title: str
    commence_time: str
    home_team: str
    away_team: str
    bookmaker_summaries: tuple[BookmakerSummary, ...]
    h2h_market: NormalizedOddsMarket | None
    missing_data: tuple[str, ...] = ()


def load_multisport_odds_fixture(path: str | Path) -> list[NormalizedOddsEvent]:
    file_path = Path(path)
    payload = _read_fixture_payload(file_path)
    events = _extract_events(payload)
    return map_odds_events(events)


def normalize_live_odds_events_for_sport_key(
    sport_key: str,
    raw_events: list[Mapping[str, Any]],
) -> list[NormalizedOddsEvent]:
    normalized_sport_key = _validate_supported_sport_key(sport_key)
    if not isinstance(raw_events, list):
        raise MultiSportOddsMapperError(
            f"Live odds events for sport_key '{normalized_sport_key}' must be provided as a list."
        )
    if not all(isinstance(event, Mapping) for event in raw_events):
        raise MultiSportOddsMapperError(
            f"Live odds events for sport_key '{normalized_sport_key}' must contain only "
            "JSON objects."
        )

    normalized_events: list[NormalizedOddsEvent] = []
    for index, event in enumerate(raw_events):
        event_sport_key = str(event.get("sport_key", "")).strip()
        if not event_sport_key:
            raise MultiSportOddsMapperError(
                f"Live odds event at index {index} is missing required field 'sport_key'."
            )
        if event_sport_key != normalized_sport_key:
            raise MultiSportOddsMapperError(
                f"Live odds event at index {index} does not match requested sport_key "
                f"'{normalized_sport_key}'."
            )
        normalized_events.append(map_odds_event(event))

    return normalized_events


def normalize_live_odds_events(
    events_by_sport_key: Mapping[str, list[Mapping[str, Any]]],
) -> list[NormalizedOddsEvent]:
    if not isinstance(events_by_sport_key, Mapping):
        raise MultiSportOddsMapperError(
            "Live odds events must be grouped by sport_key in a JSON object."
        )

    combined_events: list[NormalizedOddsEvent] = []
    for sport_key, raw_events in events_by_sport_key.items():
        combined_events.extend(normalize_live_odds_events_for_sport_key(sport_key, raw_events))
    return combined_events


def map_odds_events(events: list[Mapping[str, Any]]) -> list[NormalizedOddsEvent]:
    if not isinstance(events, list):
        raise MultiSportOddsMapperError("events must be provided as a list.")
    if not all(isinstance(event, Mapping) for event in events):
        raise MultiSportOddsMapperError("events must contain only JSON objects.")
    return [map_odds_event(event) for event in events]


def map_odds_event(event: Mapping[str, Any]) -> NormalizedOddsEvent:
    if not isinstance(event, Mapping):
        raise MultiSportOddsMapperError("event must be a JSON object.")

    event_id = _read_required_text(event, "id")
    sport_key = _validate_supported_sport_key(_read_required_text(event, "sport_key"))

    home_team = _read_team_text(event, "home_team", MISSING_HOME_TEAM_NOTE)
    away_team = _read_team_text(event, "away_team", MISSING_AWAY_TEAM_NOTE)
    bookmakers = _read_bookmakers(event)
    bookmaker_summaries = summarize_bookmakers(event)
    h2h_market = extract_h2h_market(event)

    missing_data: list[str] = []
    if not bookmakers:
        missing_data.append(MISSING_BOOKMAKERS_NOTE)
    if h2h_market is None:
        missing_data.append(MISSING_H2H_MARKET_NOTE)

    return NormalizedOddsEvent(
        game_id=event_id,
        event_id=event_id,
        sport_key=sport_key,
        sport_title=_read_required_text(event, "sport_title"),
        commence_time=_read_required_text(event, "commence_time"),
        home_team=home_team,
        away_team=away_team,
        bookmaker_summaries=bookmaker_summaries,
        h2h_market=h2h_market,
        missing_data=tuple(dict.fromkeys(missing_data)),
    )


def decimal_odds_to_implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise MultiSportOddsMapperError("Decimal odds must be greater than 1.0.")
    return round(1.0 / decimal_odds, 4)


def extract_h2h_market(event: Mapping[str, Any]) -> NormalizedOddsMarket | None:
    bookmakers = _read_bookmakers(event)
    for bookmaker_index, bookmaker in enumerate(bookmakers):
        bookmaker_name = _read_required_text(bookmaker, "title")
        markets = _read_markets(bookmaker, bookmaker_name=bookmaker_name)
        for market_index, market in enumerate(markets):
            market_key = _read_required_text(
                market,
                "key",
                context=(
                    f"Bookmaker '{bookmaker_name}' market at index {market_index} "
                    "is missing required field 'key'."
                ),
            )
            if market_key != "h2h":
                continue
            return _build_h2h_market(
                bookmaker_name=bookmaker_name,
                market=market,
                bookmaker_index=bookmaker_index,
            )
    return None


def summarize_bookmakers(event: Mapping[str, Any]) -> tuple[BookmakerSummary, ...]:
    bookmakers = _read_bookmakers(event)
    summaries: list[BookmakerSummary] = []

    for bookmaker_index, bookmaker in enumerate(bookmakers):
        bookmaker_name = _read_required_text(
            bookmaker,
            "title",
            context=f"Bookmaker at index {bookmaker_index} is missing required field 'title'.",
        )
        markets = _read_markets(bookmaker, bookmaker_name=bookmaker_name)
        market_keys = tuple(
            _read_required_text(
                market,
                "key",
                context=(f"Bookmaker '{bookmaker_name}' market is missing required field 'key'."),
            )
            for market in markets
        )
        summaries.append(
            BookmakerSummary(
                bookmaker_name=bookmaker_name,
                market_keys=market_keys,
                has_h2h_market="h2h" in market_keys,
            )
        )

    return tuple(summaries)


def _validate_supported_sport_key(sport_key: str) -> str:
    normalized_sport_key = sport_key.strip()
    if normalized_sport_key not in SUPPORTED_SPORT_KEYS:
        supported_keys_text = ", ".join(SUPPORTED_SPORT_KEYS)
        raise MultiSportOddsMapperError(
            f"Unsupported sport_key '{normalized_sport_key}'. Use one of: {supported_keys_text}."
        )
    return normalized_sport_key


def _build_h2h_market(
    *,
    bookmaker_name: str,
    market: Mapping[str, Any],
    bookmaker_index: int,
) -> NormalizedOddsMarket:
    outcomes_payload = market.get("outcomes", [])
    if not isinstance(outcomes_payload, list):
        raise MultiSportOddsMapperError(
            f"Bookmaker '{bookmaker_name}' at index {bookmaker_index} "
            "must use a list for 'outcomes'."
        )

    if not outcomes_payload:
        return NormalizedOddsMarket(
            source_bookmaker=bookmaker_name,
            market_key="h2h",
            outcomes=(),
            missing_data=(MISSING_OUTCOMES_NOTE,),
        )

    normalized_outcomes: list[NormalizedOddsOutcome] = []
    for outcome_index, outcome in enumerate(outcomes_payload):
        if not isinstance(outcome, Mapping):
            raise MultiSportOddsMapperError(
                f"Outcome at index {outcome_index} for bookmaker '{bookmaker_name}' "
                "must be a JSON object."
            )
        selection = _read_required_text(
            outcome,
            "name",
            context=(
                f"Outcome at index {outcome_index} for bookmaker '{bookmaker_name}' "
                "is missing required field 'name'."
            ),
        )
        price = outcome.get("price")
        if price is None:
            normalized_outcomes.append(
                NormalizedOddsOutcome(
                    selection=selection,
                    decimal_odds=None,
                    implied_probability=None,
                    missing_data=(MISSING_DECIMAL_ODDS_NOTE,),
                )
            )
            continue

        decimal_odds = _coerce_decimal_odds(price, bookmaker_name=bookmaker_name)
        normalized_outcomes.append(
            NormalizedOddsOutcome(
                selection=selection,
                decimal_odds=decimal_odds,
                implied_probability=decimal_odds_to_implied_probability(decimal_odds),
                missing_data=(),
            )
        )

    return NormalizedOddsMarket(
        source_bookmaker=bookmaker_name,
        market_key="h2h",
        outcomes=tuple(normalized_outcomes),
        missing_data=(),
    )


def _read_fixture_payload(file_path: Path) -> dict[str, Any] | list[dict[str, Any]]:
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as error:
        raise MultiSportOddsMapperError(
            f"Could not read The Odds API multisport fixture file: {file_path}"
        ) from error

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise MultiSportOddsMapperError(
            f"Invalid JSON in The Odds API multisport fixture file {file_path}: {error.msg}"
        ) from error

    if not isinstance(payload, (dict, list)):
        raise MultiSportOddsMapperError(
            f"The Odds API multisport fixture file must contain a JSON object or list: {file_path}"
        )
    return payload


def _extract_events(
    payload: dict[str, Any] | list[dict[str, Any]],
) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return payload

    events = payload.get("events")
    if not isinstance(events, list):
        raise MultiSportOddsMapperError(
            "The Odds API multisport sample must include an 'events' list."
        )
    return events


def _read_required_text(
    payload: Mapping[str, Any],
    key: str,
    *,
    context: str | None = None,
) -> str:
    raw_value = payload.get(key)
    value = str(raw_value).strip() if raw_value is not None else ""
    if not value:
        raise MultiSportOddsMapperError(context or f"Event is missing required field '{key}'.")
    return value


def _read_team_text(payload: Mapping[str, Any], key: str, message: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise MultiSportOddsMapperError(message)
    return value


def _read_bookmakers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    bookmakers = event.get("bookmakers", [])
    if not isinstance(bookmakers, list):
        raise MultiSportOddsMapperError("Event field 'bookmakers' must be a list.")
    if not all(isinstance(bookmaker, Mapping) for bookmaker in bookmakers):
        raise MultiSportOddsMapperError("Event field 'bookmakers' must contain only JSON objects.")
    return list(bookmakers)


def _read_markets(
    bookmaker: Mapping[str, Any],
    *,
    bookmaker_name: str,
) -> list[Mapping[str, Any]]:
    markets = bookmaker.get("markets", [])
    if not isinstance(markets, list):
        raise MultiSportOddsMapperError(
            f"Bookmaker '{bookmaker_name}' must use a list for 'markets'."
        )
    if not all(isinstance(market, Mapping) for market in markets):
        raise MultiSportOddsMapperError(
            f"Bookmaker '{bookmaker_name}' must use JSON objects inside 'markets'."
        )
    return list(markets)


def _coerce_decimal_odds(price: Any, *, bookmaker_name: str) -> float:
    try:
        decimal_odds = float(price)
    except (TypeError, ValueError) as error:
        raise MultiSportOddsMapperError(
            f"Bookmaker '{bookmaker_name}' includes a non-numeric decimal odds value."
        ) from error
    if decimal_odds <= 1.0:
        raise MultiSportOddsMapperError(
            f"Bookmaker '{bookmaker_name}' includes invalid decimal odds {decimal_odds}."
        )
    return decimal_odds
