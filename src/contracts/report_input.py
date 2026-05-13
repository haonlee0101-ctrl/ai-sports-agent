from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Region = Literal["east", "west"]
ReportMode = Literal["mock", "live"]
ConfidenceLevel = Literal["high", "medium", "low"]
TrustLevel = Literal["high", "medium", "low"]
DiscrepancyLevel = Literal["high", "medium", "low"]
AvailabilityStatus = Literal["available", "partial", "missing"]

FORBIDDEN_EXPRESSIONS = (
    "무조건",
    "필승",
    "확실",
    "100% 보장",
    "돈 걸어도 됨",
    "적중 확정",
)


def ensure_safe_text(value: str) -> str:
    for expression in FORBIDDEN_EXPRESSIONS:
        if expression in value:
            raise ValueError(f"Forbidden expression is not allowed: {expression}")
    return value


def clean_required_text(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("This field cannot be blank.")
    return ensure_safe_text(cleaned)


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return ensure_safe_text(cleaned)


def clean_text_list(values: list[str]) -> list[str]:
    cleaned_values: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        cleaned_values.append(ensure_safe_text(cleaned))
    return cleaned_values


class MarketProbability(BaseModel):
    """Normalized market probability input for one game."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(..., description="Where this market probability came from.")
    market_name: str = Field(..., description="Market name such as moneyline or match result.")
    selection: str = Field(..., description="Which side the probability describes.")
    implied_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Probability value between 0 and 1. Use None when missing.",
    )
    confidence_level: ConfidenceLevel = Field(
        ..., description="How stable this market probability appears."
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Explicit list of market inputs that are missing.",
    )

    @field_validator("source_name", "market_name", "selection")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return clean_required_text(value)

    @field_validator("missing_data")
    @classmethod
    def validate_missing_data(cls, values: list[str]) -> list[str]:
        return clean_text_list(values)

    @model_validator(mode="after")
    def require_explicit_missing_data(self) -> MarketProbability:
        if self.implied_probability is None and not self.missing_data:
            raise ValueError("missing_data must explain why implied_probability is unavailable.")
        return self


class ReferenceProbability(BaseModel):
    """Reference probability from a baseline or model source."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(..., description="Where the reference probability came from.")
    selection: str = Field(..., description="Which side the reference probability describes.")
    win_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Reference win probability between 0 and 1. Use None when missing.",
    )
    trust_level: TrustLevel = Field(..., description="How much the input should be trusted.")
    missing_data: list[str] = Field(
        default_factory=list,
        description="Explicit list of reference inputs that are missing.",
    )

    @field_validator("source_name", "selection")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return clean_required_text(value)

    @field_validator("missing_data")
    @classmethod
    def validate_missing_data(cls, values: list[str]) -> list[str]:
        return clean_text_list(values)

    @model_validator(mode="after")
    def require_explicit_missing_data(self) -> ReferenceProbability:
        if self.win_probability is None and not self.missing_data:
            raise ValueError("missing_data must explain why win_probability is unavailable.")
        return self


class DataQuality(BaseModel):
    """Data availability and trust notes for one game input."""

    model_config = ConfigDict(extra="forbid")

    trust_level: TrustLevel = Field(..., description="Trust level for the collected input set.")
    odds_status: AvailabilityStatus = Field(..., description="Whether odds data is available.")
    lineup_status: AvailabilityStatus = Field(..., description="Whether lineup data is available.")
    injury_status: AvailabilityStatus = Field(..., description="Whether injury data is available.")
    weather_status: AvailabilityStatus = Field(
        ..., description="Whether weather input is available."
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Explicit list of missing or partial inputs.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Short quality notes that are safe to show or inspect.",
    )

    @field_validator("missing_data", "notes")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        return clean_text_list(values)

    @model_validator(mode="after")
    def require_explicit_missing_data(self) -> DataQuality:
        statuses = (
            self.odds_status,
            self.lineup_status,
            self.injury_status,
            self.weather_status,
        )
        has_incomplete_data = any(status != "available" for status in statuses)
        if has_incomplete_data and not self.missing_data:
            raise ValueError("missing_data must list which inputs are unavailable or partial.")
        return self


class GameInput(BaseModel):
    """Normalized input contract for one game before GPT analysis."""

    model_config = ConfigDict(extra="forbid")

    game_id: str = Field(..., description="Unique identifier for the game.")
    league: str = Field(..., description="League or competition name.")
    match_time_local: str = Field(..., description="Local game start time as text.")
    home_team: str = Field(..., description="Home team display name.")
    away_team: str = Field(..., description="Away team display name.")
    market_probability: MarketProbability = Field(..., description="Market probability input.")
    reference_probability: ReferenceProbability = Field(
        ..., description="Reference probability input."
    )
    data_quality: DataQuality = Field(..., description="Availability and trust metadata.")
    input_notes: list[str] = Field(
        default_factory=list,
        description="Safe notes derived from mock or collected input data.",
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Explicit list of game-level missing inputs.",
    )

    @field_validator("game_id", "league", "match_time_local", "home_team", "away_team")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return clean_required_text(value)

    @field_validator("input_notes", "missing_data")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        return clean_text_list(values)


class ReportInput(BaseModel):
    """Top-level report input contract used before analysis generation."""

    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., description="Unique identifier for the report.")
    region: Region = Field(..., description="Target report region.")
    mode: ReportMode = Field(..., description="Execution mode for the report input.")
    generated_at: str = Field(..., description="When the input was generated.")
    report_name: str = Field(..., description="Human-readable name for the report run.")
    report_context: str = Field(..., description="Short overview of the input context.")
    source_notes: list[str] = Field(
        default_factory=list,
        description="Safe notes about how the input was gathered.",
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Explicit list of report-level missing inputs.",
    )
    games: list[GameInput] = Field(..., min_length=1, description="Game inputs for this report.")

    @field_validator("report_id", "generated_at", "report_name", "report_context")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return clean_required_text(value)

    @field_validator("source_notes", "missing_data")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        return clean_text_list(values)

    @field_validator("games")
    @classmethod
    def validate_unique_game_ids(cls, games: list[GameInput]) -> list[GameInput]:
        game_ids = [game.game_id for game in games]
        if len(game_ids) != len(set(game_ids)):
            raise ValueError("Each game_id must be unique inside ReportInput.")
        return games
