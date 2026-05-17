from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.live_odds_fetcher import (  # noqa: E402
    LiveOddsDisabledError,
    LiveOddsFetchConfig,
    LiveOddsFetcherError,
    MissingLiveOddsApiKeyError,
    fetch_and_normalize_live_odds_events,
    fetch_and_normalize_live_odds_events_for_sport_keys,
    fetch_live_odds_events,
    fetch_live_odds_events_for_sport_keys,
)


class RecordingFakeOddsClient:
    def __init__(self, responses_by_sport_key):
        self.responses_by_sport_key = responses_by_sport_key
        self.calls: list[dict[str, object]] = []

    def fetch_events(self, *, sport_key, params=None, use_live=False):
        self.calls.append(
            {
                "sport_key": sport_key,
                "params": dict(params or {}),
                "use_live": use_live,
            }
        )
        return self.responses_by_sport_key[sport_key]


def test_allow_live_false_fails_before_transport_is_called() -> None:
    client = RecordingFakeOddsClient(
        {
            "baseball_mlb": [
                {
                    "id": "mlb-live-001",
                    "sport_key": "baseball_mlb",
                }
            ]
        }
    )
    config = LiveOddsFetchConfig(sport_keys=("baseball_mlb",), allow_live=False)

    with pytest.raises(
        LiveOddsDisabledError,
        match=re.escape("Live odds fetching is disabled by default. Re-run with allow_live=True."),
    ):
        fetch_live_odds_events(
            config,
            api_key="test-key",
            client=client,
        )

    assert client.calls == []


def test_allow_live_true_without_api_key_fails_before_transport_is_called() -> None:
    client = RecordingFakeOddsClient({"baseball_mlb": []})
    config = LiveOddsFetchConfig(sport_keys=("baseball_mlb",), allow_live=True)

    with pytest.raises(
        MissingLiveOddsApiKeyError,
        match=re.escape("Live odds fetching requires an explicit API key when allow_live=True."),
    ):
        fetch_live_odds_events(config, client=client)

    assert client.calls == []


def test_allow_live_true_with_api_key_uses_injected_fake_client() -> None:
    client = RecordingFakeOddsClient(
        {
            "baseball_mlb": [
                {
                    "id": "mlb-live-001",
                    "sport_key": "baseball_mlb",
                    "home_team": "Sample Home",
                    "away_team": "Sample Away",
                }
            ]
        }
    )
    config = LiveOddsFetchConfig(sport_keys=("baseball_mlb",), allow_live=True)

    events = fetch_live_odds_events(
        config,
        api_key="test-key",
        client=client,
    )

    assert len(client.calls) == 1
    assert client.calls[0]["sport_key"] == "baseball_mlb"
    assert client.calls[0]["use_live"] is True
    assert events == [
        {
            "id": "mlb-live-001",
            "sport_key": "baseball_mlb",
            "home_team": "Sample Home",
            "away_team": "Sample Away",
        }
    ]


def test_sport_keys_are_requested_one_by_one() -> None:
    client = RecordingFakeOddsClient(
        {
            "baseball_mlb": [{"id": "mlb-live-001", "sport_key": "baseball_mlb"}],
            "basketball_nba": [{"id": "nba-live-001", "sport_key": "basketball_nba"}],
        }
    )

    events = fetch_live_odds_events_for_sport_keys(
        ("baseball_mlb", "basketball_nba"),
        allow_live=True,
        api_key="test-key",
        client=client,
    )

    assert [call["sport_key"] for call in client.calls] == [
        "baseball_mlb",
        "basketball_nba",
    ]
    assert [event["id"] for event in events] == [
        "mlb-live-001",
        "nba-live-001",
    ]


def test_regions_markets_and_formats_are_passed_to_injected_client() -> None:
    client = RecordingFakeOddsClient(
        {
            "soccer_epl": [
                {
                    "id": "epl-live-001",
                    "sport_key": "soccer_epl",
                }
            ]
        }
    )
    config = LiveOddsFetchConfig(
        sport_keys=("soccer_epl",),
        regions=("us", "eu"),
        markets=("h2h", "spreads"),
        odds_format="decimal",
        date_format="iso",
        allow_live=True,
    )

    fetch_live_odds_events(
        config,
        api_key="test-key",
        client=client,
    )

    assert client.calls[0]["params"] == {
        "regions": "us,eu",
        "markets": "h2h,spreads",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }


def test_fake_client_can_return_events_from_events_object_payload() -> None:
    client = RecordingFakeOddsClient(
        {
            "soccer_epl": {
                "events": [
                    {
                        "id": "epl-live-001",
                        "sport_key": "soccer_epl",
                    }
                ]
            }
        }
    )
    config = LiveOddsFetchConfig(sport_keys=("soccer_epl",), allow_live=True)

    events = fetch_live_odds_events(
        config,
        api_key="test-key",
        client=client,
    )

    assert events == [{"id": "epl-live-001", "sport_key": "soccer_epl"}]


