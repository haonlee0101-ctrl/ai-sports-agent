from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_LABELS = [
    "강력 추천 경기",
    "고신뢰 분석 경기",
    "시장 괴리 높은 경기",
    "데이터 부족 경기",
]

FORBIDDEN_EXPRESSIONS = [
    "무조건",
    "필승",
    "확실",
    "100% 보장",
    "돈 걸어도 됨",
    "적중 확정",
]


def load_mock_report_tools():
    run_report = importlib.import_module("run_report")
    mock_data = importlib.import_module("src.mock_data")
    renderer = importlib.import_module("src.reports.html_renderer")
    return run_report.generate_mock_report, mock_data.get_mock_report, renderer.render_report_html


@pytest.mark.parametrize("region", ["east", "west"])
def test_mock_report_data_renders_to_html(region: str) -> None:
    _, get_mock_report, render_report_html = load_mock_report_tools()
    report = get_mock_report(region)
    html = render_report_html(report)

    assert "<!DOCTYPE html>" in html
    assert report.title in html

    for label in REQUIRED_LABELS:
        assert label in html

    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in html


@pytest.mark.parametrize(
    ("region", "expected_name"),
    [("east", "report_east.html"), ("west", "report_west.html")],
)
def test_generate_mock_report_writes_expected_html_file(
    tmp_path, monkeypatch: pytest.MonkeyPatch, region: str, expected_name: str
) -> None:
    generate_mock_report, _, _ = load_mock_report_tools()
    monkeypatch.chdir(tmp_path)

    output_path = generate_mock_report(region)

    assert output_path.name == expected_name
    assert output_path.exists()

    html = output_path.read_text(encoding="utf-8")
    assert "<html" in html
    assert "missing" in html

    for label in REQUIRED_LABELS:
        assert label in html

    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in html
