from __future__ import annotations

from typing import TypeAlias

from src.contracts.analysis_output import AnalysisOutput, GameAnalysis, ReportSummary
from src.contracts.report_input import (
    ConfidenceLevel,
    DiscrepancyLevel,
    GameInput,
    ReportInput,
    TrustLevel,
    clean_text_list,
)

Label: TypeAlias = str

LABEL_STRONG = "강력 추천 경기"
LABEL_HIGH_TRUST = "고신뢰 분석 경기"
LABEL_MARKET_GAP = "시장 괴리 높은 경기"
LABEL_DATA_GAP = "데이터 부족 경기"

UNAVAILABLE_MARKET_DISCREPANCY = "market_discrepancy_level unavailable"


def analyze_report_with_fallback(report_input: ReportInput | dict) -> AnalysisOutput:
    report = (
        report_input
        if isinstance(report_input, ReportInput)
        else ReportInput.model_validate(report_input)
    )
    game_analyses = [_analyze_game(game) for game in report.games]
    summary = _build_report_summary(report, game_analyses)

    return AnalysisOutput(
        report_id=report.report_id,
        region=report.region,
        generated_at=report.generated_at,
        summary=summary,
        games=game_analyses,
    )


def _analyze_game(game: GameInput) -> GameAnalysis:
    missing_data = _collect_missing_data(game)
    trust_level = game.data_quality.trust_level
    discrepancy_level, market_note, discrepancy_missing = _determine_market_discrepancy(game)
    missing_data.extend(discrepancy_missing)
    missing_data = _deduplicate_strings(missing_data)

    confidence_level = _determine_confidence_level(game, trust_level, missing_data)
    label = _determine_label(game, confidence_level, discrepancy_level, missing_data)
    analysis_summary = _build_analysis_summary(label, discrepancy_missing)
    supporting_points = _build_supporting_points(game, discrepancy_level)
    caution_notes = _build_caution_notes(game, discrepancy_missing)

    return GameAnalysis(
        game_id=game.game_id,
        label=label,
        confidence_level=confidence_level,
        trust_level=trust_level,
        discrepancy_level=discrepancy_level,
        analysis_summary=analysis_summary,
        supporting_points=supporting_points,
        caution_notes=caution_notes,
        market_note=market_note,
        missing_data=missing_data,
    )


def _collect_missing_data(game: GameInput) -> list[str]:
    combined = (
        game.missing_data
        + game.market_probability.missing_data
        + game.reference_probability.missing_data
        + game.data_quality.missing_data
    )
    return _deduplicate_strings(combined)


def _determine_market_discrepancy(
    game: GameInput,
) -> tuple[DiscrepancyLevel, str | None, list[str]]:
    market_probability = game.market_probability.implied_probability
    reference_probability = game.reference_probability.win_probability

    if market_probability is None:
        return "low", None, [UNAVAILABLE_MARKET_DISCREPANCY]

    if reference_probability is None:
        return "low", None, [UNAVAILABLE_MARKET_DISCREPANCY]

    probability_gap = abs(market_probability - reference_probability)

    if probability_gap >= 0.12:
        discrepancy_level: DiscrepancyLevel = "high"
    elif probability_gap >= 0.06:
        discrepancy_level = "medium"
    else:
        discrepancy_level = "low"

    market_note = (
        "Fallback comparison used the provided market and reference probabilities "
        f"with a gap of {probability_gap:.2f}."
    )
    return discrepancy_level, market_note, []


def _determine_confidence_level(
    game: GameInput, trust_level: TrustLevel, missing_data: list[str]
) -> ConfidenceLevel:
    incomplete_status_count = sum(
        status != "available"
        for status in (
            game.data_quality.odds_status,
            game.data_quality.lineup_status,
            game.data_quality.injury_status,
            game.data_quality.weather_status,
        )
    )

    if trust_level == "low" or incomplete_status_count >= 2 or missing_data:
        return "low"

    if trust_level == "high" and incomplete_status_count == 0:
        return "high"

    return "medium"


def _determine_label(
    game: GameInput,
    confidence_level: ConfidenceLevel,
    discrepancy_level: DiscrepancyLevel,
    missing_data: list[str],
) -> Label:
    if missing_data or game.data_quality.odds_status != "available":
        return LABEL_DATA_GAP

    if discrepancy_level == "high":
        return LABEL_MARKET_GAP

    market_probability = game.market_probability.implied_probability
    reference_probability = game.reference_probability.win_probability
    aligned_probabilities = (
        market_probability is not None
        and reference_probability is not None
        and abs(market_probability - reference_probability) <= 0.05
    )
    strong_probability_signal = any(
        probability is not None and probability >= 0.6
        for probability in (market_probability, reference_probability)
    )

    if confidence_level == "high" and aligned_probabilities and strong_probability_signal:
        return LABEL_STRONG

    return LABEL_HIGH_TRUST


