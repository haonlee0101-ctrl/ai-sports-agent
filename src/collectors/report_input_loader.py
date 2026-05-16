from __future__ import annotations

from typing import Any, Mapping

from src.collectors.api_clients import (
    ApiResponseFormatError,
    ApiSportsClient,
    LiveApiConfigurationError,
    OddsApiClient,
)
from src.collectors.api_sports import ApiSportsCollectorError, parse_api_sports_fixture_response
from src.collectors.odds_api import OddsApiCollectorError, parse_odds_api_events_response
from src.collectors.report_input_builder import (
    ReportInputBuilderError,
    build_report_input_from_parsed_sources,
)
from src.contracts.report_input import ReportInput


class ReportInputLoaderError(ValueError):
    """Raised when client-loaded responses cannot be converted into a ReportInput."""


def load_report_input_from_clients(
    *,
    region: str,
    api_sports_client: ApiSportsClient,
    odds_api_client: OddsApiClient | None = None,
    fixture_params: Mapping[str, Any] | None = None,
    odds_sport_key: str = "upcoming",
    odds_params: Mapping[str, Any] | None = None,
    use_live: bool = False,
) -> ReportInput:
    """Load one region-specific ReportInput from injected API client interfaces.

    This loader never creates network clients on its own. Callers must provide
    client instances explicitly, and live mode stays disabled unless the caller
    passes ``use_live=True``.
    """

    if api_sports_client is None:
        raise ReportInputLoaderError("api_sports_client is required.")

    try:
        fixture_payload = api_sports_client.fetch_fixtures(
            params=fixture_params,
            use_live=use_live,
        )
        fixture_report_input = parse_api_sports_fixture_response(fixture_payload)
        _ensure_region_match(region, fixture_report_input)

        if odds_api_client is None:
            return fixture_report_input

        odds_payload = odds_api_client.fetch_events(
            sport_key=odds_sport_key,
            params=odds_params,
            use_live=use_live,
        )
        odds_events = parse_odds_api_events_response(odds_payload)
        combined_report_input = build_report_input_from_parsed_sources(
            fixture_report_input,
            odds_events,
        )
        _ensure_region_match(region, combined_report_input)
        return combined_report_input
    except LiveApiConfigurationError:
        raise
    except ReportInputLoaderError:
        raise
    except (
        ApiResponseFormatError,
        ApiSportsCollectorError,
        OddsApiCollectorError,
        ReportInputBuilderError,
        ValueError,
    ) as error:
        raise ReportInputLoaderError(
            f"Could not load ReportInput from API clients: {error}"
        ) from error


def _ensure_region_match(expected_region: str, report_input: ReportInput) -> None:
    if report_input.region != expected_region:
        raise ReportInputLoaderError(
            "Requested region does not match client-loaded ReportInput: "
            f"expected {expected_region}, got {report_input.region}."
        )
