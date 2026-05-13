from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_plain_text_tools():
    mock_data_module = importlib.import_module("src.mock_data")
    renderer_module = importlib.import_module("src.reports.html_renderer")
    plain_text_module = importlib.import_module("src.reports.plain_text_renderer")
    return (
        mock_data_module.get_mock_report,
        renderer_module.render_report_html,
        plain_text_module.render_plain_text_report,
    )


def test_plain_text_renderer_produces_readable_text_from_report_payload() -> None:
    get_mock_report, _, render_plain_text_report = load_plain_text_tools()
    report = get_mock_report("east")

    text = render_plain_text_report(report)

    assert "AI Sports Analyst Agent - East Mock Report" in text
    assert "강력 추천 경기" in text
    assert "Seoul Mock Club" in text
    assert "Market Note:" in text


def test_plain_text_renderer_produces_readable_text_from_report_html() -> None:
    get_mock_report, render_report_html, render_plain_text_report = load_plain_text_tools()
    report = get_mock_report("west")
    html = render_report_html(report)

    text = render_plain_text_report(html)

    assert "<html" not in text
    assert "AI Sports Analyst Agent - West Mock Report" in text
    assert "데이터 부족 경기" in text
    assert "Madrid Training XI" in text
