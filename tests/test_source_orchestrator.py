from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors import source_orchestrator as source_orchestrator_module  # noqa: E402
from src.collectors.api_clients import (  # noqa: E402
    ApiSportsClient,
    LiveApiConfigurationError,
    OddsApiClient,
)
from src.collectors.source_orchestrator import (  # noqa: E402
    ReportSlotSourcePlan,
    ReportSourceConfig,
    SourceOrchestratorError,
    build_report_slot_plan,
    build_report_slot_plan_from_config,
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


def test_asia_day_preview_resolves_expected_sources() -> None:
    plan = build_report_slot_plan("asia_day_preview")

    assert isinstance(plan, ReportSlotSourcePlan)
    assert plan.report_slot == "asia_day_preview"
    assert "baseball_kbo" in plan.enabled_league_keys
    assert "baseball_npb" in plan.enabled_league_keys
    assert "soccer_korea_kleague1" in plan.enabled_league_keys
    assert "soccer_japan_j_league" in plan.enabled_league_keys
    assert set(plan.sports_included) == {"baseball", "soccer"}
    assert plan.primary_odds_sources == ("The Odds API",)


def test_global_night_preview_resolves_expected_sources() -> None:
    plan = build_report_slot_plan("global_night_preview")

    assert plan.report_slot == "global_night_preview"
    assert "baseball_mlb" in plan.enabled_league_keys
    assert "basketball_nba" in plan.enabled_league_keys
    assert "soccer_epl" in plan.enabled_league_keys
    assert "soccer_uefa_champs_league" in plan.enabled_league_keys
    assert {"baseball", "basketball", "soccer"} <= set(plan.sports_included)


def test_asia_day_preview_delivery_time_is_0100_kst() -> None:
    plan = build_report_slot_plan("asia_day_preview")
    assert plan.delivery_time_kst == "01:00 KST"


def test_global_night_preview_delivery_time_is_1300_kst() -> None:
    plan = build_report_slot_plan("global_night_preview")
    assert plan.delivery_time_kst == "13:00 KST"


def test_unknown_report_slot_fails_clearly() -> None:
    with pytest.raises(SourceOrchestratorError, match=re.escape("Unknown report_slot")):
        build_report_slot_plan("overnight_preview")


def test_report_slot_plan_can_be_built_from_config() -> None:
    config = ReportSourceConfig(
        source="mock",
        region="east",
        report_slot="asia_day_preview",
    )

    plan = build_report_slot_plan_from_config(config)

    assert plan.report_slot == "asia_day_preview"
    assert "baseball_kbo" in plan.enabled_league_keys


def test_report_slot_plan_from_config_requires_report_slot() -> None:
    config = ReportSourceConfig(source="mock", region="east")

    with pytest.raises(
        SourceOrchestratorError,
        match=re.escape("config.report_slot is required for report slot planning."),
    ):
        build_report_slot_plan_from_config(config)


def test_report_slot_resolution_does_not_require_api_keys() -> None:
    plan = build_report_slot_plan("global_night_preview")

    assert plan.primary_odds_sources == ("The Odds API",)
    assert plan.secondary_schedule_source_candidates


def test_report_slot_resolution_does_not_call_source_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader_called = False

    def raising_loader(*args, **kwargs):
        nonlocal loader_called
        loader_called = True
        raise AssertionError("Report slot planning should not call source loading.")

    monkeypatch.setattr(
        source_orchestrator_module,
        "load_report_input_for_source",
        raising_loader,
    )

    plan = build_report_slot_plan("asia_day_preview")

    assert plan.enabled_league_keys
    assert loader_called is False


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


def test_existing_source_orchestrator_behavior_still_works_without_report_slot() -> None:
    config = ReportSourceConfig(source="mock", region="east", mode="mock")

    report_input = load_report_input_from_config(config)

    assert report_input.region == "east"
    assert len(report_input.games) == 4


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


def test_github_actions_workflow_is_not_needed_for_this_layer() -> None:
    orchestrator_source = (
        PROJECT_ROOT / "src" / "collectors" / "source_orchestrator.py"
    ).read_text(encoding="utf-8")

    assert ".github/workflows" not in orchestrator_source
    assert "report.yml" not in orchestrator_source


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
