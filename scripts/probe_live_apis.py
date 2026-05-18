from __future__ import annotations

import argparse
import getpass
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any, Callable, TextIO

from src.collectors.api_clients import (
    ApiRequestError,
    ApiResponseFormatError,
    ApiSportsClient,
    LiveApiConfigurationError,
    OddsApiClient,
    Transport,
    build_request_url,
    default_json_transport,
)
from src.collectors.live_odds_fetcher import fetch_live_odds_events_for_sport_keys
from src.collectors.multisport_odds_mapper import (
    MultiSportOddsMapperError,
    normalize_live_odds_events,
)
from src.collectors.report_input_loader import (
    ReportInputLoaderError,
    load_report_input_from_normalized_odds_events,
)
from src.config.sport_sources import get_source_by_league_key

API_SPORTS_BASE_URL = "https://v3.football.api-sports.io"
ODDS_API_BASE_URL = "https://api.the-odds-api.com"
SUPPORTED_PROVIDERS = ("api-sports", "odds", "both")
SUPPORTED_API_SPORTS_MODES = ("status", "fixtures")
SUPPORTED_ODDS_MODES = ("sports", "odds")


class LiveApiProbeError(ValueError):
    """Raised when a manual live API probe is not configured safely."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manually probe live sports APIs with an explicit safety confirmation."
    )
    parser.add_argument(
        "--provider",
        required=True,
        help="Choose one provider: api-sports, odds, or both.",
    )
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="Required before any live network call can happen.",
    )
    parser.add_argument(
        "--api-sports-mode",
        default="fixtures",
        help="API-Sports probe target: status or fixtures. Defaults to fixtures.",
    )
    parser.add_argument(
        "--api-sports-date",
        help="Optional fixture date filter in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--api-sports-next",
        type=int,
        default=1,
        help="Optional next-fixtures count for API-Sports fixture probing. Defaults to 1.",
    )
    parser.add_argument(
        "--odds-mode",
        default="odds",
        help="The Odds API probe target: sports or odds. Defaults to odds.",
    )
    parser.add_argument(
        "--odds-sport",
        action="append",
        help="The Odds API sport key for odds probing. Repeat this flag to probe multiple sports.",
    )
    parser.add_argument(
        "--odds-regions",
        default="us",
        help="The Odds API regions filter for odds probing. Defaults to us.",
    )
    parser.add_argument(
        "--odds-markets",
        default="h2h",
        help="The Odds API markets filter for odds probing. Defaults to h2h.",
    )
    parser.add_argument(
        "--odds-format",
        default="decimal",
        help="The Odds API odds format for odds probing. Defaults to decimal.",
    )
    parser.add_argument(
        "--odds-date-format",
        default="iso",
        help="The Odds API date format for odds probing. Defaults to iso.",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Normalize The Odds API odds response through the multisport odds mapper.",
    )
    parser.add_argument(
        "--report-input",
        action="store_true",
        help="Build a compact ReportInput summary from normalized live odds events.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    api_sports_transport: Transport | None = None,
    odds_transport: Transport | None = None,
    secret_prompt: Callable[[str], str] | None = None,
) -> int:
    stream = stdout or sys.stdout
    environment = env or os.environ
    parser = build_parser()
    args = parser.parse_args(argv)
    active_secret_prompt = secret_prompt
    if active_secret_prompt is None and sys.stdin.isatty():
        active_secret_prompt = getpass.getpass

    try:
        summaries = run_probe(
            provider=args.provider,
            confirm_live=args.confirm_live,
            api_sports_mode=args.api_sports_mode,
            api_sports_date=args.api_sports_date,
            api_sports_next=args.api_sports_next,
            odds_mode=args.odds_mode,
            odds_sports=args.odds_sport,
            odds_regions=args.odds_regions,
            odds_markets=args.odds_markets,
            odds_format=args.odds_format,
            odds_date_format=args.odds_date_format,
            normalize=args.normalize,
            report_input=args.report_input,
            env=environment,
            api_sports_transport=api_sports_transport,
            odds_transport=odds_transport,
            secret_prompt=active_secret_prompt,
        )
    except LiveApiProbeError as error:
        print(f"Live API probe failed: {error}", file=stream)
        return 1

    for index, summary in enumerate(summaries):
        if index:
            print("", file=stream)
        for line in format_summary(summary):
            print(line, file=stream)

    return 0


def run_probe(
    *,
    provider: str,
    confirm_live: bool,
    api_sports_mode: str = "fixtures",
    api_sports_date: str | None = None,
    api_sports_next: int | None = 1,
    odds_mode: str = "odds",
    odds_sports: Sequence[str] | None = None,
    odds_regions: str = "us",
    odds_markets: str = "h2h",
    odds_format: str = "decimal",
    odds_date_format: str = "iso",
    normalize: bool = False,
    report_input: bool = False,
    env: Mapping[str, str],
    api_sports_transport: Transport | None = None,
    odds_transport: Transport | None = None,
    secret_prompt: Callable[[str], str] | None = None,
) -> list[dict[str, Any]]:
    normalized_provider = validate_provider(provider)
    normalized_api_sports_mode = validate_mode(
        api_sports_mode,
        supported_modes=SUPPORTED_API_SPORTS_MODES,
        provider_name="api-sports",
    )
    normalized_odds_mode = validate_mode(
        odds_mode,
        supported_modes=SUPPORTED_ODDS_MODES,
        provider_name="odds",
    )
    validated_api_sports_next = validate_next_count(api_sports_next)
    normalized_odds_sports = normalize_odds_sports(odds_sports)

    if not confirm_live:
        raise LiveApiProbeError("Refusing live API probe without --confirm-live.")

    requested_providers = (
        ("api-sports", "odds") if normalized_provider == "both" else (normalized_provider,)
    )
    summaries: list[dict[str, Any]] = []
    for item in requested_providers:
        summaries.append(
            probe_provider(
                provider=item,
                api_sports_mode=normalized_api_sports_mode,
                api_sports_date=api_sports_date,
                api_sports_next=validated_api_sports_next,
                odds_mode=normalized_odds_mode,
                odds_sports=normalized_odds_sports,
                odds_regions=odds_regions,
                odds_markets=odds_markets,
                odds_format=odds_format,
                odds_date_format=odds_date_format,
                normalize=normalize,
                report_input=report_input,
                env=env,
                api_sports_transport=api_sports_transport,
                odds_transport=odds_transport,
                secret_prompt=secret_prompt,
            )
        )
    return summaries


def validate_provider(provider: str) -> str:
    normalized_provider = provider.strip().lower()
    if normalized_provider not in SUPPORTED_PROVIDERS:
        raise LiveApiProbeError("Unsupported provider. Use one of: api-sports, odds, both.")
    return normalized_provider


def validate_mode(
    mode: str,
    *,
    supported_modes: tuple[str, ...],
    provider_name: str,
) -> str:
    normalized_mode = mode.strip().lower()
    if normalized_mode not in supported_modes:
        supported_modes_text = ", ".join(supported_modes)
        raise LiveApiProbeError(
            f"Unsupported {provider_name} mode. Use one of: {supported_modes_text}."
        )
    return normalized_mode


def validate_next_count(next_count: int | None) -> int | None:
    if next_count is None:
        return None
    if next_count < 1:
        raise LiveApiProbeError("--api-sports-next must be 1 or greater.")
    return next_count


def normalize_odds_sports(odds_sports: Sequence[str] | None) -> list[str]:
    if not odds_sports:
        return ["upcoming"]
    normalized_sports = [value.strip() for value in odds_sports if value and value.strip()]
    return normalized_sports or ["upcoming"]


def probe_provider(
    *,
    provider: str,
    api_sports_mode: str,
    api_sports_date: str | None,
    api_sports_next: int | None,
    odds_mode: str,
    odds_sports: Sequence[str],
    odds_regions: str,
    odds_markets: str,
    odds_format: str,
    odds_date_format: str,
    normalize: bool,
    report_input: bool,
    env: Mapping[str, str],
    api_sports_transport: Transport | None = None,
    odds_transport: Transport | None = None,
    secret_prompt: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    try:
        if report_input and provider != "odds":
            raise LiveApiProbeError("--report-input is only supported with --provider odds.")

        if provider == "api-sports":
            api_key = require_env_key(
                env,
                "API_SPORTS_KEY",
                provider_name="api-sports",
                secret_prompt=secret_prompt,
            )
            return probe_api_sports(
                api_key=api_key,
                mode=api_sports_mode,
                fixture_date=api_sports_date,
                next_count=api_sports_next,
                transport=api_sports_transport,
            )

        if provider == "odds":
            api_key = require_env_key(
                env,
                "ODDS_API_KEY",
                provider_name="odds",
                secret_prompt=secret_prompt,
            )
            return probe_odds(
                api_key=api_key,
                mode=odds_mode,
                sport_keys=odds_sports,
                regions=odds_regions,
                markets=odds_markets,
                odds_format=odds_format,
                date_format=odds_date_format,
                normalize=normalize,
                report_input=report_input,
                transport=odds_transport,
            )
    except (
        ApiRequestError,
        ApiResponseFormatError,
        LiveApiConfigurationError,
        MultiSportOddsMapperError,
        ReportInputLoaderError,
    ) as error:
        raise LiveApiProbeError(str(error)) from error

    raise LiveApiProbeError("Unsupported provider. Use one of: api-sports, odds, both.")


def require_env_key(
    env: Mapping[str, str],
    env_name: str,
    *,
    provider_name: str,
    secret_prompt: Callable[[str], str] | None = None,
) -> str:
    value = env.get(env_name, "").strip()
    if not value and secret_prompt is not None:
        value = secret_prompt(f"Enter {env_name} for {provider_name} live probe: ").strip()
    if not value:
        raise LiveApiProbeError(f"{env_name} is required for {provider_name} live probe.")
    return value


def probe_api_sports(
    *,
    api_key: str,
    mode: str,
    fixture_date: str | None,
    next_count: int | None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    if mode == "status":
        payload = fetch_live_object(
            transport=transport,
            url=build_request_url(API_SPORTS_BASE_URL, "/status"),
            headers={"x-apisports-key": api_key},
            source_name="API-Sports live status response",
        )
        return summarize_api_sports_status_payload(payload)

    if mode == "fixtures":
        client = ApiSportsClient(
            api_key=api_key,
            base_url=API_SPORTS_BASE_URL,
            transport=transport,
        )
        payload = client.fetch_fixtures(
            params=build_api_sports_fixture_params(
                fixture_date=fixture_date,
                next_count=next_count,
            ),
            use_live=True,
        )
        return summarize_api_sports_fixtures_payload(payload)

    raise LiveApiProbeError("Unsupported api-sports mode. Use one of: status, fixtures.")


def probe_odds(
    *,
    api_key: str,
    mode: str,
    sport_keys: Sequence[str],
    regions: str,
    markets: str,
    odds_format: str,
    date_format: str,
    normalize: bool,
    report_input: bool,
    transport: Transport | None = None,
) -> dict[str, Any]:
    if mode == "sports":
        if normalize or report_input:
            raise LiveApiProbeError(
                "--normalize and --report-input are only supported with "
                "--provider odds --odds-mode odds."
            )
        payload = fetch_live_list(
            transport=transport,
            url=build_request_url(ODDS_API_BASE_URL, "/v4/sports", {"apiKey": api_key}),
            headers={},
            source_name="The Odds API live sports response",
        )
        return summarize_odds_sports_payload(payload)

    if mode == "odds":
        client = OddsApiClient(
            api_key=api_key,
            base_url=ODDS_API_BASE_URL,
            transport=transport,
        )
        if report_input:
            raw_events = fetch_live_odds_events_for_sport_keys(
                sport_keys,
                regions=(regions,),
                markets=(markets,),
                odds_format=odds_format,
                date_format=date_format,
                allow_live=True,
                api_key=api_key,
                client=client,
                base_url=ODDS_API_BASE_URL,
            )
            normalized_events = normalize_live_odds_events(
                group_live_events_by_sport_key(raw_events)
            )
            return summarize_report_input_probe(
                raw_events,
                normalized_events=normalized_events,
                report_input_payload=build_report_input_for_probe(normalized_events),
                sport_keys=sport_keys,
            )

        if normalize:
            raw_events = fetch_live_odds_events_for_sport_keys(
                sport_keys,
                regions=(regions,),
                markets=(markets,),
                odds_format=odds_format,
                date_format=date_format,
                allow_live=True,
                api_key=api_key,
                client=client,
                base_url=ODDS_API_BASE_URL,
            )
            normalized_events = normalize_live_odds_events(
                group_live_events_by_sport_key(raw_events)
            )
            return summarize_normalized_odds_events(
                raw_events,
                normalized_events=normalized_events,
                sport_keys=sport_keys,
            )

        if len(sport_keys) == 1:
            payload = client.fetch_events(
                sport_key=sport_keys[0],
                params={
                    "regions": regions,
                    "markets": markets,
                    "oddsFormat": odds_format,
                    "dateFormat": date_format,
                },
                use_live=True,
            )
            return summarize_odds_events_payload(payload, sport_key_count=1)

        raw_events = fetch_live_odds_events_for_sport_keys(
            sport_keys,
            regions=(regions,),
            markets=(markets,),
            odds_format=odds_format,
            date_format=date_format,
            allow_live=True,
            api_key=api_key,
            client=client,
            base_url=ODDS_API_BASE_URL,
        )
        return summarize_odds_events_payload(raw_events, sport_key_count=len(sport_keys))

    raise LiveApiProbeError("Unsupported odds mode. Use one of: sports, odds.")


def fetch_live_object(
    *,
    transport: Transport | None,
    url: str,
    headers: Mapping[str, str],
    source_name: str,
) -> dict[str, Any]:
    payload = (transport or default_json_transport)(url, headers)
    if not isinstance(payload, dict):
        raise ApiResponseFormatError(f"{source_name} must be a JSON object.")
    return payload


def fetch_live_list(
    *,
    transport: Transport | None,
    url: str,
    headers: Mapping[str, str],
    source_name: str,
) -> list[dict[str, Any]]:
    payload = (transport or default_json_transport)(url, headers)
    if not isinstance(payload, list):
        raise ApiResponseFormatError(f"{source_name} must be a JSON list.")
    if not all(isinstance(item, dict) for item in payload):
        raise ApiResponseFormatError(f"{source_name} must contain only JSON objects.")
    return payload


def build_api_sports_fixture_params(
    *,
    fixture_date: str | None,
    next_count: int | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if fixture_date:
        params["date"] = fixture_date
    if next_count is not None:
        params["next"] = next_count
    return params


def summarize_api_sports_status_payload(payload: dict[str, Any]) -> dict[str, Any]:
    response_items = payload.get("response")
    response_item_count = len(response_items) if isinstance(response_items, list) else None
    return {
        "provider": "api-sports",
        "probe_mode": "status",
        "status": "empty" if response_item_count == 0 else "success",
        "top_level_keys": sorted(payload.keys()),
        "response_item_count": response_item_count,
    }


def summarize_api_sports_fixtures_payload(payload: dict[str, Any]) -> dict[str, Any]:
    response_items = payload.get("response", [])
    response_item_count = len(response_items) if isinstance(response_items, list) else None
    return {
        "provider": "api-sports",
        "probe_mode": "fixtures",
        "status": "empty" if response_item_count == 0 else "success",
        "top_level_keys": sorted(payload.keys()),
        "response_item_count": response_item_count,
        "sample_fixture_ids": extract_api_sports_fixture_ids(response_items),
        "sample_matchups": extract_api_sports_matchups(response_items),
        "sample_leagues": extract_api_sports_leagues(response_items),
    }


def summarize_odds_sports_payload(payload: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "provider": "odds",
        "probe_mode": "sports",
        "status": "empty" if len(payload) == 0 else "success",
        "top_level_keys": ["list"],
        "sport_count": len(payload),
        "sample_sport_keys": extract_odds_sport_keys(payload),
    }


def summarize_odds_events_payload(
    payload: dict[str, Any] | list[dict[str, Any]],
    *,
    sport_key_count: int | None = None,
) -> dict[str, Any]:
    if isinstance(payload, list):
        events = payload
        top_level_keys = ["list"]
    else:
        events = payload.get("events", [])
        top_level_keys = sorted(payload.keys())

    return {
        "provider": "odds",
        "probe_mode": "odds",
        "status": "empty" if len(events) == 0 else "success",
        "top_level_keys": top_level_keys,
        "sport_key_count": sport_key_count,
        "event_count": len(events) if isinstance(events, list) else None,
        "sample_event_ids": extract_odds_event_ids(events),
        "sample_matchups": extract_odds_matchups(events),
        "bookmaker_count": count_bookmakers(events),
    }


def summarize_normalized_odds_events(
    raw_events: list[dict[str, Any]],
    *,
    normalized_events: Sequence[Any],
    sport_keys: Sequence[str],
) -> dict[str, Any]:
    return {
        "provider": "odds",
        "probe_mode": "odds",
        "status": "empty" if len(raw_events) == 0 else "success",
        "sport_key_count": len(sport_keys),
        "raw_event_count": len(raw_events),
        "normalized_event_count": len(normalized_events),
        "sample_event_ids": extract_odds_event_ids(raw_events),
        "missing_data_count": count_normalized_missing_data(normalized_events),
    }


def summarize_report_input_probe(
    raw_events: list[dict[str, Any]],
    *,
    normalized_events: Sequence[Any],
    report_input_payload: Any | None,
    sport_keys: Sequence[str],
) -> dict[str, Any]:
    status = "empty" if len(normalized_events) == 0 else "success"
    report_input_status = "built" if report_input_payload is not None else "skipped_no_events"
    return {
        "provider": "odds",
        "probe_mode": "report_input",
        "status": status,
        "sport_key_count": len(sport_keys),
        "raw_event_count": len(raw_events),
        "normalized_event_count": len(normalized_events),
        "report_input_status": report_input_status,
        "report_input_region": getattr(report_input_payload, "region", None),
        "report_input_mode": (
            getattr(report_input_payload, "mode", None) if report_input_payload else "live"
        ),
        "report_input_game_count": len(getattr(report_input_payload, "games", ())),
        "missing_data_count": (
            count_report_input_missing_data(report_input_payload)
            if report_input_payload is not None
            else count_normalized_missing_data(normalized_events)
        ),
        "sample_event_ids": extract_odds_event_ids(raw_events),
        "sample_game_ids": (
            [game.game_id for game in report_input_payload.games[:3]]
            if report_input_payload is not None
            else []
        ),
    }


def group_live_events_by_sport_key(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped_events: dict[str, list[dict[str, Any]]] = {}
    for item in events:
        if not isinstance(item, Mapping):
            raise LiveApiProbeError("Live odds probe returned a non-object event payload.")
        sport_key = str(item.get("sport_key", "")).strip()
        if not sport_key:
            raise LiveApiProbeError("Live odds event is missing required field 'sport_key'.")
        grouped_events.setdefault(sport_key, []).append(dict(item))
    return grouped_events


def count_normalized_missing_data(normalized_events: Sequence[Any]) -> int:
    missing_data_count = 0
    for event in normalized_events:
        missing_data_count += len(getattr(event, "missing_data", ()))
        h2h_market = getattr(event, "h2h_market", None)
        if h2h_market is None:
            continue
        missing_data_count += len(getattr(h2h_market, "missing_data", ()))
        for outcome in getattr(h2h_market, "outcomes", ()):
            missing_data_count += len(getattr(outcome, "missing_data", ()))
    return missing_data_count


def count_report_input_missing_data(report_input_payload: Any) -> int:
    missing_data_count = len(getattr(report_input_payload, "missing_data", ()))
    for game in getattr(report_input_payload, "games", ()):
        missing_data_count += len(getattr(game, "missing_data", ()))
    return missing_data_count


def build_report_input_for_probe(normalized_events: Sequence[Any]) -> Any | None:
    if not normalized_events:
        return None

    report_input_region = derive_report_input_region(normalized_events)
    return load_report_input_from_normalized_odds_events(
        normalized_events=list(normalized_events),
        region=report_input_region,
        mode="live",
        analysis_mode="manual_probe",
    )


def derive_report_input_region(normalized_events: Sequence[Any]) -> str:
    if not normalized_events:
        raise LiveApiProbeError(
            "No live odds events were returned, so ReportInput could not be built."
        )

    derived_regions: set[str] = set()
    for event in normalized_events:
        sport_key = str(getattr(event, "sport_key", "")).strip()
        if not sport_key:
            raise LiveApiProbeError("Normalized odds event is missing required field 'sport_key'.")
        source = get_source_by_league_key(sport_key)
        derived_regions.add("east" if source.report_slot == "asia_day_preview" else "west")

    if len(derived_regions) != 1:
        raise LiveApiProbeError(
            "Normalized live odds events span multiple report regions. "
            "Re-run with one region-specific sport set."
        )

    return next(iter(derived_regions))


def extract_api_sports_fixture_ids(response_items: Any) -> list[str]:
    if not isinstance(response_items, list):
        return []

    sample_ids: list[str] = []
    for item in response_items[:3]:
        if not isinstance(item, dict):
            continue
        fixture = item.get("fixture", {})
        if isinstance(fixture, dict) and fixture.get("id") is not None:
            sample_ids.append(str(fixture["id"]))
    return sample_ids


def extract_api_sports_matchups(response_items: Any) -> list[str]:
    if not isinstance(response_items, list):
        return []

    matchups: list[str] = []
    for item in response_items[:3]:
        if not isinstance(item, dict):
            continue
        teams = item.get("teams", {})
        if not isinstance(teams, dict):
            continue
        home_name = _read_nested_name(teams.get("home"))
        away_name = _read_nested_name(teams.get("away"))
        if home_name and away_name:
            matchups.append(f"{home_name} vs {away_name}")
    return matchups


def extract_api_sports_leagues(response_items: Any) -> list[str]:
    if not isinstance(response_items, list):
        return []

    leagues: list[str] = []
    for item in response_items[:3]:
        if not isinstance(item, dict):
            continue
        league_name = _read_nested_name(item.get("league"))
        if league_name:
            leagues.append(league_name)
    return leagues


def extract_odds_event_ids(events: Any) -> list[str]:
    if not isinstance(events, list):
        return []

    sample_ids: list[str] = []
    for item in events[:3]:
        if not isinstance(item, dict):
            continue
        if item.get("id") is not None:
            sample_ids.append(str(item["id"]))
    return sample_ids


def extract_odds_matchups(events: Any) -> list[str]:
    if not isinstance(events, list):
        return []

    matchups: list[str] = []
    for item in events[:3]:
        if not isinstance(item, dict):
            continue
        home_team = str(item.get("home_team", "")).strip()
        away_team = str(item.get("away_team", "")).strip()
        if home_team and away_team:
            matchups.append(f"{home_team} vs {away_team}")
    return matchups


def extract_odds_sport_keys(events: Any) -> list[str]:
    if not isinstance(events, list):
        return []

    sport_keys: list[str] = []
    for item in events[:3]:
        if not isinstance(item, dict):
            continue
        sport_key = str(item.get("key", "") or item.get("sport_key", "")).strip()
        if sport_key:
            sport_keys.append(sport_key)
    return sport_keys


def count_bookmakers(events: Any) -> int | None:
    if not isinstance(events, list):
        return None

    bookmaker_count = 0
    for item in events:
        if not isinstance(item, dict):
            continue
        bookmakers = item.get("bookmakers")
        if isinstance(bookmakers, list):
            bookmaker_count += len(bookmakers)
    return bookmaker_count


def _read_nested_name(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = str(payload.get("name", "")).strip()
    return value or None


def format_summary(summary: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    ordered_keys = (
        "provider",
        "probe_mode",
        "status",
        "top_level_keys",
        "response_item_count",
        "sport_count",
        "sport_key_count",
        "event_count",
        "raw_event_count",
        "normalized_event_count",
        "report_input_status",
        "report_input_region",
        "report_input_mode",
        "report_input_game_count",
        "bookmaker_count",
        "missing_data_count",
        "sample_fixture_ids",
        "sample_event_ids",
        "sample_game_ids",
        "sample_sport_keys",
        "sample_matchups",
        "sample_leagues",
    )
    for key in ordered_keys:
        if key not in summary:
            continue
        value = summary[key]
        if isinstance(value, list):
            rendered = ", ".join(value) if value else "none"
        else:
            rendered = "none" if value is None else str(value)
        lines.append(f"{key}: {rendered}")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
