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

REQUIRED_LABELS = [
    "강력 추천 경기",
    "고신뢰 분석 경기",
    "시장 괴리 높은 경기",
    "데이터 부족 경기",
]

UNAVAILABLE_MARKET_DISCREPANCY = "market_discrepancy_level unavailable"


def load_report_builder_tools():
    validator_module = importlib.import_module("src.analysis.analysis_validator")
    renderer_module = importlib.import_module("src.reports.html_renderer")
    builder_module = importlib.import_module("src.reports.report_builder")
    report_input_module = importlib.import_module("src.contracts.report_input")
    analysis_output_module = importlib.import_module("src.contracts.analysis_output")
    schema_module = importlib.import_module("src.schemas")
    return (
        validator_module.AnalysisValidationError,
        renderer_module.render_report_html,
        builder_module.build_report_payload,
        report_input_module.ReportInput,
        analysis_output_module.AnalysisOutput,
        schema_module.ReportPayload,
    )


def sample_report_input_payload() -> dict:
    return {
        "report_id": "report-builder-east-001",
        "region": "east",
        "mode": "mock",
        "generated_at": "2026-05-13 23:20 KST",
        "report_name": "Phase 6 Report Builder Sample",
        "report_context": "Mock pipeline sample for report builder validation.",
        "source_notes": [
            "Mock contract input only.",
        ],
        "missing_data": [
            "league-wide injury feed missing",
        ],
        "games": [
            {
                "game_id": "builder-game-001",
                "league": "KBO",
                "match_time_local": "2026-05-14 18:30 KST",
                "home_team": "Seoul Mock Club",
                "away_team": "Busan Mock Club",
                "market_probability": {
                    "source_name": "Mock Odds Board",
                    "market_name": "moneyline",
                    "selection": "Seoul Mock Club",
                    "implied_probability": 0.64,
                    "confidence_level": "high",
                    "missing_data": [],
                },
                "reference_probability": {
                    "source_name": "Mock Reference Model",
                    "selection": "Seoul Mock Club",
                    "win_probability": 0.62,
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
                    "Structured sample for the strongest label path.",
                ],
                "missing_data": [],
            },
            {
                "game_id": "builder-game-002",
                "league": "NPB",
                "match_time_local": "2026-05-14 18:00 JST",
                "home_team": "Tokyo Sample Nine",
                "away_team": "Osaka Sample Nine",
                "market_probability": {
                    "source_name": "Mock Odds Board",
                    "market_name": "moneyline",
                    "selection": "Tokyo Sample Nine",
                    "implied_probability": 0.55,
                    "confidence_level": "medium",
                    "missing_data": [],
                },
                "reference_probability": {
                    "source_name": "Mock Reference Model",
                    "selection": "Tokyo Sample Nine",
                    "win_probability": 0.52,
                    "trust_level": "medium",
                    "missing_data": [],
                },
                "data_quality": {
                    "trust_level": "medium",
                    "odds_status": "available",
                    "lineup_status": "available",
                    "injury_status": "available",
                    "weather_status": "available",
                    "missing_data": [],
                    "notes": [
                        "The mock inputs are complete but not especially strong.",
                    ],
                },
                "input_notes": [
                    "Structured sample for a high-trust label path.",
                ],
                "missing_data": [],
            },
            {
                "game_id": "builder-game-003",
                "league": "K League",
                "match_time_local": "2026-05-14 19:30 KST",
                "home_team": "Incheon Demo FC",
                "away_team": "Daegu Demo FC",
                "market_probability": {
                    "source_name": "Mock Odds Board",
                    "market_name": "moneyline",
                    "selection": "Incheon Demo FC",
                    "implied_probability": 0.70,
                    "confidence_level": "high",
                    "missing_data": [],
                },
                "reference_probability": {
                    "source_name": "Mock Reference Model",
                    "selection": "Incheon Demo FC",
                    "win_probability": 0.52,
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
                        "The provided market and reference values are far apart.",
                    ],
                },
                "input_notes": [
                    "Structured sample for a market-gap label path.",
                ],
                "missing_data": [],
            },
            {
                "game_id": "builder-game-004",
                "league": "East Cup",
                "match_time_local": "2026-05-14 20:00 KST",
                "home_team": "Jeju Practice XI",
                "away_team": "Sapporo Practice XI",
                "market_probability": {
                    "source_name": "Mock Odds Board",
                    "market_name": "moneyline",
                    "selection": "Jeju Practice XI",
                    "implied_probability": None,
                    "confidence_level": "low",
                    "missing_data": [
                        "market probability missing",
                    ],
                },
                "reference_probability": {
                    "source_name": "Mock Reference Model",
                    "selection": "Jeju Practice XI",
                    "win_probability": 0.48,
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
                        "Use this game to keep missing data explicit.",
                    ],
                },
                "input_notes": [
                    "Structured sample for a data-shortage label path.",
                ],
                "missing_data": [
                    "market probability missing",
                ],
            },
        ],
    }


