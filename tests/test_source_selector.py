from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.api_clients import (  # noqa: E402
    ApiSportsClient,
    LiveApiConfigurationError,
    OddsApiClient,
)
from src.collectors.source_selector import (  # noqa: E402
    SourceSelectorError,
    load_report_input_for_source,
)
from src.contracts.report_input import ReportInput  # noqa: E402


def load_fixture(filename: str):
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_unsupported_source_fails_clearly() -> None:
    with pytest.raises(
        SourceSelectorError,
        match=re.escape(
            "Unsupported source. Use one of: mock, input_file, fixture, api_client_fake, live."
        ),
    ):
        load_report_input_for_source(source="unknown", region="east")


def test_live_source_fails_clearly_unless_explicitly_allowed() -> None:
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called when live source is disabled.")

    api_sports_client = ApiSportsClient(
        base_url="https://example.invalid",
        transport=raising_transport,
    )

    with pytest.raises(
        SourceSelectorError,
        match=re.escape("source='live' is disabled by default. Pass allow_live=True to enable it."),
    ):
        load_report_input_for_source(
            source="live",
            region="east",
            api_sports_client=api_sports_client,
        )

    assert transport_called is False


def test_live_source_does_not_call_network_by_default() -> None:
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called before explicit live opt-in.")

    api_sports_client = ApiSportsClient(
        base_url="https://example.invalid",
        transport=raising_transport,
    )

    with pytest.raises(SourceSelectorError):
        load_report_input_for_source(
            source="live",
            region="west",
            api_sports_client=api_sports_client,
        )

    assert transport_called is False


def test_api_client_fake_can_return_east_report_input_objects() -> None:
    report_input = load_report_input_for_source(
        source="api_client_fake",
        region="east",
        api_sports_client=ApiSportsClient(
            fake_response=load_fixture("api_sports_fixtures_sample.json"),
        ),
        odds_api_client=OddsApiClient(
            fake_response=load_fixture("odds_api_events_sample.json"),
        ),
    )

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "east"
    assert len(report_input.games) == 2


def test_api_client_fake_can_return_west_report_input_objects() -> None:
    report_input = load_report_input_for_source(
        source="api_client_fake",
        region="west",
        api_sports_client=ApiSportsClient(
            fake_response=load_fixture("api_sports_fixtures_west_sample.json"),
        ),
        odds_api_client=OddsApiClient(
            fake_response=load_fixture("odds_api_events_west_sample.json"),
        ),
    )

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "west"
    assert report_input.games[0].market_probability.implied_probability == pytest.approx(0.5714)


def test_region_mismatch_fails_clearly() -> None:
    with pytest.raises(
        SourceSelectorError,
        match=re.escape(
            "Requested region does not match selected ReportInput source: expected west, got east."
        ),
    ):
        load_report_input_for_source(
            source="input_file",
            region="west",
            input_file=PROJECT_ROOT / "tests" / "fixtures" / "sample_report_input_east.json",
        )


def test_missing_odds_remain_explicit() -> None:
    report_input = load_report_input_for_source(
        source="api_client_fake",
        region="east",
        api_sports_client=ApiSportsClient(
            fake_response=load_fixture("api_sports_fixtures_sample.json"),
        ),
    )

    assert all(game.market_probability.implied_probability is None for game in report_input.games)
    assert all(game.data_quality.odds_status == "missing" for game in report_input.games)
    assert all(game.market_probability.missing_data for game in report_input.games)


def test_fake_mode_does_not_require_api_keys() -> None:
    report_input = load_report_input_for_source(
        source="api_client_fake",
        region="west",
        api_sports_client=ApiSportsClient(
            fake_response=load_fixture("api_sports_fixtures_west_sample.json"),
        ),
        odds_api_client=OddsApiClient(
            fake_response=load_fixture("odds_api_events_west_sample.json"),
        ),
    )

    assert report_input.region == "west"


def test_mock_source_preserves_existing_behavior() -> None:
    report_input = load_report_input_for_source(source="mock", region="east")

    assert report_input.region == "east"
    assert report_input.mode == "mock"
    assert len(report_input.games) == 4


def test_input_file_source_preserves_existing_behavior() -> None:
    report_input = load_report_input_for_source(
        source="input_file",
        region="east",
        input_file=PROJECT_ROOT / "tests" / "fixtures" / "sample_report_input_east.json",
    )

    assert report_input.region == "east"
    assert len(report_input.games) == 4


def test_fixture_source_preserves_existing_behavior() -> None:
    report_input = load_report_input_for_source(
        source="fixture",
        region="west",
        fixtures_file=PROJECT_ROOT / "tests" / "fixtures" / "api_sports_fixtures_west_sample.json",
        odds_file=PROJECT_ROOT / "tests" / "fixtures" / "odds_api_events_west_sample.json",
    )

    assert report_input.region == "west"
    assert len(report_input.games) == 2
    assert report_input.games[0].market_probability.implied_probability == pytest.approx(0.5714)


def test_live_source_with_explicit_opt_in_still_fails_before_network_without_api_key() -> None:
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called before API key validation.")

    api_sports_client = ApiSportsClient(
        base_url="https://example.invalid",
        transport=raising_transport,
    )

    with pytest.raises(
        LiveApiConfigurationError,
        match=re.escape("API-Sports live mode requires an explicit API key."),
    ):
        load_report_input_for_source(
            source="live",
            region="east",
            api_sports_client=api_sports_client,
            allow_live=True,
        )

    assert transport_called is False


def test_source_selector_does_not_contain_hardcoded_secret_looking_values() -> None:
    selector_source = (PROJECT_ROOT / "src" / "collectors" / "source_selector.py").read_text(
        encoding="utf-8"
    )
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, selector_source) is None