def test_multiple_sport_keys_return_combined_events() -> None:
    client = RecordingFakeOddsClient(
        {
            "baseball_mlb": [
                {"id": "mlb-live-001", "sport_key": "baseball_mlb"},
                {"id": "mlb-live-002", "sport_key": "baseball_mlb"},
            ],
            "soccer_epl": [
                {"id": "epl-live-001", "sport_key": "soccer_epl"},
            ],
        }
    )
    config = LiveOddsFetchConfig(
        sport_keys=("baseball_mlb", "soccer_epl"),
        allow_live=True,
    )

    events = fetch_live_odds_events(
        config,
        api_key="test-key",
        client=client,
    )

    assert [event["id"] for event in events] == [
        "mlb-live-001",
        "mlb-live-002",
        "epl-live-001",
    ]


def test_empty_sport_keys_fail_clearly() -> None:
    with pytest.raises(
        LiveOddsFetcherError,
        match=re.escape("sport_keys must include at least one sport key."),
    ):
        LiveOddsFetchConfig(sport_keys=(), allow_live=True)


def test_invalid_sport_key_fails_clearly() -> None:
    with pytest.raises(
        LiveOddsFetcherError,
        match=re.escape("sport_keys contains an unsupported value: baseball-mlb."),
    ):
        LiveOddsFetchConfig(sport_keys=("baseball-mlb",), allow_live=True)


def test_api_key_is_never_printed_and_raw_response_is_not_printed(capsys) -> None:
    client = RecordingFakeOddsClient(
        {
            "basketball_nba": [
                {
                    "id": "nba-live-001",
                    "sport_key": "basketball_nba",
                    "secret_like_value": "not-printed",
                }
            ]
        }
    )
    config = LiveOddsFetchConfig(sport_keys=("basketball_nba",), allow_live=True)

    events = fetch_live_odds_events(
        config,
        api_key="test-key-123",
        client=client,
    )
    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == ""
    assert events[0]["secret_like_value"] == "not-printed"


def test_live_odds_fetcher_does_not_contain_hardcoded_secret_looking_values() -> None:
    source_text = (PROJECT_ROOT / "src" / "collectors" / "live_odds_fetcher.py").read_text(
        encoding="utf-8"
    )
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"https?://[^\\s\"']+[?&](?:api_?key|key|token)=",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, source_text) is None


def test_fetch_and_normalize_live_path_fails_before_transport_when_live_is_disabled() -> None:
    client = RecordingFakeOddsClient({"baseball_mlb": []})
    config = LiveOddsFetchConfig(sport_keys=("baseball_mlb",), allow_live=False)

    with pytest.raises(
        LiveOddsDisabledError,
        match=re.escape("Live odds fetching is disabled by default. Re-run with allow_live=True."),
    ):
        fetch_and_normalize_live_odds_events(
            config,
            api_key="test-key",
            client=client,
        )

    assert client.calls == []


def test_fetch_and_normalize_live_path_fails_before_transport_when_api_key_is_missing() -> None:
    client = RecordingFakeOddsClient({"baseball_mlb": []})
    config = LiveOddsFetchConfig(sport_keys=("baseball_mlb",), allow_live=True)

    with pytest.raises(
        MissingLiveOddsApiKeyError,
        match=re.escape("Live odds fetching requires an explicit API key when allow_live=True."),
    ):
        fetch_and_normalize_live_odds_events(
            config,
            client=client,
        )

    assert client.calls == []


def test_fetch_and_normalize_live_path_uses_injected_fake_client_only() -> None:
    client = RecordingFakeOddsClient(
        {
            "baseball_mlb": [
                {
                    "id": "mlb-live-001",
                    "sport_key": "baseball_mlb",
                    "sport_title": "MLB",
                    "commence_time": "2026-05-17T23:05:00Z",
                    "home_team": "Sample Home",
                    "away_team": "Sample Away",
                    "bookmakers": [],
                }
            ]
        }
    )
    config = LiveOddsFetchConfig(sport_keys=("baseball_mlb",), allow_live=True)

    normalized_events = fetch_and_normalize_live_odds_events(
        config,
        api_key="test-key",
        client=client,
    )

    assert len(client.calls) == 1
    assert client.calls[0]["use_live"] is True
    assert normalized_events[0].game_id == "mlb-live-001"
    assert "Event does not include bookmaker data." in normalized_events[0].missing_data


def test_fetch_and_normalize_live_path_handles_multiple_sport_keys() -> None:
    client = RecordingFakeOddsClient(
        {
            "baseball_mlb": [
                {
                    "id": "mlb-live-001",
                    "sport_key": "baseball_mlb",
                    "sport_title": "MLB",
                    "commence_time": "2026-05-17T23:05:00Z",
                    "home_team": "Sample Home",
                    "away_team": "Sample Away",
                    "bookmakers": [],
                }
            ],
            "soccer_epl": [
                {
                    "id": "epl-live-001",
                    "sport_key": "soccer_epl",
                    "sport_title": "Premier League",
                    "commence_time": "2026-05-17T12:30:00Z",
                    "home_team": "Sample FC",
                    "away_team": "Away FC",
                    "bookmakers": [],
                }
            ],
        }
    )

    normalized_events = fetch_and_normalize_live_odds_events_for_sport_keys(
        ("baseball_mlb", "soccer_epl"),
        allow_live=True,
        api_key="test-key",
        client=client,
    )

    assert [event.game_id for event in normalized_events] == [
        "mlb-live-001",
        "epl-live-001",
    ]
    assert [call["sport_key"] for call in client.calls] == [
        "baseball_mlb",
        "soccer_epl",
    ]
