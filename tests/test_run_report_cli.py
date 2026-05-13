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


def load_run_report_tools():
    run_report_module = importlib.import_module("run_report")
    return run_report_module.main


def assert_html_has_expected_content(html: str) -> None:
    for label in REQUIRED_LABELS:
        assert label in html

    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in html


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
