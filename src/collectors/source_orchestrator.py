from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.collectors.api_clients import ApiSportsClient, LiveApiConfigurationError, OddsApiClient
from src.collectors.source_selector import SourceSelectorError, load_report_input_for_source
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


class SourceOrchestratorError(ValueError):
    """Raised when source orchestration cannot produce a safe ReportInput."""


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
