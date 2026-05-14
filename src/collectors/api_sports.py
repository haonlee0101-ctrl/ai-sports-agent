from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import ValidationError

from src.contracts.report_input import ReportInput

DEFAULT_MODE = "mock"
DEFAULT_SOURCE_NOTE = "Parsed from a local API-Sports-like fixture sample only."
ODDS_MISSING_NOTE = "API-Sports fixture sample does not include odds data."
REFERENCE_MISSING_NOTE = "API-Sports fixture sample does not include reference probabilities."
LINEUP_MISSING_NOTE = "API-Sports fixture sample does not include lineup data."
INJURY_MISSING_NOTE = "API-Sports fixture sample does not include injury data."
WEATHER_MISSING_NOTE = "API-Sports fixture sample does not include weather data."


class ApiSportsCollectorError(ValueError):
    """Raised when an API-Sports-like local fixture cannot be parsed safely."""


def load_report_input_from_api_sports_fixture(path: str | Path) -> ReportInput:
    file_path = Path(path)
    payload = _read_fixture_payload(file_path)
    return parse_api_sports_fixture_response(payload)


def parse_api_sports_fixture_response(payload: dict) -> ReportInput:
    if not isinstance(payload, dict):
        raise ApiSportsCollectorError("API-Sports-like fixture payload must be a JSON object.")

    region = _read_required_text(payload, "region")
    generated_at = _read_required_text(payload, "generated_at")
    response_items = payload.get("response")

    if not isinstance(response_items, list) or not response_items:
        raise ApiSportsCollectorError(
            "API-Sports-like fixture payload must include a non-empty response list."
        )

    report_payload = {
        "report_id": payload.get("report_id") or _build_report_id(region, generated_at),
        "region": region,
        "mode": payload.get("mode", DEFAULT_MODE),
        "generated_at": generated_at,
        "report_name": payload.get("report_name") or f"API-Sports Fixture Sample Report ({region})",
        "report_context": payload.get("report_context")
        or "Structured fixture-only sample parsed from a local API-Sports-like response.",
        "source_notes": payload.get("source_notes", [DEFAULT_SOURCE_NOTE]),
        "missing_data": payload.get(
            "missing_data",
            [
                ODDS_MISSING_NOTE,
                LINEUP_MISSING_NOTE,
                INJURY_MISSING_NOTE,
                WEATHER_MISSING_NOTE,
            ],
        ),
        "games": [_build_game_input(item, index) for index, item in enumerate(response_items)],
    }

    try:
        return ReportInput.model_validate(report_payload)
    except ValidationError as error:
        raise ApiSportsCollectorError(
            f"API-Sports-like fixture payload failed ReportInput validation: {error}"
        ) from error


def _read_fixture_payload(file_path: Path) -> dict:
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ApiSportsCollectorError(
            f"Could not read API-Sports-like fixture file: {file_path}"
        ) from error

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ApiSportsCollectorError(
            f"Invalid JSON in API-Sports-like fixture file {file_path}: {error.msg}"
        ) from error

    if not isinstance(payload, dict):
        raise ApiSportsCollectorError(
            f"API-Sports-like fixture file must contain a JSON object: {file_path}"
        )

    return payload


def _build_game_input(item: dict, index: int) -> dict:
    if not isinstance(item, dict):
        raise ApiSportsCollectorError(f"Fixture item at index {index} must be a JSON object.")

    fixture = _read_required_object(item, "fixture", index)
    league = _read_required_object(item, "league", index)
    teams = _read_required_object(item, "teams", index)
    home_team_object = _read_required_object(teams, "home", index)
    away_team_object = _read_required_object(teams, "away", index)

    fixture_id = _read_required_value(fixture, "id", index)
    league_name = _read_required_value(league, "name", index)
    home_team = _read_required_value(home_team_object, "name", index)
    away_team = _read_required_value(away_team_object, "name", index)
    match_time_local = _read_required_value(fixture, "date", index)

    status_long = ""
    status = fixture.get("status")
    if isinstance(status, dict):
        status_long = str(status.get("long", "")).strip()

    notes = item.get("notes", [])
    if not isinstance(notes, list):
        raise ApiSportsCollectorError(f"Fixture item at index {index} must use a list for notes.")

    input_notes = [
        "Fixture metadata was parsed from a local API-Sports-like sample.",
        *[str(note) for note in notes],
    ]
    quality_notes = []
    if status_long:
        quality_notes.append(f"Fixture status from sample: {status_long}.")

    return {
        "game_id": f"api-sports-{fixture_id}",
        "league": str(league_name),
        "match_time_local": str(match_time_local),
        "home_team": str(home_team),
        "away_team": str(away_team),
        "market_probability": {
            "source_name": "API-Sports fixture sample",
            "market_name": "match result",
            "selection": str(home_team),
            "implied_probability": None,
            "confidence_level": "low",
            "missing_data": [ODDS_MISSING_NOTE],
        },
        "reference_probability": {
            "source_name": "API-Sports fixture sample",
            "selection": str(home_team),
            "win_probability": None,
            "trust_level": "low",
            "missing_data": [REFERENCE_MISSING_NOTE],
        },
        "data_quality": {
            "trust_level": "low",
            "odds_status": "missing",
            "lineup_status": "missing",
            "injury_status": "missing",
            "weather_status": "missing",
            "missing_data": [
                ODDS_MISSING_NOTE,
                LINEUP_MISSING_NOTE,
                INJURY_MISSING_NOTE,
                WEATHER_MISSING_NOTE,
            ],
            "notes": quality_notes,
        },
        "input_notes": input_notes,
        "missing_data": [
            ODDS_MISSING_NOTE,
            LINEUP_MISSING_NOTE,
            INJURY_MISSING_NOTE,
            WEATHER_MISSING_NOTE,
        ],
    }


def _read_required_object(mapping: dict, key: str, index: int) -> dict:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ApiSportsCollectorError(
            f"Fixture item at index {index} is missing required object '{key}'."
        )
    return value


def _read_required_value(mapping: dict, key: str, index: int) -> str | int:
    value = mapping.get(key)
    if value is None or str(value).strip() == "":
        raise ApiSportsCollectorError(
            f"Fixture item at index {index} is missing required field '{key}'."
        )
    return value


def _read_required_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if value is None or str(value).strip() == "":
        raise ApiSportsCollectorError(
            f"API-Sports-like fixture payload is missing required field '{key}'."
        )
    return str(value)


def _build_report_id(region: str, generated_at: str) -> str:
    normalized_timestamp = re.sub(r"[^0-9A-Za-z]+", "-", generated_at).strip("-").lower()
    return f"api-sports-{region}-{normalized_timestamp}"
