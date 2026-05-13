from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

UNAVAILABLE_MARKET_DISCREPANCY = "market_discrepancy_level unavailable"


def load_gpt_tools():
    gpt_analyst_module = importlib.import_module("src.analysis.gpt_analyst")
    prompt_builder_module = importlib.import_module("src.analysis.prompt_builder")
    analysis_output_module = importlib.import_module("src.contracts.analysis_output")
    report_input_module = importlib.import_module("src.contracts.report_input")
    return (
        gpt_analyst_module.GPTAnalyst,
        gpt_analyst_module.GPTAnalystError,
        prompt_builder_module.build_analysis_prompt,
        analysis_output_module.AnalysisOutput,
        report_input_module.ReportInput,
    )


def sample_report_input_payload() -> dict:
    return {
        "report_id": "gpt-east-001",
        "region": "east",
        "mode": "mock",
        "generated_at": "2026-05-13 22:50 KST",
        "report_name": "GPT analyst sample input",
        "report_context": "Sample input for prompt builder and GPT wrapper tests.",
        "source_notes": [
            "Mock contract input only.",
        ],
        "missing_data": [
            "league-wide injury feed missing",
        ],
        "games": [
            {
                "game_id": "gpt-game-001",
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
                "game_id": "gpt-game-002",
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


def sample_valid_analysis_output_payload() -> dict:
    return {
        "report_id": "gpt-east-001",
        "region": "east",
        "generated_at": "2026-05-13 22:50 KST",
        "summary": {
            "headline": "Structured GPT analyst summary",
            "overview": (
                "This fake response uses only the provided input data "
                "and marks missing data clearly."
            ),
            "confidence_level": "low",
            "trust_level": "medium",
            "discrepancy_level": "low",
            "key_points": [
                "The first game has missing market probability and is treated cautiously.",
                "The second game has enough provided structure for a higher-trust summary.",
            ],
            "missing_data": [
                "league-wide injury feed missing",
                UNAVAILABLE_MARKET_DISCREPANCY,
            ],
        },
        "games": [
            {
                "game_id": "gpt-game-001",
                "label": "데이터 부족 경기",
                "confidence_level": "low",
                "trust_level": "medium",
                "discrepancy_level": "low",
                "analysis_summary": (
                    "This structured response stays cautious because market discrepancy cannot be "
                    "measured from the provided inputs."
                ),
                "supporting_points": [
                    "Only provided league, matchup, and timing fields were used.",
                    "Market probability is missing in the normalized input.",
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
            {
                "game_id": "gpt-game-002",
                "label": "강력 추천 경기",
                "confidence_level": "high",
                "trust_level": "high",
                "discrepancy_level": "low",
                "analysis_summary": (
                    "This structured response uses the available market and reference values "
                    "without adding new facts."
                ),
                "supporting_points": [
                    "Both provided probability fields are available.",
                    "The provided inputs align closely enough for a featured sample note.",
                ],
                "caution_notes": [
                    "This remains a mock structured example and not betting advice.",
                ],
                "market_note": "The provided market and reference values are closely aligned.",
                "missing_data": [],
            },
        ],
    }


class RecordingFakeClient:
    def __init__(self, response):
        self.response = response
        self.call_count = 0
        self.prompts: list[str] = []
        self.report_ids: list[str] = []

    def create_analysis(self, *, prompt, report_input):
        self.call_count += 1
        self.prompts.append(prompt)
        self.report_ids.append(report_input.report_id)
        return self.response


def test_prompt_builder_includes_safety_instructions() -> None:
    _, _, build_analysis_prompt, _, ReportInput = load_gpt_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())

    prompt = build_analysis_prompt(report_input)

    assert (
        "Do not invent injuries, lineups, player names, weather, news, or probabilities." in prompt
    )
    assert "Use only provided input data." in prompt
    assert "Mark missing data explicitly." in prompt
    assert "Return AnalysisOutput-compatible structured data." in prompt


def test_prompt_builder_includes_provided_game_id_values() -> None:
    _, _, build_analysis_prompt, _, ReportInput = load_gpt_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())

    prompt = build_analysis_prompt(report_input)

    assert "gpt-game-001" in prompt
    assert "gpt-game-002" in prompt


def test_gpt_analyst_returns_valid_analysis_output_from_fake_response() -> None:
    GPTAnalyst, _, _, AnalysisOutput, ReportInput = load_gpt_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())
    fake_client = RecordingFakeClient(sample_valid_analysis_output_payload())

    analyst = GPTAnalyst(fake_client)
    result = analyst.analyze(report_input)

    assert isinstance(result, AnalysisOutput)
    assert result.report_id == report_input.report_id
    assert [game.game_id for game in result.games] == [game.game_id for game in report_input.games]


def test_invalid_fake_response_fails_clearly() -> None:
    GPTAnalyst, GPTAnalystError, _, _, ReportInput = load_gpt_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())
    invalid_response = json.dumps({"bad": "payload"})
    fake_client = RecordingFakeClient(invalid_response)

    analyst = GPTAnalyst(fake_client)

    try:
        analyst.analyze(report_input)
    except GPTAnalystError as error:
        assert "Invalid GPT analyst response" in str(error)
    else:
        raise AssertionError("Invalid fake response should raise GPTAnalystError.")


def test_no_real_api_calls_are_made_in_tests() -> None:
    GPTAnalyst, _, _, _, ReportInput = load_gpt_tools()
    report_input = ReportInput.model_validate(sample_report_input_payload())
    fake_client = RecordingFakeClient(sample_valid_analysis_output_payload())

    analyst = GPTAnalyst(fake_client)
    analyst.analyze(report_input)

    assert fake_client.call_count == 1
    assert fake_client.report_ids == [report_input.report_id]
    assert fake_client.prompts
