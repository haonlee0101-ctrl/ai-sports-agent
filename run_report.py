from __future__ import annotations

import argparse
from pathlib import Path

from src.mock_data import get_mock_report
from src.reports.html_renderer import render_report_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a mock sports analysis report as an HTML file."
    )
    parser.add_argument(
        "--region",
        choices=["east", "west"],
        required=True,
        help="Choose which mock regional report to generate.",
    )
    parser.add_argument(
        "--mode",
        choices=["mock"],
        required=True,
        help="Only mock mode is supported in Phase 1-B.",
    )
    return parser


def get_output_path(region: str) -> Path:
    output_directory = Path("out")
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory / f"report_{region}.html"


def generate_mock_report(region: str) -> Path:
    report = get_mock_report(region)
    html = render_report_html(report)
    output_path = get_output_path(region)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.mode != "mock":
        parser.error("Only --mode mock is supported in Phase 1-B.")

    output_path = generate_mock_report(args.region)
    print(f"Mock report created successfully: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
