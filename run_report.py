from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

from src.analysis.analysis_validator import validate_analysis_output
from src.analysis.fallback_analyst import analyze_report_with_fallback
from src.analysis.gpt_analyst import GPTAnalyst, GPTAnalystError
from src.mock_data import get_mock_report, get_mock_report_input
from src.reports.html_renderer import render_report_html
from src.reports.report_builder import build_report_payload


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
    parser.add_argument(
        "--analysis",
        choices=["none", "fallback", "gpt"],
        default="none",
        help=(
            "Choose whether to render the original mock report, fallback analysis, or GPT analysis."
        ),
    )
    return parser


def get_output_path(region: str) -> Path:
    output_directory = Path("out")
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory / f"report_{region}.html"


def generate_mock_report(
    region: str, analysis_mode: str = "none", gpt_client: Any | None = None
) -> Path:
    report = _build_report_for_cli(region, analysis_mode, gpt_client)
    html = render_report_html(report)
    output_path = get_output_path(region)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _build_report_for_cli(region: str, analysis_mode: str, gpt_client: Any | None = None):
    if analysis_mode == "fallback":
        report_input = get_mock_report_input(region)
        analysis_output = analyze_report_with_fallback(report_input)
        validated_analysis = validate_analysis_output(report_input, analysis_output)
        return build_report_payload(report_input, validated_analysis)

    if analysis_mode == "gpt":
        report_input = get_mock_report_input(region)
        analyst = GPTAnalyst(gpt_client or _UnavailableGPTClient())
        analysis_output = analyst.analyze(
            report_input,
            use_fallback_on_error=gpt_client is None,
        )
        return build_report_payload(report_input, analysis_output)

    return get_mock_report(region)


def main(argv: Sequence[str] | None = None, gpt_client: Any | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.mode != "mock":
        parser.error("Only --mode mock is supported in Phase 1-B.")

    output_path = generate_mock_report(args.region, args.analysis, gpt_client)
    print(f"Mock report created successfully: {output_path.resolve()}")
    return 0


class _UnavailableGPTClient:
    def create_analysis(self, *, prompt, report_input):
        raise GPTAnalystError(
            "No GPT client was provided for CLI gpt mode. Falling back to deterministic analysis."
        )


if __name__ == "__main__":
    raise SystemExit(main())
