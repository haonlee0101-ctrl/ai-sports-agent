from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.collectors.api_clients import OddsApiClient, validate_odds_api_response
from src.collectors.multisport_odds_mapper import (
    NormalizedOddsEvent,
    normalize_live_odds_events_for_sport_key,
)

DEFAULT_LIVE_ODDS_BASE_URL = "https://api.the-odds-api.com"
DEFAULT_REGIONS = ("us",)
DEFAULT_MARKETS = ("h2h",)


class LiveOddsFetcherError(ValueError):
    """Base error for the opt-in live odds fetcher skeleton."""


class LiveOddsDisabledError(LiveOddsFetcherError):
    """Raised when a caller tries to fetch live odds without explicit opt-in."""


class MissingLiveOddsApiKeyError(LiveOddsFetcherError):
    """Raised when live odds fetching is allowed but no API key was provided."""


@dataclass(frozen=True, slots=True)
class LiveOddsFetchConfig:
    """Beginner-friendly settings for one manual live odds fetch request."""

    sport_keys: tuple[str, ...]
    regions: tuple[str, ...] = DEFAULT_REGIONS
    markets: tuple[str, ...] = DEFAULT_MARKETS
    odds_format: str = "decimal"
    date_format: str = "iso"
    allow_live: bool = False

    def __post_init__(self) -> None:
        normalized_sport_keys = _normalize_string_values(self.sport_keys, field_name="sport_keys")
        normalized_regions = _normalize_string_values(
            self.regions,
            field_name="regions",
        )
        normalized_markets = _normalize_string_values(
            self.markets,
            field_name="markets",
        )
        normalized_odds_format = _normalize_single_value(
            self.odds_format,
            field_name="odds_format",
        )
        normalized_date_format = _normalize_single_value(
            self.date_format,
            field_name="date_format",
        )

        object.__setattr__(self, "sport_keys", normalized_sport_keys)
        object.__setattr__(self, "regions", normalized_regions)
        object.__setattr__(self, "markets", normalized_markets)
        object.__setattr__(self, "odds_format", normalized_odds_format)
        object.__setattr__(self, "date_format", normalized_date_format)

        if not normalized_sport_keys:
            raise LiveOddsFetcherError("sport_keys must include at least one sport key.")


def fetch_live_odds_events(
    config: LiveOddsFetchConfig,
    *,
    api_key: str | None = None,
    client: OddsApiClient | Any | None = None,
    base_url: str = DEFAULT_LIVE_ODDS_BASE_URL,
) -> list[dict[str, Any]]:
    """Fetch raw The Odds API-style event objects for the configured sport keys.

    This helper is intentionally opt-in only. It refuses to call any client unless
    ``allow_live=True`` and an explicit ``api_key`` are both provided.
    """

    return fetch_live_odds_events_for_sport_keys(
        config.sport_keys,
        regions=config.regions,
        markets=config.markets,
        odds_format=config.odds_format,
        date_format=config.date_format,
        allow_live=config.allow_live,
        api_key=api_key,
        client=client,
        base_url=base_url,
    )


def fetch_and_normalize_live_odds_events(
    config: LiveOddsFetchConfig,
    *,
    api_key: str | None = None,
    client: OddsApiClient | Any | None = None,
    base_url: str = DEFAULT_LIVE_ODDS_BASE_URL,
) -> list[NormalizedOddsEvent]:
    """Fetch and normalize live-style odds events through the shared mapper logic."""

    return fetch_and_normalize_live_odds_events_for_sport_keys(
        config.sport_keys,
        regions=config.regions,
        markets=config.markets,
        odds_format=config.odds_format,
        date_format=config.date_format,
        allow_live=config.allow_live,
        api_key=api_key,
        client=client,
        base_url=base_url,
    )


