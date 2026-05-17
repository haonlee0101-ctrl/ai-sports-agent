from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.collectors.api_clients import ApiSportsClient, LiveApiConfigurationError, OddsApiClient
from src.collectors.source_selector import SourceSelectorError, load_report_input_for_source
from src.config.sport_sources import (
    SportSource,
    get_report_slot_schedule,
    list_sources_by_report_slot,
)
from src.contracts.report_input import ReportInput


@dataclass(frozen=True, slots=True)
class ReportSourceConfig:
    """CLI-ready configuration for selecting one ReportInput source."""

    source: str
    region: str
    mode: str = "mock"
    input_file: str | Path | None = None
    fixtures_file: str | Path | None = None
    odds_file: str | Path | None = None
    allow_live: bool = False
    report_slot: str | None = None


@dataclass(frozen=True, slots=True)
class ReportSlotSourcePlan:
    """Resolved catalog plan for one report slot, without touching any API client."""

    report_slot: str
    delivery_time_kst: str
    enabled_league_keys: tuple[str, ...]
    sports_included: tuple[str, ...]
    primary_odds_sources: tuple[str, ...]
    secondary_schedule_source_candidates: tuple[str, ...]
    sources: tuple[SportSource, ...]


class SourceOrchestratorError(ValueError):
    """Raised when source orchestration cannot produce a safe ReportInput."""


def resolve_sources_for_report_slot(report_slot: str) -> list[SportSource]:
    """Return enabled catalog entries for one report slot without any network activity."""

    try:
        return list_sources_by_report_slot(report_slot)
    except ValueError as error:
        raise SourceOrchestratorError(str(error)) from error


def build_report_slot_plan(report_slot: str) -> ReportSlotSourcePlan:
    """Build a deterministic source plan for one report slot."""

    sources = resolve_sources_for_report_slot(report_slot)
    schedule = get_report_slot_schedule(report_slot)

    return ReportSlotSourcePlan(
        report_slot=schedule.report_slot,
        delivery_time_kst=schedule.delivery_time_kst,
        enabled_league_keys=tuple(source.league_key for source in sources),
        sports_included=tuple(sorted({source.sport for source in sources})),
        primary_odds_sources=tuple(sorted({source.primary_odds_source for source in sources})),
        secondary_schedule_source_candidates=tuple(
            sorted({source.secondary_schedule_source for source in sources})
        ),
        sources=tuple(sources),
    )


def build_report_slot_plan_from_config(config: ReportSourceConfig) -> ReportSlotSourcePlan:
    """Resolve a report slot plan from a config object without changing existing load paths."""

    if config is None:
        raise SourceOrchestratorError("config is required.")
    if not config.report_slot:
        raise SourceOrchestratorError("config.report_slot is required for report slot planning.")
    return build_report_slot_plan(config.report_slot)


def load_report_input_from_config(
    config: ReportSourceConfig,
    *,
    api_sports_client: ApiSportsClient | None = None,
    odds_api_client: OddsApiClient | None = None,
) -> ReportInput:
    """Load one ReportInput from a small config object without changing CLI behavior."""

    if config is None:
        raise SourceOrchestratorError("config is required.")

    try:
        return load_report_input_for_source(
            source=config.source,
            region=config.region,
            input_file=config.input_file,
            fixtures_file=config.fixtures_file,
            odds_file=config.odds_file,
            api_sports_client=api_sports_client,
            odds_api_client=odds_api_client,
            allow_live=config.allow_live,
        )
    except LiveApiConfigurationError:
        raise
    except SourceSelectorError as error:
        raise SourceOrchestratorError(
            f"Could not orchestrate ReportInput for source '{config.source}': {error}"
        ) from error


def load_report_inputs_from_config(
    config: ReportSourceConfig,
    *,
    api_sports_client: ApiSportsClient | None = None,
    odds_api_client: OddsApiClient | None = None,
) -> list[ReportInput]:
    """Return a single-item list so future CLI flows can stay list-friendly."""

    return [
        load_report_input_from_config(
            config,
            api_sports_client=api_sports_client,
            odds_api_client=odds_api_client,
        )
    ]