def _build_analysis_summary(label: Label, discrepancy_missing: list[str]) -> str:
    if discrepancy_missing:
        return (
            "This fallback analysis stays cautious because market discrepancy "
            "could not be measured "
            "from the available inputs."
        )

    if label == LABEL_MARKET_GAP:
        return (
            "This fallback analysis highlights a noticeable gap between the provided market and "
            "reference probabilities."
        )

    if label == LABEL_STRONG:
        return (
            "This fallback analysis found aligned structured inputs "
            "and a stable enough probability "
            "signal for a featured game note."
        )

    if label == LABEL_HIGH_TRUST:
        return (
            "This fallback analysis found the available structured inputs consistent enough for a "
            "high-trust game summary."
        )

    return (
        "This fallback analysis keeps the game in a data-shortage bucket because some structured "
        "inputs are incomplete."
    )


def _build_supporting_points(game: GameInput, discrepancy_level: DiscrepancyLevel) -> list[str]:
    points = [
        (
            "Fallback analysis used the provided league and matchup fields for "
            f"{game.away_team} at {game.home_team}."
        ),
        f"Current data trust level is {game.data_quality.trust_level}.",
    ]

    if game.market_probability.implied_probability is not None:
        points.append("A market probability value was available in the normalized input.")

    if game.reference_probability.win_probability is not None:
        points.append("A reference probability value was available in the normalized input.")

    if (
        game.market_probability.implied_probability is not None
        and game.reference_probability.win_probability is not None
    ):
        points.append(f"Calculated market discrepancy level is {discrepancy_level}.")

    return _deduplicate_strings(points)


def _build_caution_notes(game: GameInput, discrepancy_missing: list[str]) -> list[str]:
    notes = list(game.data_quality.notes)

    if discrepancy_missing:
        notes.append(
            "Market discrepancy could not be measured because a required probability is missing."
        )

    if game.data_quality.lineup_status != "available":
        notes.append(
            "Lineup input is incomplete, so the fallback review does not infer player availability."
        )

    if game.data_quality.injury_status != "available":
        notes.append(
            "Injury input is incomplete, so the fallback review does not infer injury news."
        )

    if game.data_quality.weather_status != "available":
        notes.append(
            "Weather input is incomplete, so the fallback review does not infer weather impact."
        )

    return _deduplicate_strings(notes)


def _build_report_summary(report: ReportInput, game_analyses: list[GameAnalysis]) -> ReportSummary:
    label_counts = {
        LABEL_STRONG: 0,
        LABEL_HIGH_TRUST: 0,
        LABEL_MARKET_GAP: 0,
        LABEL_DATA_GAP: 0,
    }
    for analysis in game_analyses:
        label_counts[analysis.label] += 1

    summary_missing_data = _deduplicate_strings(
        report.missing_data + [item for analysis in game_analyses for item in analysis.missing_data]
    )

    confidence_level = _aggregate_confidence_level(game_analyses)
    trust_level = _aggregate_trust_level(game_analyses)
    discrepancy_level = _aggregate_discrepancy_level(game_analyses)

    key_points = [
        f"Fallback analyst processed {len(game_analyses)} games for the {report.region} report.",
        f"{label_counts[LABEL_DATA_GAP]} games were marked as data-shortage cases.",
    ]
    if label_counts[LABEL_MARKET_GAP]:
        key_points.append(
            f"{label_counts[LABEL_MARKET_GAP]} games showed a high market-versus-reference gap."
        )
    if UNAVAILABLE_MARKET_DISCREPANCY in summary_missing_data:
        key_points.append(
            "Some games could not compute market discrepancy because "
            "a required probability was missing."
        )

    return ReportSummary(
        headline=f"Fallback analysis summary for {report.report_name}",
        overview=(
            "This fallback summary is deterministic and uses only the normalized report input. "
            "It does not infer injuries, lineups, weather, news, or new probabilities."
        ),
        confidence_level=confidence_level,
        trust_level=trust_level,
        discrepancy_level=discrepancy_level,
        key_points=_deduplicate_strings(key_points),
        missing_data=summary_missing_data,
    )


def _aggregate_confidence_level(game_analyses: list[GameAnalysis]) -> ConfidenceLevel:
    levels = [analysis.confidence_level for analysis in game_analyses]
    if "low" in levels:
        return "low"
    if all(level == "high" for level in levels):
        return "high"
    return "medium"


def _aggregate_trust_level(game_analyses: list[GameAnalysis]) -> TrustLevel:
    levels = [analysis.trust_level for analysis in game_analyses]
    if "low" in levels:
        return "low"
    if all(level == "high" for level in levels):
        return "high"
    return "medium"


def _aggregate_discrepancy_level(game_analyses: list[GameAnalysis]) -> DiscrepancyLevel:
    missing_market_discrepancy = any(
        UNAVAILABLE_MARKET_DISCREPANCY in analysis.missing_data for analysis in game_analyses
    )
    levels = [analysis.discrepancy_level for analysis in game_analyses]

    if not missing_market_discrepancy:
        if "high" in levels:
            return "high"
        if "medium" in levels:
            return "medium"

    return "low"


def _deduplicate_strings(values: list[str]) -> list[str]:
    cleaned = clean_text_list(values)
    return list(dict.fromkeys(cleaned))
