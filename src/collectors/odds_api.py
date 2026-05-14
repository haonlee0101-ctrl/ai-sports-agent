from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from src.contracts.report_input import MarketProbability, clean_required_text, clean_text_list

ODDS_MISSING_NOTE = "The Odds API-like sample does not include bookmaker odds data."
OUTCOME_MISSING_NOTE = "The Odds API-like sample market does not include outcome odds data."


class OddsApiCollectorError(ValueError):
    """Raised when a local The Odds API-like fixture cannot be parsed safely."""


class NormalizedOddsOutcome(BaseModel):
    """One normalized bookmaker outcome with optional implied probability."""

    model_config = ConfigDict(extra="forbid")

    selection: str = Field(..., description="Outcome display name.")
    decimal_odds: float | None = Field(
        default=None,
        gt=1.0,
        description="Decimal odds value when the sample contains one.",
    )
    implied_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Simple implied probability derived from decimal odds.",
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Explicit missing-data notes for this outcome.",
    )

    @field_validator("selection")
    @classmethod
    def validate_selection(cls, value: str) -> str:
        return clean_required_text(value)

    @field_validator("missing_data")
    @classmethod
    def validate_missing_data(cls, values: list[str]) -> list[str]:
        return clean_text_list(values)


class NormalizedOddsMarket(BaseModel):
    """One normalized market from a bookmaker sample."""

    model_config = ConfigDict(extra="forbid")

    bookmaker_name: str = Field(..., description="Bookmaker title from the sample payload.")
    market_name: str = Field(..., description="Market key such as h2h.")
    outcomes: list[NormalizedOddsOutcome] = Field(
        default_factory=list,
        description="Available outcomes for the normalized market.",
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Explicit missing-data notes for the market.",
    )

    @field_validator("bookmaker_name", "market_name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return clean_required_text(value)

    @field_validator("missing_data")
    @classmethod
    def validate_missing_data(cls, values: list[str]) -> list[str]:
        return clean_text_list(values)

    def as_market_probabilities(self) -> list[MarketProbability]:
        normalized_probabilities: list[MarketProbability] = []
        for outcome in self.outcomes:
            normalized_probabilities.append(
                MarketProbability(
                    source_name=self.bookmaker_name,
                    market_name=self.market_name,
                    selection=outcome.selection,
                    implied_probability=outcome.implied_probability,
                    confidence_level="medium" if outcome.implied_probability is not None else "low",
                    missing_data=outcome.missing_data,
                )
            )
        return normalized_probabilities


class NormalizedOddsEvent(BaseModel):
    """One normalized event entry from a The Odds API-like sample."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., description="Unique event identifier from the sample.")
    sport_key: str = Field(..., description="Sport key from the sample payload.")
    sport_title: str = Field(..., description="Human-readable sport title.")
    commence_time: str = Field(..., description="Event start time as text.")
    home_team: str = Field(..., description="Home team display name.")
    away_team: str = Field(..., description="Away team display name.")
    markets: list[NormalizedOddsMarket] = Field(
        default_factory=list,
        description="Normalized bookmaker markets for the event.",
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Explicit missing-data notes at the event level.",
    )

    @field_validator(
        "event_id",
        "sport_key",
        "sport_title",
        "commence_time",
        "home_team",
        "away_team",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return clean_required_text(value)

    @field_validator("missing_data")
    @classmethod
    def validate_missing_data(cls, values: list[str]) -> list[str]:
        return clean_text_list(values)

    def as_market_probabilities(self) -> list[MarketProbability]:
        normalized_probabilities: list[MarketProbability] = []
        for market in self.markets:
            normalized_probabilities.extend(market.as_market_probabilities())
        return normalized_probabilities


def load_odds_api_events_fixture(path: str | Path) -> list[NormalizedOddsEvent]:
    file_path = Path(path)
    payload = _read_fixture_payload(file_path)
    return parse_odds_api_events_response(payload)


def parse_odds_api_events_response(payload: dict | list) -> list[NormalizedOddsEvent]:
    events_payload = _get_events_payload(payload)
    if not events_payload:
        raise OddsApiCollectorError(
            "The Odds API-like sample must include at least one event entry."
        )

    try:
        return [_build_normalized_event(item, index) for index, item in enumerate(events_payload)]
    except ValidationError as error:
        raise OddsApiCollectorError(
            f"The Odds API-like sample failed normalized validation: {error}"
        ) from error


def decimal_odds_to_implied_probability(decimal_odds: float) -> float:
    """Convert decimal odds to a simple implied probability without vig adjustment."""

    if decimal_odds <= 1.0:
        raise OddsApiCollectorError("Decimal odds must be greater than 1.0.")
    return round(1.0 / decimal_odds, 4)


def _read_fixture_payload(file_path: Path) -> dict | list:
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as error:
        raise OddsApiCollectorError(
            f"Could not read The Odds API-like fixture file: {file_path}"
        ) from error

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise OddsApiCollectorError(
            f"Invalid JSON in The Odds API-like fixture file {file_path}: {error.msg}"
        ) from error

    if not isinstance(payload, (dict, list)):
        raise OddsApiCollectorError(
            f"The Odds API-like fixture file must contain a JSON object or list: {file_path}"
        )

    return payload


def _get_events_payload(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        if not all(isinstance(item, dict) for item in payload):
            raise OddsApiCollectorError(
                "The Odds API-like sample list must contain only JSON objects."
            )
        return payload

    events = payload.get("events")
    if not isinstance(events, list):
        raise OddsApiCollectorError("The Odds API-like sample must include an 'events' list.")
    if not all(isinstance(item, dict) for item in events):
        raise OddsApiCollectorError(
            "The Odds API-like 'events' list must contain only JSON objects."
        )
    return events


def _build_normalized_event(item: dict, index: int) -> NormalizedOddsEvent:
    home_team = _read_required_value(item, "home_team", index)
    away_team = _read_required_value(item, "away_team", index)
    bookmakers = item.get("bookmakers", [])

    missing_data: list[str] = []
    markets: list[NormalizedOddsMarket] = []

    if not isinstance(bookmakers, list):
        raise OddsApiCollectorError(f"Event at index {index} must use a list for 'bookmakers'.")

    if not bookmakers:
        missing_data.append(ODDS_MISSING_NOTE)

    for bookmaker_index, bookmaker in enumerate(bookmakers):
        markets.extend(_build_markets(bookmaker, index, bookmaker_index, home_team, away_team))

    if not markets and ODDS_MISSING_NOTE not in missing_data:
        missing_data.append(ODDS_MISSING_NOTE)

    return NormalizedOddsEvent(
        event_id=str(_read_required_value(item, "id", index)),
        sport_key=str(_read_required_value(item, "sport_key", index)),
        sport_title=str(_read_required_value(item, "sport_title", index)),
        commence_time=str(_read_required_value(item, "commence_time", index)),
        home_team=str(home_team),
        away_team=str(away_team),
        markets=markets,
        missing_data=missing_data,
    )


def _build_markets(
    bookmaker: dict,
    event_index: int,
    bookmaker_index: int,
    home_team: str,
    away_team: str,
) -> list[NormalizedOddsMarket]:
    if not isinstance(bookmaker, dict):
        raise OddsApiCollectorError(
            f"Bookmaker at event index {event_index}, bookmaker index {bookmaker_index} "
            "must be a JSON object."
        )

    bookmaker_name = str(_read_required_value(bookmaker, "title", event_index))
    markets_payload = bookmaker.get("markets", [])
    if not isinstance(markets_payload, list):
        raise OddsApiCollectorError(
            f"Bookmaker '{bookmaker_name}' at event index {event_index} must use a list for "
            "'markets'."
        )

    if not markets_payload:
        return [
            NormalizedOddsMarket(
                bookmaker_name=bookmaker_name,
                market_name="h2h",
                outcomes=[],
                missing_data=[OUTCOME_MISSING_NOTE],
            )
        ]

    normalized_markets: list[NormalizedOddsMarket] = []
    for market_index, market in enumerate(markets_payload):
        normalized_markets.append(
            _build_normalized_market(
                market,
                bookmaker_name,
                event_index,
                market_index,
                home_team,
                away_team,
            )
        )
    return normalized_markets


def _build_normalized_market(
    market: dict,
    bookmaker_name: str,
    event_index: int,
    market_index: int,
    home_team: str,
    away_team: str,
) -> NormalizedOddsMarket:
    if not isinstance(market, dict):
        raise OddsApiCollectorError(
            "Market at event index "
            f"{event_index}, market index {market_index} must be a JSON object."
        )

    market_name = str(_read_required_value(market, "key", event_index))
    outcomes_payload = market.get("outcomes", [])
    if not isinstance(outcomes_payload, list):
        raise OddsApiCollectorError(
            f"Market '{market_name}' at event index {event_index} must use a list for 'outcomes'."
        )

    if not outcomes_payload:
        return NormalizedOddsMarket(
            bookmaker_name=bookmaker_name,
            market_name=market_name,
            outcomes=[],
            missing_data=[OUTCOME_MISSING_NOTE],
        )

    normalized_outcomes = [
        _build_outcome(outcome, event_index, home_team, away_team) for outcome in outcomes_payload
    ]
    return NormalizedOddsMarket(
        bookmaker_name=bookmaker_name,
        market_name=market_name,
        outcomes=normalized_outcomes,
        missing_data=[],
    )


def _build_outcome(
    outcome: dict,
    event_index: int,
    home_team: str,
    away_team: str,
) -> NormalizedOddsOutcome:
    if not isinstance(outcome, dict):
        raise OddsApiCollectorError(f"Outcome at event index {event_index} must be a JSON object.")

    selection = str(_read_required_value(outcome, "name", event_index))
    price = outcome.get("price")
    missing_data: list[str] = []

    if selection not in {home_team, away_team, "Draw"}:
        missing_data.append("Outcome name is outside the known home/away/draw set.")

    if price is None:
        missing_data.append(OUTCOME_MISSING_NOTE)
        return NormalizedOddsOutcome(
            selection=selection,
            decimal_odds=None,
            implied_probability=None,
            missing_data=missing_data,
        )

    decimal_odds = float(price)
    implied_probability = decimal_odds_to_implied_probability(decimal_odds)
    return NormalizedOddsOutcome(
        selection=selection,
        decimal_odds=decimal_odds,
        implied_probability=implied_probability,
        missing_data=missing_data,
    )


def _read_required_value(mapping: dict, key: str, index: int) -> str | int | float:
    value = mapping.get(key)
    if value is None or str(value).strip() == "":
        raise OddsApiCollectorError(f"Event at index {index} is missing required field '{key}'.")
    return value
