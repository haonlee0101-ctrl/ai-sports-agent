from __future__ import annotations

from src.analysis.analysis_validator import validate_analysis_output
from src.analysis.fallback_analyst import analyze_report_with_fallback
from src.contracts.analysis_output import AnalysisOutput, GameAnalysis
from src.contracts.report_input import GameInput, ReportInput, clean_text_list
from src.schemas import GameReport, ReportPayload


def build_report_payload(
    report_input: ReportInput | dict, analysis_output: AnalysisOutput | dict | None = None
) -> ReportPayload:
    report = (
        report_input
        if isinstance(report_input, ReportInput)
        else ReportInput.model_validate(report_input)
    )

    analysis = _get_valid_analysis_output(report, analysis_output)
    _ensure_matching_report_metadata(report, analysis)

    analysis_games = {game.game_id: game for game in analysis.games}
    report_games = [_build_game_report(game, analysis_games[game.game_id]) for game in report.games]

    return ReportPayload(
        report_id=report.report_id,
        region=report.region,
        title=_build_report_title(report),
        generated_at=analysis.generated_at,
        mode="mock",
        overview=analysis.summary.overview,
        games=report_games,
    )


def _get_valid_analysis_output(
    report: ReportInput, analysis_output: AnalysisOutput | dict | None
) -> AnalysisOutput:
    if analysis_output is None:
        analysis = analyze_report_with_fallback(report)
    else:
        analysis = (
            analysis_output
            if isinstance(analysis_output, AnalysisOutput)
            else AnalysisOutput.model_validate(analysis_output)
        )

    return validate_analysis_output(report, analysis)


def _ensure_matching_report_metadata(report: ReportInput, analysis: AnalysisOutput) -> None:
    if analysis.report_id != report.report_id:
        raise ValueError("AnalysisOutput report_id must match ReportInput report_id.")
    if analysis.region != report.region:
        raise ValueError("AnalysisOutput region must match ReportInput region.")


def _build_report_title(report: ReportInput) -> str:
    return f"{report.report_name} - {report.region.upper()} Analysis Report"


def _build_game_report(game_input: GameInput, game_analysis: GameAnalysis) -> GameReport:
    return GameReport(
        game_id=game_input.game_id,
        league=game_input.league,
        match_time_local=game_input.match_time_local,
        home_team=game_input.home_team,
        away_team=game_input.away_team,
        label=game_analysis.label,
        analysis_summary=game_analysis.analysis_summary,
        watch_points=_merge_lists(game_analysis.supporting_points, game_input.input_notes),
        risk_factors=_merge_lists(game_analysis.caution_notes, game_input.data_quality.notes),
        market_note=game_analysis.market_note,
        missing_data=_merge_lists(
            game_analysis.missing_data,
            game_input.missing_data,
            game_input.market_probability.missing_data,
            game_input.reference_probability.missing_data,
            game_input.data_quality.missing_data,
        ),
    )


def _merge_lists(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        merged.extend(group)
    return list(dict.fromkeys(clean_text_list(merged)))
