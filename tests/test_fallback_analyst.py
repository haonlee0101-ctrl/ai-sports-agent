from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

FORBIDDEN_EXPRESSIONS = [
    "무조건",
    "필승",
    "확실",
    "100% 보장",
    "돈 걸어도 됨",
    "적중 확정",
]

UNAVAILABLE_MARKET_DISCREPANCY = "market_discrepancy_level unavailable"


def load_fallback_tools():
    analyst_module = importlib.import_module("src.analysis.fallback_analyst")
    analysis_output_module = importlib.import_module("src.contracts.analysis_output")
    report_input_module = importlib.import_module("src.contracts.report_input")
    return (
        analyst_module.analyze_report_with_fallback,
        analysis_output_module.AnalysisOutput,
        report_input_module.ReportInput,
    )


def sample_report_input_payload() -> dict:
    return {
        "report_id": "fallback-east-001",
        "region": "east",
        "mode": "mock",
        "generated_at": "2026-05-13 22:10 KST",
        "report_name": "East fallback analysis sample",
        "report_context": "Deterministic fallback analyst validation sample.",
        "source_notes": [
            "Mock contract input only.",
        ],
        "missing_data": [
            "league-wide injury feed missing",
        ],
        "games": [
            {
                "game_id": "fallback-game-001",
                "league": "KBO",
                "match_time_local": "2026-05-14 18:30 KST",
                "home_team": "Seoul Mock Club",
                "away_team": "Busan Mock Club",
                "market_probability": {
                    "source_name": "Mock Odds Board",
                    "market_name": "moneyline",
                    "selection": "Seoul Mock Club",
                    "implied_probability": None,
                    "confidence_level": "low",
                    "missing_data": [
                        "market probability missing",
                    ],
                },
                "reference_probability": {
                    "source_name": "Mock Reference Model",
                    "selection": "Seoul Mock Club",
                    "win_probability": 0.58,
                    "trust_level": "medium",
                    "missing_data": [],
                },
                "data_quality": {
                    "trust_level": "medium",
                    "odds_status": "missing",
                    "lineup_status": "missing",
                    "injury_status": "missing",
                    "weather_status": "partial",
                    "missing_data": [
                        "odds feed missing",
                        "starting lineup missing",
                        "injury feed missing",
                        "full weather note missing",
                    ],
                    "notes": [
                        "Mock mode only.",
                    ],
                },
                "input_notes": [
                    "Use this game to validate missing market handling.",
                ],
                "missing_data": [
                    "market probability missing",
                ],
            },
            {
                "game_id": "fallback-game-002",
                "league": "NPB",
                "match_time_local": "2026-05-14 18:00 JST",
                "home_team": "Tokyo Sample Nine",
                "away_team": "Osaka Sample Nine",
                "market_probability": {
                    "source_name": "Mock Odds Board",
                    "market_name": "moneyline",
                    "selection": "Tokyo Sample Nine",
                    "implied_probability": 0.63,
                    "confidence_level": "high",
                    "missing_data": [],
                },
                "reference_probability": {
                    "source_name": "Mock Reference Model",
                    "selection": "Tokyo Sample Nine",
                    "win_probability": 0.61,
                    "trust_level": "high",
                    "missing_data": [],
                },
                "data_quality": {
                    "trust_level": "high",
                    "odds_status": "available",
                    "lineup_status": "available",
                    "injury_status": "available",
                    "weather_status": "available",
                    "missing_data": [],
                    "notes": [
                        "All core mock fields are present.",
                    ],
                },
                "input_notes": [
                    "Use this game to validate a fully available structured case.",
                ],
                "missing_data": [],
            },
        ],
    }


def collect_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(collect_strings(item))
        return strings
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(collect_strings(item))
        return strings
    return []


def test_fallback_analyst_returns_valid_analysis_output() -> None:
    analyze_report_with_fallback, AnalysisOutput, ReportInput = load_fallback_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())

    result = analyze_report_with_fallback(report_input)

    assert isinstance(result, AnalysisOutput)
    assert result.report_id == report_input.report_id
    assert len(result.games) == len(report_input.games)


def test_output_game_ids_match_input_game_ids() -> None:
    analyze_report_with_fallback, _, ReportInput = load_fallback_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())

    result = analyze_report_with_fallback(report_input)

    input_ids = [game.game_id for game in report_input.games]
    output_ids = [game.game_id for game in result.games]
    assert output_ids == input_ids


def test_missing_odds_marks_market_discrepancy_unavailable() -> None:
    analyze_report_with_fallback, _, ReportInput = load_fallback_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())

    result = analyze_report_with_fallback(report_input)
    first_game = result.games[0]

    assert UNAVAILABLE_MARKET_DISCREPANCY in first_game.missing_data
    assert first_game.market_note is None
    assert first_game.discrepancy_level == "low"


def test_missing_data_appears_in_output_missing_data() -> None:
    analyze_report_with_fallback, _, ReportInput = load_fallback_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())

    result = analyze_report_with_fallback(report_input)
    first_game = result.games[0]

    assert "market probability missing" in first_game.missing_data
    assert "starting lineup missing" in first_game.missing_data
    assert UNAVAILABLE_MARKET_DISCREPANCY in result.summary.missing_data


def test_forbidden_expressions_are_not_present() -> None:
    analyze_report_with_fallback, _, ReportInput = load_fallback_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())

    result = analyze_report_with_fallback(report_input)
    strings = collect_strings(result.model_dump())

    for expression in FORBIDDEN_EXPRESSIONS:
        assert all(expression not in text for text in strings)
