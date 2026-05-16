from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from src.analysis.analysis_validator import validate_analysis_output
from src.analysis.fallback_analyst import analyze_report_with_fallback
from src.analysis.gpt_analyst import GPTAnalyst, GPTAnalystError
from src.collectors.api_clients import LiveApiConfigurationError
from src.collectors.source_orchestrator import (
    ReportSourceConfig,
    SourceOrchestratorError,
    load_report_input_from_config,
)
from src.contracts.report_input import ReportInput
from src.evaluation.prediction_log import (
    DEFAULT_DB_PATH,
    PredictionLogError,
    init_db,
    save_prediction_log,
)
from src.messaging.sendgrid_mailer import SendGridMailer, SendGridMailerError
from src.mock_data import get_mock_report
from src.reports.html_renderer import render_report_html
from src.reports.plain_text_renderer import render_plain_text_report
from src.reports.report_builder import build_report_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a sports analysis report as an HTML file."
    )
    parser.add_argument(
        "--region",
        choices=["east", "west"],
        required=True,
        help="Choose which mock regional report to generate.",
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "fixture"],
        required=True,
        help="Choose mock mode or local fixture mode.",
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
        "--input-file",
        help="Optional local JSON file that will be loaded and validated as ReportInput.",
    )
    parser.add_argument(
        "--fixtures-file",
        help="Local API-Sports-like fixture JSON file used when --mode fixture is selected.",
    )
    parser.add_argument(
        "--odds-file",
        help="Optional local The Odds API-like JSON file used to enrich fixture mode input.",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the generated report email after writing the HTML file.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save per-game prediction rows to the local SQLite database.",
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Override the SQLite database path. Useful for tests and local debugging.",
    )
    return parser


def get_output_path(region: str) -> Path:
    output_directory = Path("out")
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory / f"report_{region}.html"


def generate_mock_report(
    region: str,
    analysis_mode: str = "none",
    gpt_client: Any | None = None,
    input_file: str | Path | None = None,
) -> Path:
    output_path, _, _, _, _ = generate_mock_report_artifacts(
        region,
        analysis_mode,
        gpt_client,
        input_file=input_file,
        mode="mock",
    )
    return output_path


def generate_mock_report_artifacts(
    region: str,
    analysis_mode: str = "none",
    gpt_client: Any | None = None,
    input_file: str | Path | None = None,
    mode: str = "mock",
    fixtures_file: str | Path | None = None,
    odds_file: str | Path | None = None,
):
    report, report_input, analysis_output = _build_report_for_cli(
        region,
        analysis_mode,
        gpt_client,
        mode=mode,
        input_file=input_file,
        fixtures_file=fixtures_file,
        odds_file=odds_file,
    )
    html = render_report_html(report)
    output_path = get_output_path(region)
    output_path.write_text(html, encoding="utf-8")
    return output_path, report, html, report_input, analysis_output


def _build_report_for_cli(
    region: str,
    analysis_mode: str,
    gpt_client: Any | None = None,
    mode: str = "mock",
    input_file: str | Path | None = None,
    fixtures_file: str | Path | None = None,
    odds_file: str | Path | None = None,
):
    if mode == "fixture":
        if fixtures_file is None:
            raise ReportInputSelectionError(
                "--fixtures-file is required when --mode fixture is used."
            )

    report_input = _load_report_input_for_cli(
        region=region,
        mode=mode,
        input_file=input_file,
        fixtures_file=fixtures_file,
        odds_file=odds_file,
    )

    if mode == "mock" and input_file is None and analysis_mode == "none":
        return get_mock_report(region), report_input, None

    return _build_structured_report_for_cli(report_input, analysis_mode, gpt_client)


def _build_structured_report_for_cli(
    report_input: ReportInput,
    analysis_mode: str,
    gpt_client: Any | None = None,
):
    if analysis_mode == "gpt":
        analyst = GPTAnalyst(gpt_client or _UnavailableGPTClient())
        analysis_output = analyst.analyze(
            report_input,
            use_fallback_on_error=gpt_client is None,
        )
    else:
        analysis_output = analyze_report_with_fallback(report_input)

    validated_analysis = validate_analysis_output(report_input, analysis_output)
    return build_report_payload(report_input, validated_analysis), report_input, validated_analysis


