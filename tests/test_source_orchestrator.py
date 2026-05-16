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
from src.collectors.source_orchestrator import (  # noqa: E402
    ReportSourceConfig,
    SourceOrchestratorError,
    load_report_input_from_config,
    load_report_inputs_from_config,
)
from src.contracts.report_input import ReportInput  # noqa: E402


def load_fixture(filename: str):
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_unsupported_source_fails_clearly() -> None:
    config = ReportSourceConfig(source="unknown", region="east")

    with pytest.raises(
        SourceOrchestratorError,
        match=re.escape(
            "Could not orchestrate ReportInput for source 'unknown': "
            "Unsupported source. Use one of: mock, input_file, fixture, api_client_fake, live."
        ),
    ):
        load_report_input_from_config(config)


def test_live_source_fails_by_default() -> None:
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called when live is disabled by default.")

    config = ReportSourceConfig(source="live", region="east")
    api_sports_client = ApiSportsClient(
        base_url="https://example.invalid",
        transport=raising_transport,
    )

    with pytest.raises(
        SourceOrchestratorError,
        match=re.escape(
            "Could not orchestrate ReportInput for source 'live': "
            "source='live' is disabled by default. Pass allow_live=True to enable it."
        ),
    ):
        load_report_input_from_config(
            config,
            api_sports_client=api_sports_client,
        )

    assert transport_called is False


def test_allow_live_false_prevents_any_live_network_path() -> None:
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called before live opt-in.")

    config = ReportSourceConfig(source="live", region="west", allow_live=False)
    api_sports_client = ApiSportsClient(
        base_url="https://example.invalid",
        transport=raising_transport,
    )

    with pytest.raises(SourceOrchestratorError):
        load_report_input_from_config(
            config,
            api_sports_client=api_sports_client,
        )

    assert transport_called is False


def test_api_client_fake_can_route_through_the_orchestrator() -> None:
    config = ReportSourceConfig(source="api_client_fake", region="east", mode="fixture")

    report_inputs = load_report_inputs_from_config(
        config,
        api_sports_client=ApiSportsClient(
            fake_response=load_fixture("api_sports_fixtures_sample.json"),
        ),
        odds_api_client=OddsApiClient(
            fake_response=load_fixture("odds_api_events_sample.json"),
        ),
    )

    assert len(report_inputs) == 1
    assert isinstance(report_inputs[0], ReportInput)
    assert report_inputs[0].region == "east"


def test_api_client_fake_can_return_west_report_input_objects() -> None:
    config = ReportSourceConfig(source="api_client_fake", region="west", mode="fixture")

    report_input = load_report_input_from_config(
        config,
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


def test_fixture_source_can_be_represented_safely() -> None:
    config = ReportSourceConfig(
        source="fixture",
        region="west",
        mode="fixture",
        fixtures_file=PROJECT_ROOT / "tests" / "fixtures" / "api_sports_fixtures_west_sample.json",
        odds_file=PROJECT_ROOT / "tests" / "fixtures" / "odds_api_events_west_sample.json",
    )

    report_input = load_report_input_from_config(config)

    assert report_input.region == "west"
    assert len(report_input.games) == 2
    assert report_input.games[1].market_probability.implied_probability is None


def test_input_file_source_can_be_represented_safely() -> None:
    config = ReportSourceConfig(
        source="input_file",
        region="east",
        mode="mock",
        input_file=PROJECT_ROOT / "tests" / "fixtures" / "sample_report_input_east.json",
    )

    report_input = load_report_input_from_config(config)

    assert report_input.region == "east"
    assert len(report_input.games) == 4


def test_region_mismatch_fails_clearly() -> None:
    config = ReportSourceConfig(
        source="input_file",
        region="west",
        mode="mock",
        input_file=PROJECT_ROOT / "tests" / "fixtures" / "sample_report_input_east.json",
    )

    with pytest.raises(
        SourceOrchestratorError,
        match=re.escape(
            "Could not orchestrate ReportInput for source 'input_file': "
            "Requested region does not match selected ReportInput source: expected west, got east."
        ),
    ):
        load_report_input_from_config(config)


def test_missing_data_remains_explicit() -> None:
    config = ReportSourceConfig(source="api_client_fake", region="east", mode="fixture")

    report_input = load_report_input_from_config(
        config,
        api_sports_client=ApiSportsClient(
            fake_response=load_fixture("api_sports_fixtures_sample.json"),
        ),
    )

    assert all(game.market_probability.implied_probability is None for game in report_input.games)
    assert all(game.market_probability.missing_data for game in report_input.games)
    assert all(game.data_quality.odds_status == "missing" for game in report_input.games)


def test_no_api_keys_are_required_for_fake_or_local_sources() -> None:
    fake_config = ReportSourceConfig(source="api_client_fake", region="west", mode="fixture")
    file_config = ReportSourceConfig(
        source="input_file",
        region="east",
        mode="mock",
        input_file=PROJECT_ROOT / "tests" / "fixtures" / "sample_report_input_east.json",
    )

    fake_report_input = load_report_input_from_config(
        fake_config,
        api_sports_client=ApiSportsClient(
            fake_response=load_fixture("api_sports_fixtures_west_sample.json"),
        ),
        odds_api_client=OddsApiClient(
            fake_response=load_fixture("odds_api_events_west_sample.json"),
        ),
    )
    file_report_input = load_report_input_from_config(file_config)

    assert fake_report_input.region == "west"
    assert file_report_input.region == "east"


def test_live_source_with_explicit_opt_in_still_fails_before_network_without_api_key() -> None:
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called before API key validation.")

    config = ReportSourceConfig(source="live", region="east", mode="live", allow_live=True)
    api_sports_client = ApiSportsClient(
        base_url="https://example.invalid",
        transport=raising_transport,
    )

    with pytest.raises(
        LiveApiConfigurationError,
        match=re.escape("API-Sports live mode requires an explicit API key."),
    ):
        load_report_input_from_config(
            config,
            api_sports_client=api_sports_client,
        )

    assert transport_called is False


def test_run_report_is_not_needed_for_this_layer() -> None:
    orchestrator_source = (
        PROJECT_ROOT / "src" / "collectors" / "source_orchestrator.py"
    ).read_text(encoding="utf-8")

    assert "run_report" not in orchestrator_source


def test_source_orchestrator_does_not_contain_hardcoded_secret_looking_values() -> None:
    orchestrator_source = (
        PROJECT_ROOT / "src" / "collectors" / "source_orchestrator.py"
    ).read_text(encoding="utf-8")
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, orchestrator_source) is None
