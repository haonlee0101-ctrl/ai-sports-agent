from __future__ import annotations

from src.contracts.report_input import FORBIDDEN_EXPRESSIONS, ReportInput

ALLOWED_LABELS = (
    "강력 추천 경기",
    "고신뢰 분석 경기",
    "시장 괴리 높은 경기",
    "데이터 부족 경기",
)

ALLOWED_LEVELS = ("high", "medium", "low")

UNAVAILABLE_MARKET_DISCREPANCY = "market_discrepancy_level unavailable"


def build_analysis_prompt(report_input: ReportInput | dict) -> str:
    report = (
        report_input
        if isinstance(report_input, ReportInput)
        else ReportInput.model_validate(report_input)
    )
    game_ids = ", ".join(game.game_id for game in report.games)

    return f"""You are GPT Analyst for AI Sports Analyst Agent V7.2 Fast Track.

Task:
- Convert the provided ReportInput into AnalysisOutput-compatible structured data.

Safety rules:
- Do not invent injuries, lineups, player names, weather, news, or probabilities.
- Use only provided input data.
- Mark missing data explicitly.
- Return AnalysisOutput-compatible structured data.
- Do not create probabilities that are not already present in the input.
- Do not use forbidden expressions: {", ".join(FORBIDDEN_EXPRESSIONS)}.
- Output game_id values must match the provided input game_id values exactly.
- Allowed labels: {", ".join(ALLOWED_LABELS)}.
- Allowed confidence, trust, and discrepancy levels: {", ".join(ALLOWED_LEVELS)}.
- If market probability is unavailable in the input, include
  '{UNAVAILABLE_MARKET_DISCREPANCY}' in missing_data, keep market_note as null,
  and use discrepancy_level as low.

Provided report metadata:
- report_id: {report.report_id}
- region: {report.region}
- mode: {report.mode}
- generated_at: {report.generated_at}
- game_id values: {game_ids}

Return format:
- Return only AnalysisOutput-compatible structured data.
- Keep every game entry tied to the matching input game_id.
- Do not repair or replace missing facts with guesses.

ReportInput JSON:
{report.model_dump_json(indent=2)}
"""
