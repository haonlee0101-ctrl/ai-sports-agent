from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

JsonObject = dict[str, Any]
JsonPayload = JsonObject | list[JsonObject]
Transport = Callable[[str, Mapping[str, str]], JsonPayload]


class ApiClientError(ValueError):
    """Base error for beginner-friendly local/live API client wrappers."""


class LiveApiConfigurationError(ApiClientError):
    """Raised when live mode is requested without explicit client configuration."""


class ApiResponseFormatError(ApiClientError):
    """Raised when a fake or live response does not match the expected JSON shape."""


class ApiRequestError(ApiClientError):
    """Raised when a live request fails before a valid JSON response is returned."""


class ApiSportsClient:
    """Thin API-Sports client wrapper with fake-response support for tests."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        fake_response: JsonObject | None = None,
        transport: Transport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.fake_response = fake_response
        self.transport = transport or default_json_transport

    def fetch_fixtures(
        self,
        *,
        params: Mapping[str, Any] | None = None,
        use_live: bool = False,
    ) -> JsonObject:
        if self.fake_response is not None:
            return validate_api_sports_response(self.fake_response, source_name="fake response")

        if not use_live:
            raise LiveApiConfigurationError(
                "API-Sports client has no fake response configured. "
                "Provide fake_response or request live mode explicitly."
            )

        api_key = require_live_api_key(
            self.api_key,
            provider_name="API-Sports",
        )
        base_url = require_live_base_url(
            self.base_url,
            provider_name="API-Sports",
        )
        url = build_request_url(base_url, "/fixtures", params)
        payload = self.transport(url, {"x-apisports-key": api_key})
        return validate_api_sports_response(payload, source_name="live API-Sports response")


class OddsApiClient:
    """Thin The Odds API client wrapper with fake-response support for tests."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        fake_response: JsonPayload | None = None,
        transport: Transport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.fake_response = fake_response
        self.transport = transport or default_json_transport

    def fetch_events(
        self,
        *,
        sport_key: str = "upcoming",
        params: Mapping[str, Any] | None = None,
        use_live: bool = False,
    ) -> JsonPayload:
        if self.fake_response is not None:
            return validate_odds_api_response(self.fake_response, source_name="fake response")

        if not use_live:
            raise LiveApiConfigurationError(
                "The Odds API client has no fake response configured. "
                "Provide fake_response or request live mode explicitly."
            )

        api_key = require_live_api_key(
            self.api_key,
            provider_name="The Odds API",
        )
        base_url = require_live_base_url(
            self.base_url,
            provider_name="The Odds API",
        )
        odds_params = dict(params or {})
        odds_params["apiKey"] = api_key
        path = f"/v4/sports/{sport_key}/odds"
        url = build_request_url(base_url, path, odds_params)
        payload = self.transport(url, {})
        return validate_odds_api_response(payload, source_name="live The Odds API response")


def require_live_api_key(api_key: str | None, *, provider_name: str) -> str:
    if api_key is None or not api_key.strip():
        raise LiveApiConfigurationError(f"{provider_name} live mode requires an explicit API key.")
    return api_key.strip()


def require_live_base_url(base_url: str | None, *, provider_name: str) -> str:
    if base_url is None or not base_url.strip():
        raise LiveApiConfigurationError(f"{provider_name} live mode requires an explicit base URL.")
    return base_url.rstrip("/")


def build_request_url(
    base_url: str,
    path: str,
    params: Mapping[str, Any] | None = None,
) -> str:
    normalized_path = path if path.startswith("/") else f"/{path}"
    if not params:
        return f"{base_url}{normalized_path}"

    query_string = urlencode(
        {key: value for key, value in params.items() if value is not None},
        doseq=True,
    )
    return f"{base_url}{normalized_path}?{query_string}"


def validate_api_sports_response(
    payload: JsonPayload,
    *,
    source_name: str,
) -> JsonObject:
    if not isinstance(payload, dict):
        raise ApiResponseFormatError(f"API-Sports {source_name} must be a JSON object.")

    response_items = payload.get("response")
    if not isinstance(response_items, list):
        raise ApiResponseFormatError(f"API-Sports {source_name} must include a 'response' list.")

    if not all(isinstance(item, dict) for item in response_items):
        raise ApiResponseFormatError(
            f"API-Sports {source_name} must use JSON objects inside 'response'."
        )

    return deepcopy(payload)


def validate_odds_api_response(
    payload: JsonPayload,
    *,
    source_name: str,
) -> JsonPayload:
    if isinstance(payload, list):
        if not all(isinstance(item, dict) for item in payload):
            raise ApiResponseFormatError(
                f"The Odds API {source_name} list must contain only JSON objects."
            )
        return deepcopy(payload)

    if not isinstance(payload, dict):
        raise ApiResponseFormatError(f"The Odds API {source_name} must be a JSON object or list.")

    events = payload.get("events")
    if not isinstance(events, list):
        raise ApiResponseFormatError(f"The Odds API {source_name} must include an 'events' list.")

    if not all(isinstance(item, dict) for item in events):
        raise ApiResponseFormatError(
            f"The Odds API {source_name} must use JSON objects inside 'events'."
        )

    return deepcopy(payload)


def default_json_transport(url: str, headers: Mapping[str, str]) -> JsonPayload:
    request = Request(url, headers=dict(headers))
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise ApiRequestError(f"Live API request failed with HTTP {error.code}.") from error
    except URLError as error:
        raise ApiRequestError(f"Live API request failed: {error.reason}") from error
    except json.JSONDecodeError as error:
        raise ApiRequestError(f"Live API request returned invalid JSON: {error.msg}") from error

    if not isinstance(payload, (dict, list)):
        raise ApiResponseFormatError("Live API response must decode to a JSON object or list.")

    return payload
