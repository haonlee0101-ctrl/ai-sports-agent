from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.contracts.report_input import (
    ConfidenceLevel,
    DiscrepancyLevel,
    Region,
    TrustLevel,
    clean_optional_text,
    clean_required_text,
    clean_text_list,
)

AnalysisLabel = Literal[
    "강력 추천 경기",
    "고신뢰 분석 경기",
    "시장 괴리 높은 경기",
    "데이터 부족 경기",
]


class ReportSummary(BaseModel):
    """Top-level summary produced from a validated report input."""

    model_config = ConfigDict(extra="forbid")

    headline: str = Field(..., description="Short headline for the report.")
    overview: str = Field(..., description="Plain-language report summary.")
    confidence_level: ConfidenceLevel = Field(..., description="Confidence level for the summary.")
    trust_level: TrustLevel = Field(..., description="Trust level for the summary.")
    discrepancy_level: DiscrepancyLevel = Field(
        ..., description="How large the overall market disagreement appears."
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Key summary points for readers or downstream systems.",
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Explicit list of missing context at the report-summary level.",
    )

    @field_validator("headline", "overview")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return clean_required_text(value)

    @field_validator("key_points", "missing_data")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        return clean_text_list(values)


class GameAnalysis(BaseModel):
    """Structured GPT analysis output for one game."""

    model_config = ConfigDict(extra="forbid")

    game_id: str = Field(..., description="Unique identifier matching the input game.")
    label: AnalysisLabel = Field(..., description="Approved game label.")
    confidence_level: ConfidenceLevel = Field(
        ..., description="Confidence level for the game analysis."
    )
    trust_level: TrustLevel = Field(..., description="Trust level for the game analysis.")
    discrepancy_level: DiscrepancyLevel = Field(
        ..., description="Market discrepancy level for the game analysis."
    )
    analysis_summary: str = Field(..., description="Short plain-language analysis summary.")
    supporting_points: list[str] = Field(
        default_factory=list,
        description="Main reasons supporting the label or summary.",
    )
    caution_notes: list[str] = Field(
        default_factory=list,
        description="Warnings or uncertainty notes for this game.",
    )
    market_note: str | None = Field(
        default=None,
        description="Optional market note. Use None when not available.",
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Explicit list of missing context for this game analysis.",
    )

    @field_validator("game_id", "analysis_summary")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return clean_required_text(value)

    @field_validator("market_note")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        return clean_optional_text(value)

    @field_validator("supporting_points", "caution_notes", "missing_data")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        return clean_text_list(values)


class AnalysisOutput(BaseModel):
    """Top-level structured analysis result produced from ReportInput."""

    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., description="Unique identifier for the analyzed report.")
    region: Region = Field(..., description="Target report region.")
    generated_at: str = Field(..., description="When the structured analysis was produced.")
    summary: ReportSummary = Field(..., description="Top-level report summary.")
    games: list[GameAnalysis] = Field(..., min_length=1, description="Per-game analyses.")

    @field_validator("report_id", "generated_at")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return clean_required_text(value)

    @field_validator("games")
    @classmethod
    def validate_unique_game_ids(cls, games: list[GameAnalysis]) -> list[GameAnalysis]:
        game_ids = [game.game_id for game in games]
        if len(game_ids) != len(set(game_ids)):
            raise ValueError("Each game_id must be unique inside AnalysisOutput.")
        return games
