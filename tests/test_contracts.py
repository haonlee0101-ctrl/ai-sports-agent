from __future__ import annotations

import importlib
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_contract_models():
    analysis_output_module = importlib.import_module("src.contracts.analysis_output")
    report_input_module = importlib.import_module("src.contracts.report_input")
    return analysis_output_module.AnalysisOutput, report_input_module.ReportInput


def sample_report_input_payload() -> dict:
    return {
        "report_id": "report-input-east-001",
        "region": "east",
        "mode": "mock",
        "generated_at": "2026-05-13 21:30 KST",
        "report_name": "East Mock Input Contract",
        "report_context": "Mock contract sample for Phase 2 validation.",
        "source_notes": [
            "Mock data only.",
            "No live API calls are used.",
        ],
        "missing_data": [
            "league-wide injury feed missing",
        ],
        "games": [
            {
                "game_id": "east-contract-001",
                "league": "KBO",
                "match_time_local": "2026-05-14 18:30 KST",
                "home_team": "Seoul Mock Club",
                "away_team": "Busan Mock Club",
                "market_probability": {
                    "source_name": "Mock Odds Board",
                    "market_name": "moneyline",
                    "selection": "Seoul Mock Club",
                    "implied_probability": 0.57,
                    "confidence_level": "medium",
                    "missing_data": [],
                },
                "reference_probability": {
                    "source_name": "Mock Reference Model",
                    "selection": "Seoul Mock Club",
                    "win_probability": None,
                    "trust_level": "low",
                    "missing_data": [
                        "reference probability missing",
                    ],
                },
                "data_quality": {
                    "trust_level": "medium",
                    "odds_status": "available",
                    "lineup_status": "missing",
                    "injury_status": "missing",
                    "weather_status": "partial",
                    "missing_data": [
                        "starting lineup missing",
                        "injury feed missing",
                        "full weather note missing",
                    ],
                    "notes": [
                        "Mock mode only.",
                    ],
                },
                "input_notes": [
                    "This game is safe for contract validation only.",
                ],
                "missing_data": [
                    "reference probability missing",
                ],
            },
            {
                "game_id": "east-contract-002",
                "league": "NPB",
                "match_time_local": "2026-05-14 18:00 JST",
                "home_team": "Tokyo Sample Nine",
                "away_team": "Osaka Sample Nine",
                "market_probability": {
                    "source_name": "Mock Odds Board",
                    "market_name": "moneyline",
                    "selection": "Tokyo Sample Nine",
                    "implied_probability": 0.52,
                    "confidence_level": "high",
                    "missing_data": [],
                },
                "reference_probability": {
                    "source_name": "Mock Reference Model",
                    "selection": "Tokyo Sample Nine",
                    "win_probability": 0.55,
                    "trust_level": "medium",
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
                    "Balanced mock example.",
                ],
                "missing_data": [],
            },
        ],
    }


def sample_analysis_output_payload() -> dict:
    return {
        "report_id": "analysis-east-001",
        "region": "east",
        "generated_at": "2026-05-13 21:35 KST",
        "summary": {
            "headline": "East mock analysis summary",
            "overview": "Structured mock analysis output for Phase 2 validation.",
            "confidence_level": "medium",
            "trust_level": "medium",
            "discrepancy_level": "low",
            "key_points": [
                "Mock structure is complete enough for contract testing.",
                "Missing data is called out directly when needed.",
            ],
            "missing_data": [
                "some live feeds are still missing",
            ],
        },
        "games": [
            {
                "game_id": "east-contract-001",
                "label": "강력 추천 경기",
                "confidence_level": "medium",
                "trust_level": "medium",
                "discrepancy_level": "low",
                "analysis_summary": (
                    "The mock input is stable enough for a featured sample analysis."
                ),
                "supporting_points": [
                    "Core team and timing fields are present.",
                    "Market and reference notes are easy to compare.",
                ],
                "caution_notes": [
                    "Reference probability is missing and called out explicitly.",
                ],
                "market_note": "Mock market context is present without live feed claims.",
                "missing_data": [
                    "reference probability missing",
                ],
            },
            {
                "game_id": "east-contract-002",
                "label": "데이터 부족 경기",
                "confidence_level": "low",
                "trust_level": "medium",
                "discrepancy_level": "medium",
                "analysis_summary": "This sample stays cautious when comparison depth is limited.",
                "supporting_points": [
                    "Structured fields validate cleanly.",
                ],
                "caution_notes": [
                    "Use mock mode as a layout and contract example only.",
                ],
                "market_note": None,
                "missing_data": [
                    "market note missing",
                ],
            },
        ],
    }


def test_report_input_accepts_valid_sample() -> None:
    _, ReportInput = load_contract_models()
    report_input = ReportInput.model_validate(sample_report_input_payload())

    assert report_input.region == "east"
    assert len(report_input.games) == 2
    assert report_input.games[0].reference_probability.win_probability is None
    assert "reference probability missing" in report_input.games[0].missing_data


def test_analysis_output_accepts_valid_sample() -> None:
    AnalysisOutput, _ = load_contract_models()
    analysis_output = AnalysisOutput.model_validate(sample_analysis_output_payload())

    assert analysis_output.region == "east"
    assert len(analysis_output.games) == 2
    assert analysis_output.games[0].label == "강력 추천 경기"
    assert analysis_output.games[1].market_note is None


@pytest.mark.parametrize("invalid_label", ["임의 라벨", "확실 추천"])
def test_invalid_label_fails_validation(invalid_label: str) -> None:
    AnalysisOutput, _ = load_contract_models()
    payload = sample_analysis_output_payload()
    payload["games"][0]["label"] = invalid_label

    with pytest.raises(ValidationError):
        AnalysisOutput.model_validate(payload)


def test_duplicate_game_ids_fail_for_report_input() -> None:
    _, ReportInput = load_contract_models()
    payload = sample_report_input_payload()
    payload["games"][1]["game_id"] = payload["games"][0]["game_id"]

    with pytest.raises(ValidationError):
        ReportInput.model_validate(payload)


def test_duplicate_game_ids_fail_for_analysis_output() -> None:
    AnalysisOutput, _ = load_contract_models()
    payload = sample_analysis_output_payload()
    payload["games"][1]["game_id"] = payload["games"][0]["game_id"]

    with pytest.raises(ValidationError):
        AnalysisOutput.model_validate(payload)


def test_sample_payload_builders_are_independent() -> None:
    original = sample_report_input_payload()
    cloned = deepcopy(original)

    cloned["games"][0]["game_id"] = "changed-game-id"

    assert original["games"][0]["game_id"] == "east-contract-001"
