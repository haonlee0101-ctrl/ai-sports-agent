from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

UNAVAILABLE_MARKET_DISCREPANCY = "market_discrepancy_level unavailable"


def load_validator_tools():
    fallback_module = importlib.import_module("src.analysis.fallback_analyst")
    validator_module = importlib.import_module("src.analysis.analysis_validator")
    report_input_module = importlib.import_module("src.contracts.report_input")
    return (
        fallback_module.analyze_report_with_fallback,
        validator_module.AnalysisValidationError,
        validator_module.validate_analysis_output,
        report_input_module.ReportInput,
    )


def sample_report_input_payload() -> dict:
    return {
        "report_id": "validator-east-001",
        "region": "east",
        "mode": "mock",
        "generated_at": "2026-05-13 22:30 KST",
        "report_name": "Validator sample input",
        "report_context": "Sample input for analysis validator tests.",
        "source_notes": [
            "Mock contract input only.",
        ],
        "missing_data": [
            "league-wide injury feed missing",
        ],
        "games": [
            {
                "game_id": "validator-game-001",
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
                "game_id": "validator-game-002",
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


def build_valid_report_and_analysis():
    analyze_report_with_fallback, _, _, ReportInput = load_validator_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())
    analysis_output = analyze_report_with_fallback(report_input)
    return report_input, analysis_output


def test_valid_fallback_analysis_passes_validation() -> None:
    report_input, analysis_output = build_valid_report_and_analysis()
    _, _, validate_analysis_output, _ = load_validator_tools()

    validated = validate_analysis_output(report_input, analysis_output)

    assert validated is analysis_output


def test_unknown_game_id_fails_validation() -> None:
    report_input, analysis_output = build_valid_report_and_analysis()
    _, AnalysisValidationError, validate_analysis_output, _ = load_validator_tools()

    invalid_output = analysis_output.model_copy(
        update={
            "games": [
                analysis_output.games[0].model_copy(update={"game_id": "unknown-game-id"}),
                *analysis_output.games[1:],
            ]
        }
    )

    try:
        validate_analysis_output(report_input, invalid_output)
    except AnalysisValidationError as error:
        assert "unknown game_id" in str(error)
    else:
        raise AssertionError("Validation should fail for an unknown game_id.")


def test_missing_analysis_entry_fails_validation() -> None:
    report_input, analysis_output = build_valid_report_and_analysis()
    _, AnalysisValidationError, validate_analysis_output, _ = load_validator_tools()

    invalid_output = analysis_output.model_copy(update={"games": analysis_output.games[:-1]})

    try:
        validate_analysis_output(report_input, invalid_output)
    except AnalysisValidationError as error:
        assert "Missing analysis entries" in str(error)
    else:
        raise AssertionError("Validation should fail when an input game has no analysis entry.")


def test_forbidden_expression_fails_validation() -> None:
    report_input, analysis_output = build_valid_report_and_analysis()
    _, AnalysisValidationError, validate_analysis_output, _ = load_validator_tools()

    invalid_output = analysis_output.model_copy(
        update={
            "games": [
                analysis_output.games[0].model_copy(
                    update={"analysis_summary": "무조건 좋은 경기"}
                ),
                *analysis_output.games[1:],
            ]
        }
    )

    try:
        validate_analysis_output(report_input, invalid_output)
    except AnalysisValidationError as error:
        assert "Forbidden expression" in str(error)
    else:
        raise AssertionError("Validation should fail when a forbidden expression is present.")


def test_unavailable_market_probability_with_high_discrepancy_fails_validation() -> None:
    report_input, analysis_output = build_valid_report_and_analysis()
    _, AnalysisValidationError, validate_analysis_output, _ = load_validator_tools()

    invalid_output = analysis_output.model_copy(
        update={
            "games": [
                analysis_output.games[0].model_copy(update={"discrepancy_level": "high"}),
                *analysis_output.games[1:],
            ]
        }
    )

    try:
        validate_analysis_output(report_input, invalid_output)
    except AnalysisValidationError as error:
        assert "must not use a measured discrepancy level" in str(error)
    else:
        raise AssertionError(
            "Validation should fail when missing market probability is paired "
            "with high discrepancy."
        )


def test_valid_unavailable_market_probability_with_unavailable_discrepancy_passes_validation() -> (
    None
):
    report_input, analysis_output = build_valid_report_and_analysis()
    _, _, validate_analysis_output, _ = load_validator_tools()

    first_game = analysis_output.games[0]
    assert UNAVAILABLE_MARKET_DISCREPANCY in first_game.missing_data
    assert first_game.discrepancy_level == "low"
    assert first_game.market_note is None

    validated = validate_analysis_output(report_input, analysis_output)

    assert validated.games[0].game_id == report_input.games[0].game_id
