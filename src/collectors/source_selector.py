from __future__ import annotations

from pathlib import Path
from typing import Literal

from src.collectors.api_clients import (
    ApiSportsClient,
    LiveApiConfigurationError,
    OddsApiClient,
)
from src.collectors.api_sports import (
    ApiSportsCollectorError,
    load_report_input_from_api_sports_fixture,
)
from src.collectors.local_json_adapter import LocalJsonAdapterError, load_report_input_from_json
from src.collectors.report_input_builder import (
    ReportInputBuilderError,
    build_report_input_from_fixture_sources,
)
from src.collectors.report_input_loader import (
    ReportInputLoaderError,
    load_report_input_from_clients,
)
from src.contracts.report_input import ReportInput
from src.mock_data import get_mock_report_input

SafeSource = Literal["mock", "input_file", "fixture", "api_client_fake", "live"]


class SourceSelectorError(ValueError):
    """Raised when a requested source cannot be loaded safely."""


def load_report_input_for_source(
    *,
    source: SafeSource | str,
    region: str,
    input_file: str | Path | None = None,
    fixtures_file: str | Path | None = None,
    odds_file: str | Path | None = None,
    api_sports_client: ApiSportsClient | None = None,
    odds_api_client: OddsApiClient | None = None,
    allow_live: bool = False,
) -> ReportInput:
    """Select one safe ReportInput source without creating live clients by default."""

    try:
        if source == "mock":
            report_input = get_mock_report_input(region)
            _ensure_region_match(region, report_input)
            return report_input

        if source == "input_file":
            if input_file is None:
                raise SourceSelectorError("input_file is required when source='input_file'.")
            report_input = load_report_input_from_json(Path(input_file))
            _ensure_region_match(region, report_input)
            return report_input

        if source == "fixture":
            if fixtures_file is None:
                raise SourceSelectorError("fixtures_file is required when source='fixture'.")
            if odds_file is None:
                report_input = load_report_input_from_api_sports_fixture(Path(fixtures_file))
            else:
                report_input = build_report_input_from_fixture_sources(
                    Path(fixtures_file),
                    Path(odds_file),
                )
            _ensure_region_match(region, report_input)
            return report_input

        if source == "api_client_fake":
            if api_sports_client is None:
                raise SourceSelectorError(
                    "api_sports_client is required when source='api_client_fake'."
                )
            return load_report_input_from_clients(
                region=region,
                api_sports_client=api_sports_client,
                odds_api_client=odds_api_client,
                use_live=False,
            )

        if source == "live":
            if not allow_live:
                raise SourceSelectorError(
                    "source='live' is disabled by default. Pass allow_live=True to enable it."
                )
            if api_sports_client is None:
                raise SourceSelectorError("api_sports_client is required when source='live'.")
            return load_report_input_from_clients(
                region=region,
                api_sports_client=api_sports_client,
                odds_api_client=odds_api_client,
                use_live=True,
            )

        raise SourceSelectorError(
            "Unsupported source. Use one of: mock, input_file, fixture, api_client_fake, live."
        )
    except LiveApiConfigurationError:
        raise
    except SourceSelectorError:
        raise
    except (
        LocalJsonAdapterError,
        ApiSportsCollectorError,
        ReportInputBuilderError,
        ReportInputLoaderError,
        ValueError,
    ) as error:
        raise SourceSelectorError(
            f"Could not load ReportInput for source '{source}': {error}"
        ) from error


def _ensure_region_match(expected_region: str, report_input: ReportInput) -> None:
    if report_input.region != expected_region:
        raise SourceSelectorError(
            "Requested region does not match selected ReportInput source: "
            f"expected {expected_region}, got {report_input.region}."
        )
