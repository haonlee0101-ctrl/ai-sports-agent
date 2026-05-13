from __future__ import annotations

from dataclasses import dataclass

from src.contracts.analysis_output import AnalysisOutput, GameAnalysis
from src.contracts.report_input import FORBIDDEN_EXPRESSIONS, GameInput, ReportInput

UNAVAILABLE_MARKET_DISCREPANCY = "market_discrepancy_level unavailable"


@dataclass(frozen=True)
class AnalysisValidationResult:
    is_valid: bool
    errors: list[str]


class AnalysisValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        message = "AnalysisOutput validation failed:\n- " + "\n- ".join(errors)
        super().__init__(message)


def validate_analysis_output(
    report_input: ReportInput | dict, analysis_output: AnalysisOutput | dict
) -> AnalysisOutput:
    report = (
        report_input
        if isinstance(report_input, ReportInput)
        else ReportInput.model_validate(report_input)
    )
    analysis = (
        analysis_output
        if isinstance(analysis_output, AnalysisOutput)
        else AnalysisOutput.model_validate(analysis_output)
    )

    errors = collect_analysis_validation_errors(report, analysis)
    if errors:
        raise AnalysisValidationError(errors)
    return analysis


def collect_analysis_validation_errors(
    report_input: ReportInput | dict, analysis_output: AnalysisOutput | dict
) -> list[str]:
    report = (
        report_input
        if isinstance(report_input, ReportInput)
        else ReportInput.model_validate(report_input)
    )
    analysis = (
        analysis_output
        if isinstance(analysis_output, AnalysisOutput)
        else AnalysisOutput.model_validate(analysis_output)
    )

    input_games = {game.game_id: game for game in report.games}
    analysis_games = {game.game_id: game for game in analysis.games}
    errors: list[str] = []

    input_game_ids = set(input_games)
    analysis_game_ids = set(analysis_games)

    missing_game_ids = sorted(input_game_ids - analysis_game_ids)
    if missing_game_ids:
        errors.append(
            "Missing analysis entries for input game_id values: " + ", ".join(missing_game_ids)
        )

    extra_game_ids = sorted(analysis_game_ids - input_game_ids)
    if extra_game_ids:
        errors.append(
            "AnalysisOutput contains unknown game_id values: " + ", ".join(extra_game_ids)
        )

    errors.extend(_find_forbidden_expression_errors(analysis))

    for game_analysis in analysis.games:
        input_game = input_games.get(game_analysis.game_id)
        if input_game is None:
            continue

        errors.extend(_validate_game_analysis_against_input(input_game, game_analysis))

    return errors


def get_analysis_validation_result(
    report_input: ReportInput | dict, analysis_output: AnalysisOutput | dict
) -> AnalysisValidationResult:
    errors = collect_analysis_validation_errors(report_input, analysis_output)
    return AnalysisValidationResult(is_valid=not errors, errors=errors)


def _validate_game_analysis_against_input(
    input_game: GameInput, game_analysis: GameAnalysis
) -> list[str]:
    errors: list[str] = []

    if _core_data_is_missing(input_game) and not game_analysis.missing_data:
        errors.append(
            f"Game {input_game.game_id} must include missing_data because "
            "core input data is incomplete."
        )

    if input_game.market_probability.implied_probability is None:
        if UNAVAILABLE_MARKET_DISCREPANCY not in game_analysis.missing_data:
            errors.append(
                f"Game {input_game.game_id} must include "
                f"'{UNAVAILABLE_MARKET_DISCREPANCY}' in missing_data "
                "when market probability is unavailable."
            )
        if game_analysis.discrepancy_level != "low":
            errors.append(
                f"Game {input_game.game_id} must not use a measured discrepancy level when market "
                "probability is unavailable."
            )
        if game_analysis.market_note is not None:
            errors.append(
                f"Game {input_game.game_id} must not include market_note "
                "when market probability is unavailable."
            )

    return errors


def _core_data_is_missing(input_game: GameInput) -> bool:
    if input_game.missing_data:
        return True
    if input_game.market_probability.implied_probability is None:
        return True
    if input_game.reference_probability.win_probability is None:
        return True
    if input_game.market_probability.missing_data:
        return True
    if input_game.reference_probability.missing_data:
        return True
    if input_game.data_quality.missing_data:
        return True
    return any(
        status != "available"
        for status in (
            input_game.data_quality.odds_status,
            input_game.data_quality.lineup_status,
            input_game.data_quality.injury_status,
            input_game.data_quality.weather_status,
        )
    )


def _find_forbidden_expression_errors(analysis_output: AnalysisOutput) -> list[str]:
    errors: list[str] = []
    for path, value in _walk_strings(analysis_output.model_dump()):
        for expression in FORBIDDEN_EXPRESSIONS:
            if expression in value:
                errors.append(f"Forbidden expression '{expression}' found at {path}.")
    return errors


def _walk_strings(value: object, path: str = "analysis_output") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]

    if isinstance(value, list):
        strings: list[tuple[str, str]] = []
        for index, item in enumerate(value):
            strings.extend(_walk_strings(item, f"{path}[{index}]"))
        return strings

    if isinstance(value, dict):
        strings: list[tuple[str, str]] = []
        for key, item in value.items():
            strings.extend(_walk_strings(item, f"{path}.{key}"))
        return strings

    return []
