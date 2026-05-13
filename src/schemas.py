from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Region = Literal["east", "west"]
AnalysisLabel = Literal[
    "강력 추천 경기",
    "고신뢰 분석 경기",
    "시장 괴리 높은 경기",
    "데이터 부족 경기",
]

FORBIDDEN_EXPRESSIONS = (
    "무조건",
    "필승",
    "확실",
    "100% 보장",
    "돈 걸어도 됨",
    "적중 확정",
)

DEFAULT_DISCLAIMER = "This report is analysis content based on mock data. It is not betting advice."


def _ensure_safe_text(value: str) -> str:
    for expression in FORBIDDEN_EXPRESSIONS:
        if expression in value:
            raise ValueError(f"Forbidden expression is not allowed: {expression}")
    return value


class GameReport(BaseModel):
    """Beginner-friendly schema for one mock game analysis card."""

    model_config = ConfigDict(extra="forbid")

    game_id: str = Field(..., description="Unique identifier for the game.")
    league: str = Field(..., description="League or competition name.")
    match_time_local: str = Field(..., description="Human-readable local start time.")
    home_team: str = Field(..., description="Home team display name.")
    away_team: str = Field(..., description="Away team display name.")
    label: AnalysisLabel = Field(..., description="One of the approved report labels.")
    analysis_summary: str = Field(..., description="Short reader-friendly summary for the game.")
    watch_points: list[str] = Field(
        default_factory=list,
        description="Key points a reader should notice in the mock input.",
    )
    risk_factors: list[str] = Field(
        default_factory=list,
        description="Reasons to read the analysis carefully.",
    )
    market_note: str | None = Field(
        default=None,
        description="Optional market context. Use None when mock data is missing.",
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Data that is unavailable in mock mode.",
    )

    @field_validator(
        "game_id",
        "league",
        "match_time_local",
        "home_team",
        "away_team",
        "analysis_summary",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank.")
        return _ensure_safe_text(cleaned)

    @field_validator("market_note")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return _ensure_safe_text(cleaned)

    @field_validator("watch_points", "risk_factors", "missing_data")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        cleaned_values: list[str] = []
        for value in values:
            cleaned = value.strip()
            if not cleaned:
                continue
            cleaned_values.append(_ensure_safe_text(cleaned))
        return cleaned_values


class ReportPayload(BaseModel):
    """Beginner-friendly schema for a full mock report."""

    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., description="Unique report identifier.")
    region: Region = Field(..., description="Target region for the report.")
    title: str = Field(..., description="Report title shown to readers.")
    generated_at: str = Field(..., description="Report generation time in local text format.")
    mode: Literal["mock"] = Field(default="mock", description="Current report mode.")
    overview: str = Field(..., description="Short introduction for the report.")
    disclaimer: str = Field(
        default=DEFAULT_DISCLAIMER,
        description="Explain that the content is analysis, not betting advice.",
    )
    games: list[GameReport] = Field(..., min_length=1, description="Games included in the report.")

    @field_validator("report_id", "title", "generated_at", "overview", "disclaimer")
    @classmethod
    def validate_report_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank.")
        return _ensure_safe_text(cleaned)

    @field_validator("games")
    @classmethod
    def validate_unique_game_ids(cls, games: list[GameReport]) -> list[GameReport]:
        game_ids = [game.game_id for game in games]
        if len(game_ids) != len(set(game_ids)):
            raise ValueError("Each game_id must be unique inside a report.")
        return games
