from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

from src.analysis.analysis_validator import validate_analysis_output
from src.analysis.fallback_analyst import analyze_report_with_fallback
from src.analysis.gpt_analyst import GPTAnalyst, GPTAnalystError
from src.messaging.sendgrid_mailer import SendGridMailer, SendGridMailerError
from src.mock_data import get_mock_report, get_mock_report_input
from src.reports.html_renderer import render_report_html
from src.reports.plain_text_renderer import render_plain_text_report
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
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the generated report email after writing the HTML file.",
    )
    return parser


def get_output_path(region: str) -> Path:
    output_directory = Path("out")
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory / f"report_{region}.html"


def generate_mock_report(
    region: str, analysis_mode: str = "none", gpt_client: Any | None = None
) -> Path:
    output_path, _, _ = generate_mock_report_artifacts(region, analysis_mode, gpt_client)
    return output_path


def generate_mock_report_artifacts(
    region: str, analysis_mode: str = "none", gpt_client: Any | None = None
):
    report = _build_report_for_cli(region, analysis_mode, gpt_client)
    html = render_report_html(report)
    output_path = get_output_path(region)
    output_path.write_text(html, encoding="utf-8")
    return output_path, report, html


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


def main(
    argv: Sequence[str] | None = None,
    gpt_client: Any | None = None,
    mailer: Any | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.mode != "mock":
        parser.error("Only --mode mock is supported in Phase 1-B.")

    output_path, report, html = generate_mock_report_artifacts(
        args.region,
        args.analysis,
        gpt_client,
    )
    print(f"Mock report created successfully: {output_path.resolve()}")

    if args.send:
        plain_text = render_plain_text_report(report)
        active_mailer = mailer or SendGridMailer()
        try:
            active_mailer.send_report(
                subject=report.title,
                html_content=html,
                plain_text_content=plain_text,
            )
        except SendGridMailerError as error:
            print(f"Email send failed: {error}")
            return 1
        print("Email sent successfully.")

    return 0


class _UnavailableGPTClient:
    def create_analysis(self, *, prompt, report_input):
        raise GPTAnalystError(
            "No GPT client was provided for CLI gpt mode. Falling back to deterministic analysis."
        )


if __name__ == "__main__":
    raise SystemExit(main())
