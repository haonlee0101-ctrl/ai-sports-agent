from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any, TextIO

from src.collectors.api_clients import (
    ApiRequestError,
    ApiResponseFormatError,
    ApiSportsClient,
    LiveApiConfigurationError,
    OddsApiClient,
    Transport,
)

API_SPORTS_BASE_URL = "https://v3.football.api-sports.io"
ODDS_API_BASE_URL = "https://api.the-odds-api.com"
SUPPORTED_PROVIDERS = ("api-sports", "odds", "both")


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
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    api_sports_transport: Transport | None = None,
    odds_transport: Transport | None = None,
) -> int:
    stream = stdout or sys.stdout
    environment = env or os.environ
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        summaries = run_probe(
            provider=args.provider,
            confirm_live=args.confirm_live,
            env=environment,
            api_sports_transport=api_sports_transport,
            odds_transport=odds_transport,
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
    env: Mapping[str, str],
    api_sports_transport: Transport | None = None,
    odds_transport: Transport | None = None,
) -> list[dict[str, Any]]:
    normalized_provider = validate_provider(provider)

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
                env=env,
                api_sports_transport=api_sports_transport,
                odds_transport=odds_transport,
            )
        )
    return summaries


def validate_provider(provider: str) -> str:
    normalized_provider = provider.strip().lower()
    if normalized_provider not in SUPPORTED_PROVIDERS:
        raise LiveApiProbeError("Unsupported provider. Use one of: api-sports, odds, both.")
    return normalized_provider


def probe_provider(
    *,
    provider: str,
    env: Mapping[str, str],
    api_sports_transport: Transport | None = None,
    odds_transport: Transport | None = None,
) -> dict[str, Any]:
    try:
        if provider == "api-sports":
            api_key = require_env_key(env, "API_SPORTS_KEY", provider_name="api-sports")
            client = ApiSportsClient(
                api_key=api_key,
                base_url=API_SPORTS_BASE_URL,
                transport=api_sports_transport,
            )
            payload = client.fetch_fixtures(params={"next": 1}, use_live=True)
            return summarize_api_sports_payload(payload)

        if provider == "odds":
            api_key = require_env_key(env, "ODDS_API_KEY", provider_name="odds")
            client = OddsApiClient(
                api_key=api_key,
                base_url=ODDS_API_BASE_URL,
                transport=odds_transport,
            )
            payload = client.fetch_events(
                sport_key="upcoming",
                params={
                    "regions": "us",
                    "markets": "h2h",
                    "oddsFormat": "decimal",
                },
                use_live=True,
            )
            return summarize_odds_payload(payload)
    except (
        ApiRequestError,
        ApiResponseFormatError,
        LiveApiConfigurationError,
    ) as error:
        raise LiveApiProbeError(str(error)) from error

    raise LiveApiProbeError("Unsupported provider. Use one of: api-sports, odds, both.")


def require_env_key(
    env: Mapping[str, str],
    env_name: str,
    *,
    provider_name: str,
) -> str:
    value = env.get(env_name, "").strip()
    if not value:
        raise LiveApiProbeError(f"{env_name} is required for {provider_name} live probe.")
    return value


def summarize_api_sports_payload(payload: dict[str, Any]) -> dict[str, Any]:
    response_items = payload.get("response", [])
    return {
        "provider": "api-sports",
        "status": "success",
        "top_level_keys": sorted(payload.keys()),
        "item_count": len(response_items) if isinstance(response_items, list) else None,
        "sample_refs": extract_api_sports_refs(response_items),
    }


def summarize_odds_payload(payload: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
    if isinstance(payload, list):
        events = payload
        top_level_keys = ["list"]
    else:
        events = payload.get("events", [])
        top_level_keys = sorted(payload.keys())

    return {
        "provider": "odds",
        "status": "success",
        "top_level_keys": top_level_keys,
        "item_count": len(events) if isinstance(events, list) else None,
        "sample_refs": extract_odds_refs(events),
    }


def extract_api_sports_refs(response_items: Any) -> list[str]:
    if not isinstance(response_items, list):
        return []

    sample_refs: list[str] = []
    for item in response_items[:3]:
        if not isinstance(item, dict):
            continue
        fixture = item.get("fixture", {})
        if isinstance(fixture, dict) and fixture.get("id") is not None:
            sample_refs.append(str(fixture["id"]))
            continue
        teams = item.get("teams", {})
        if isinstance(teams, dict):
            home_name = _read_nested_name(teams.get("home"))
            away_name = _read_nested_name(teams.get("away"))
            if home_name and away_name:
                sample_refs.append(f"{home_name} vs {away_name}")
    return sample_refs


def extract_odds_refs(events: Any) -> list[str]:
    if not isinstance(events, list):
        return []

    sample_refs: list[str] = []
    for item in events[:3]:
        if not isinstance(item, dict):
            continue
        if item.get("id") is not None:
            sample_refs.append(str(item["id"]))
            continue
        home_team = str(item.get("home_team", "")).strip()
        away_team = str(item.get("away_team", "")).strip()
        if home_team and away_team:
            sample_refs.append(f"{home_team} vs {away_team}")
    return sample_refs


def _read_nested_name(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = str(payload.get("name", "")).strip()
    return value or None


def format_summary(summary: Mapping[str, Any]) -> list[str]:
    top_level_keys = summary["top_level_keys"]
    top_level_keys_text = ", ".join(top_level_keys) if top_level_keys else "none"
    lines = [
        f"provider: {summary['provider']}",
        f"status: {summary['status']}",
        f"top_level_keys: {top_level_keys_text}",
    ]
    item_count = summary.get("item_count")
    if item_count is not None:
        lines.append(f"item_count: {item_count}")
    sample_refs = summary.get("sample_refs", [])
    if sample_refs:
        lines.append(f"sample_refs: {', '.join(sample_refs)}")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