def main(
    argv: Sequence[str] | None = None,
    gpt_client: Any | None = None,
    mailer: Any | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        output_path, report, html, report_input, analysis_output = generate_mock_report_artifacts(
            args.region,
            args.analysis,
            gpt_client,
            mode=args.mode,
            input_file=args.input_file,
            fixtures_file=args.fixtures_file,
            odds_file=args.odds_file,
        )
    except ReportInputSelectionError as error:
        print(f"Report generation failed: {error}")
        return 1

    print(f"Mock report created successfully: {output_path.resolve()}")

    if args.save:
        try:
            saved_rows = _save_report_predictions(
                db_path=args.db_path,
                report=report,
                report_input=report_input,
                analysis_output=analysis_output,
                execution_mode=args.mode,
                analysis_mode=args.analysis,
            )
        except PredictionLogError as error:
            print(f"SQLite save failed: {error}")
            return 1
        print(f"Saved {saved_rows} prediction rows to {Path(args.db_path).resolve()}")

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


class ReportInputSelectionError(ValueError):
    """Raised when CLI input selection does not match the provided ReportInput."""


def _load_report_input_for_cli(
    *,
    region: str,
    mode: str,
    input_file: str | Path | None = None,
    fixtures_file: str | Path | None = None,
    odds_file: str | Path | None = None,
    source_override: str | None = None,
    allow_live: bool = False,
    api_sports_client: Any | None = None,
    odds_api_client: Any | None = None,
) -> ReportInput:
    config = _build_source_config_for_cli(
        region=region,
        mode=mode,
        input_file=input_file,
        fixtures_file=fixtures_file,
        odds_file=odds_file,
        source_override=source_override,
        allow_live=allow_live,
    )

    try:
        return load_report_input_from_config(
            config,
            api_sports_client=api_sports_client,
            odds_api_client=odds_api_client,
        )
    except (LiveApiConfigurationError, SourceOrchestratorError) as error:
        raise ReportInputSelectionError(str(error)) from error


def _build_source_config_for_cli(
    *,
    region: str,
    mode: str,
    input_file: str | Path | None = None,
    fixtures_file: str | Path | None = None,
    odds_file: str | Path | None = None,
    source_override: str | None = None,
    allow_live: bool = False,
) -> ReportSourceConfig:
    source = source_override or _determine_cli_source(mode=mode, input_file=input_file)
    return ReportSourceConfig(
        source=source,
        region=region,
        mode=mode,
        input_file=_resolve_cli_path(input_file) if input_file is not None else None,
        fixtures_file=_resolve_cli_path(fixtures_file) if fixtures_file is not None else None,
        odds_file=_resolve_cli_path(odds_file) if odds_file is not None else None,
        allow_live=allow_live,
    )


def _determine_cli_source(
    *,
    mode: str,
    input_file: str | Path | None = None,
) -> str:
    if mode == "fixture":
        return "fixture"
    if input_file is not None:
        return "input_file"
    return "mock"


def _resolve_cli_path(path_value: str | Path) -> Path:
    return Path(path_value).expanduser()


def _save_report_predictions(
    *,
    db_path: str | Path,
    report,
    report_input,
    analysis_output,
    execution_mode: str,
    analysis_mode: str,
) -> int:
    database_path = init_db(db_path)
    input_games = {game.game_id: game for game in report_input.games}
    analysis_games = (
        {game.game_id: game for game in analysis_output.games}
        if analysis_output is not None
        else {}
    )
    saved_rows = 0

    for report_game in report.games:
        input_game = input_games.get(report_game.game_id)
        analysis_game = analysis_games.get(report_game.game_id)
        inserted = save_prediction_log(
            database_path,
            report_time_kst=report_input.generated_at,
            region=report.region,
            mode=execution_mode,
            analysis_mode=analysis_mode,
            game_id=report_game.game_id,
            label=report_game.label,
            data_trust_level=(
                input_game.data_quality.trust_level if input_game is not None else None
            ),
            prediction_confidence_level=(
                analysis_game.confidence_level if analysis_game is not None else None
            ),
            market_discrepancy_level=(
                analysis_game.discrepancy_level if analysis_game is not None else None
            ),
            recommended_side=_get_recommended_side(),
            summary=(
                analysis_game.analysis_summary
                if analysis_game is not None
                else report_game.analysis_summary
            ),
            input_snapshot_json=_dump_snapshot_json(
                input_game.model_dump() if input_game is not None else report_game.model_dump()
            ),
            analysis_output_json=_dump_analysis_json(
                analysis_game.model_dump()
                if analysis_game is not None
                else report_game.model_dump()
            ),
        )
        saved_rows += int(inserted)

    return saved_rows


def _get_recommended_side() -> None:
    # The current contracts do not expose an explicit recommended side yet.
    return None


def _dump_snapshot_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _dump_analysis_json(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    raise SystemExit(main())