def fetch_live_odds_events_for_sport_keys(
    sport_keys: Sequence[str],
    *,
    regions: Sequence[str] = DEFAULT_REGIONS,
    markets: Sequence[str] = DEFAULT_MARKETS,
    odds_format: str = "decimal",
    date_format: str = "iso",
    allow_live: bool = False,
    api_key: str | None = None,
    client: OddsApiClient | Any | None = None,
    base_url: str = DEFAULT_LIVE_ODDS_BASE_URL,
) -> list[dict[str, Any]]:
    """Fetch raw event objects one sport key at a time with explicit live opt-in."""

    config = LiveOddsFetchConfig(
        sport_keys=tuple(sport_keys),
        regions=tuple(regions),
        markets=tuple(markets),
        odds_format=odds_format,
        date_format=date_format,
        allow_live=allow_live,
    )
    _ensure_live_allowed(config.allow_live)
    validated_api_key = _require_live_api_key(api_key)
    active_client = client or OddsApiClient(
        api_key=validated_api_key,
        base_url=base_url,
    )

    combined_events: list[dict[str, Any]] = []
    request_params = _build_request_params(config)
    for sport_key in config.sport_keys:
        payload = active_client.fetch_events(
            sport_key=sport_key,
            params=request_params,
            use_live=True,
        )
        combined_events.extend(
            _extract_event_list(
                payload,
                source_name=f"live odds response for {sport_key}",
            )
        )

    return combined_events


def fetch_and_normalize_live_odds_events_for_sport_keys(
    sport_keys: Sequence[str],
    *,
    regions: Sequence[str] = DEFAULT_REGIONS,
    markets: Sequence[str] = DEFAULT_MARKETS,
    odds_format: str = "decimal",
    date_format: str = "iso",
    allow_live: bool = False,
    api_key: str | None = None,
    client: OddsApiClient | Any | None = None,
    base_url: str = DEFAULT_LIVE_ODDS_BASE_URL,
) -> list[NormalizedOddsEvent]:
    """Fetch live-style events and normalize them with the multisport odds mapper."""

    config = LiveOddsFetchConfig(
        sport_keys=tuple(sport_keys),
        regions=tuple(regions),
        markets=tuple(markets),
        odds_format=odds_format,
        date_format=date_format,
        allow_live=allow_live,
    )
    _ensure_live_allowed(config.allow_live)
    validated_api_key = _require_live_api_key(api_key)
    active_client = client or OddsApiClient(
        api_key=validated_api_key,
        base_url=base_url,
    )

    normalized_events: list[NormalizedOddsEvent] = []
    request_params = _build_request_params(config)
    for sport_key in config.sport_keys:
        payload = active_client.fetch_events(
            sport_key=sport_key,
            params=request_params,
            use_live=True,
        )
        raw_events = _extract_event_list(
            payload,
            source_name=f"live odds response for {sport_key}",
        )
        normalized_events.extend(normalize_live_odds_events_for_sport_key(sport_key, raw_events))

    return normalized_events


def _build_request_params(config: LiveOddsFetchConfig) -> dict[str, str]:
    return {
        "regions": ",".join(config.regions),
        "markets": ",".join(config.markets),
        "oddsFormat": config.odds_format,
        "dateFormat": config.date_format,
    }


def _extract_event_list(
    payload: Mapping[str, Any] | list[dict[str, Any]],
    *,
    source_name: str,
) -> list[dict[str, Any]]:
    validated_payload = validate_odds_api_response(payload, source_name=source_name)
    if isinstance(validated_payload, list):
        return list(validated_payload)
    return list(validated_payload["events"])


def _ensure_live_allowed(allow_live: bool) -> None:
    if not allow_live:
        raise LiveOddsDisabledError(
            "Live odds fetching is disabled by default. Re-run with allow_live=True."
        )


def _require_live_api_key(api_key: str | None) -> str:
    if api_key is None or not api_key.strip():
        raise MissingLiveOddsApiKeyError(
            "Live odds fetching requires an explicit API key when allow_live=True."
        )
    return api_key.strip()


def _normalize_single_value(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise LiveOddsFetcherError(f"{field_name} must be provided as a string.")
    normalized_value = value.strip()
    if not normalized_value:
        raise LiveOddsFetcherError(f"{field_name} must not be empty.")
    return normalized_value


def _normalize_string_values(
    values: Sequence[str],
    *,
    field_name: str,
) -> tuple[str, ...]:
    if isinstance(values, str):
        values = (values,)

    normalized_values: list[str] = []
    for value in values:
        normalized_value = _normalize_single_value(value, field_name=field_name)
        _validate_sport_key_format(normalized_value, field_name=field_name)
        normalized_values.append(normalized_value)
    return tuple(normalized_values)


def _validate_sport_key_format(value: str, *, field_name: str) -> None:
    allowed_characters = set("abcdefghijklmnopqrstuvwxyz0123456789_,")
    if field_name == "sport_keys":
        allowed_characters = set("abcdefghijklmnopqrstuvwxyz0123456789_")

    if any(character not in allowed_characters for character in value.lower()):
        raise LiveOddsFetcherError(f"{field_name} contains an unsupported value: {value}.")