def sample_analysis_output_payload() -> dict:
    return {
        "report_id": "report-builder-east-001",
        "region": "east",
        "generated_at": "2026-05-13 23:21 KST",
        "summary": {
            "headline": "Phase 6 structured report summary",
            "overview": (
                "This structured report uses only provided input data "
                "and keeps missing data explicit."
            ),
            "confidence_level": "low",
            "trust_level": "medium",
            "discrepancy_level": "high",
            "key_points": [
                "Each required label appears at least once in this sample output.",
                "Missing market discrepancy is called out explicitly when needed.",
            ],
            "missing_data": [
                "league-wide injury feed missing",
                UNAVAILABLE_MARKET_DISCREPANCY,
            ],
        },
        "games": [
            {
                "game_id": "builder-game-001",
                "label": "강력 추천 경기",
                "confidence_level": "high",
                "trust_level": "high",
                "discrepancy_level": "low",
                "analysis_summary": (
                    "This sample uses only the available structured values and keeps the strongest "
                    "label tied to aligned inputs."
                ),
                "supporting_points": [
                    "The market and reference values are closely aligned.",
                    "All core input fields are available.",
                ],
                "caution_notes": [
                    "This remains a mock analysis example and not betting advice.",
                ],
                "market_note": "The provided market and reference values are closely aligned.",
                "missing_data": [],
            },
            {
                "game_id": "builder-game-002",
                "label": "고신뢰 분석 경기",
                "confidence_level": "medium",
                "trust_level": "medium",
                "discrepancy_level": "low",
                "analysis_summary": (
                    "This sample stays in a high-trust bucket because the provided fields are "
                    "consistent without a standout signal."
                ),
                "supporting_points": [
                    "The provided structured values are internally consistent.",
                ],
                "caution_notes": [
                    "Use only the visible mock fields when reading this summary.",
                ],
                "market_note": "The provided market and reference values are reasonably close.",
                "missing_data": [],
            },
            {
                "game_id": "builder-game-003",
                "label": "시장 괴리 높은 경기",
                "confidence_level": "high",
                "trust_level": "high",
                "discrepancy_level": "high",
                "analysis_summary": (
                    "This sample flags a large gap between the provided market "
                    "and reference values."
                ),
                "supporting_points": [
                    "The provided market value is much higher than the provided reference value.",
                ],
                "caution_notes": [
                    "Do not infer any missing news or roster details from this gap alone.",
                ],
                "market_note": "The provided market and reference values are far apart.",
                "missing_data": [],
            },
            {
                "game_id": "builder-game-004",
                "label": "데이터 부족 경기",
                "confidence_level": "low",
                "trust_level": "medium",
                "discrepancy_level": "low",
                "analysis_summary": (
                    "This sample stays cautious because market discrepancy cannot be measured from "
                    "the provided inputs."
                ),
                "supporting_points": [
                    "Only the provided structured input fields were used.",
                ],
                "caution_notes": [
                    "Do not infer lineup, injury, weather, or news details.",
                ],
                "market_note": None,
                "missing_data": [
                    "market probability missing",
                    "starting lineup missing",
                    "injury feed missing",
                    "full weather note missing",
                    UNAVAILABLE_MARKET_DISCREPANCY,
                ],
            },
        ],
    }


def test_report_builder_creates_renderable_report_payload_from_valid_analysis() -> None:
    _, render_report_html, build_report_payload, ReportInput, AnalysisOutput, ReportPayload = (
        load_report_builder_tools()
    )
    report_input = ReportInput.model_validate(sample_report_input_payload())
    analysis_output = AnalysisOutput.model_validate(sample_analysis_output_payload())

    report_payload = build_report_payload(report_input, analysis_output)
    html = render_report_html(report_payload)

    assert isinstance(report_payload, ReportPayload)
    assert report_payload.report_id == report_input.report_id
    assert len(report_payload.games) == len(report_input.games)
    assert "<!DOCTYPE html>" in html


def test_report_builder_uses_fallback_analyst_when_analysis_missing() -> None:
    _, render_report_html, build_report_payload, ReportInput, _, ReportPayload = (
        load_report_builder_tools()
    )
    report_input = ReportInput.model_validate(sample_report_input_payload())

    report_payload = build_report_payload(report_input)
    html = render_report_html(report_payload)

    assert isinstance(report_payload, ReportPayload)
    assert len(report_payload.games) == len(report_input.games)
    assert "<html" in html
    assert all(game.game_id for game in report_payload.games)


def test_invalid_analysis_output_fails_validation_before_rendering() -> None:
    AnalysisValidationError, _, build_report_payload, ReportInput, AnalysisOutput, _ = (
        load_report_builder_tools()
    )
    report_input = ReportInput.model_validate(sample_report_input_payload())
    analysis_output = AnalysisOutput.model_validate(sample_analysis_output_payload())

    invalid_output = analysis_output.model_copy(
        update={
            "games": [
                analysis_output.games[0].model_copy(update={"game_id": "unknown-game-id"}),
                *analysis_output.games[1:],
            ]
        }
    )

    try:
        build_report_payload(report_input, invalid_output)
    except AnalysisValidationError as error:
        assert "unknown game_id" in str(error)
    else:
        raise AssertionError("Invalid AnalysisOutput should fail validation before rendering.")


def test_rendered_html_contains_required_labels_and_no_forbidden_expressions() -> None:
    _, render_report_html, build_report_payload, ReportInput, AnalysisOutput, _ = (
        load_report_builder_tools()
    )
    report_input = ReportInput.model_validate(sample_report_input_payload())
    analysis_output = AnalysisOutput.model_validate(sample_analysis_output_payload())

    report_payload = build_report_payload(report_input, analysis_output)
    html = render_report_html(report_payload)

    for label in REQUIRED_LABELS:
        assert label in html

    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in html
