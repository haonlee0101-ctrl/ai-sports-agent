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


def load_run_report_tools():
    run_report_module = importlib.import_module("run_report")
    return run_report_module.main


def assert_html_has_expected_content(html: str) -> None:
    for label in REQUIRED_LABELS:
        assert label in html

    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in html


class RecordingFakeClient:
    def __init__(self):
        self.call_count = 0
        self.report_ids: list[str] = []
        self.prompt_snippets: list[str] = []

    def create_analysis(self, *, prompt, report_input):
        self.call_count += 1
        self.report_ids.append(report_input.report_id)
        self.prompt_snippets.append(prompt[:120])
        return build_fake_analysis_output_payload(report_input)


def build_fake_analysis_output_payload(report_input) -> dict:
    games = []
    labels = [
        "강력 추천 경기",
        "고신뢰 분석 경기",
        "시장 괴리 높은 경기",
        "데이터 부족 경기",
    ]

    for index, game in enumerate(report_input.games):
        if game.market_probability.implied_probability is None:
            games.append(
                {
                    "game_id": game.game_id,
                    "label": labels[index],
                    "confidence_level": "low",
                    "trust_level": game.data_quality.trust_level,
                    "discrepancy_level": "low",
                    "analysis_summary": (
                        "This structured GPT sample stays cautious because market discrepancy "
                        "cannot be measured from the provided inputs."
                    ),
                    "supporting_points": [
                        "Only provided input fields were used for this structured sample.",
                    ],
                    "caution_notes": [
                        "Missing data remains explicit and is not replaced with guesses.",
                    ],
                    "market_note": None,
                    "missing_data": list(
                        dict.fromkeys(
                            [
                                *game.missing_data,
                                *game.market_probability.missing_data,
                                *game.reference_probability.missing_data,
                                *game.data_quality.missing_data,
                                UNAVAILABLE_MARKET_DISCREPANCY,
                            ]
                        )
                    ),
                }
            )
            continue

        discrepancy_level = "high" if index == 2 else "low"
        market_note = (
            "The provided market and reference values are far apart."
            if discrepancy_level == "high"
            else "The provided market and reference values are closely aligned."
        )
        confidence_level = "high" if index == 0 else "medium"
        games.append(
            {
                "game_id": game.game_id,
                "label": labels[index],
                "confidence_level": confidence_level,
                "trust_level": game.data_quality.trust_level,
                "discrepancy_level": discrepancy_level,
                "analysis_summary": (
                    "This structured GPT sample uses only the provided input values "
                    "without adding new sports facts."
                ),
                "supporting_points": [
                    "Only provided input fields were used for this structured sample.",
                ],
                "caution_notes": [
                    "This remains a mock analysis example and not betting advice.",
                ],
                "market_note": market_note,
                "missing_data": [],
            }
        )

    return {
        "report_id": report_input.report_id,
        "region": report_input.region,
        "generated_at": report_input.generated_at,
        "summary": {
            "headline": f"GPT sample summary for {report_input.region}",
            "overview": (
                "This structured GPT sample uses only provided input data and keeps missing "
                "data explicit."
            ),
            "confidence_level": "low",
            "trust_level": "medium",
            "discrepancy_level": "high",
            "key_points": [
                "Each required label appears at least once in this fake GPT response.",
                "Missing market discrepancy is called out explicitly when needed.",
            ],
            "missing_data": [
                *report_input.missing_data,
                UNAVAILABLE_MARKET_DISCREPANCY,
            ],
        },
        "games": games,
    }


def test_existing_mock_command_still_works_for_east(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--region", "east", "--mode", "mock"])

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_existing_mock_command_still_works_for_west(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--region", "west", "--mode", "mock"])

    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_fallback_analysis_works_for_east(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--region", "east", "--mode", "mock", "--analysis", "fallback"])

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_fallback_analysis_works_for_west(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--region", "west", "--mode", "mock", "--analysis", "fallback"])

    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_gpt_analysis_works_with_fake_response(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    fake_client = RecordingFakeClient()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        ["--region", "east", "--mode", "mock", "--analysis", "gpt"],
        gpt_client=fake_client,
    )

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert fake_client.call_count == 1


def test_gpt_analysis_uses_fake_client_without_real_api(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    fake_client = RecordingFakeClient()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main(
        ["--region", "west", "--mode", "mock", "--analysis", "gpt"],
        gpt_client=fake_client,
    )

    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert fake_client.call_count == 1
    assert fake_client.report_ids == ["mock-west-2026-05-13"]
