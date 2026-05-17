from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import sport_sources  # noqa: E402


def test_catalog_includes_kbo_and_npb_in_asia_day_preview() -> None:
    league_keys = {
        source.league_key
        for source in sport_sources.list_sources_by_report_slot("asia_day_preview")
    }

    assert "baseball_kbo" in league_keys
    assert "baseball_npb" in league_keys


def test_catalog_includes_k_league_and_j_league_in_asia_day_preview() -> None:
    league_keys = {
        source.league_key
        for source in sport_sources.list_sources_by_report_slot("asia_day_preview")
    }

    assert "soccer_korea_kleague1" in league_keys
    assert "soccer_japan_j_league" in league_keys


def test_catalog_includes_mlb_and_nba_in_global_night_preview() -> None:
    league_keys = {
        source.league_key
        for source in sport_sources.list_sources_by_report_slot("global_night_preview")
    }

    assert "baseball_mlb" in league_keys
    assert "basketball_nba" in league_keys


def test_catalog_includes_major_european_soccer_in_global_night_preview() -> None:
    league_keys = {
        source.league_key
        for source in sport_sources.list_sources_by_report_slot("global_night_preview")
    }

    assert "soccer_epl" in league_keys
    assert "soccer_uefa_champs_league" in league_keys


def test_asia_day_preview_delivery_time_is_0100_kst() -> None:
    schedule = sport_sources.get_report_slot_schedule("asia_day_preview")
    assert schedule.delivery_time_kst == "01:00 KST"


def test_global_night_preview_delivery_time_is_1300_kst() -> None:
    schedule = sport_sources.get_report_slot_schedule("global_night_preview")
    assert schedule.delivery_time_kst == "13:00 KST"


def test_helper_functions_filter_correctly() -> None:
    east_asia_sources = sport_sources.list_sources_by_region("east_asia")
    soccer_sources = sport_sources.list_sources_by_sport("soccer")
    enabled_sources = sport_sources.list_enabled_sources()
    nba_source = sport_sources.get_source_by_league_key("basketball_nba")

    assert all(source.region_group == "east_asia" for source in east_asia_sources)
    assert {source.sport for source in soccer_sources} == {"soccer"}
    assert enabled_sources
    assert all(source.enabled for source in enabled_sources)
    assert nba_source.display_name == "NBA"


def test_unknown_report_slot_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Unknown report_slot"):
        sport_sources.list_sources_by_report_slot("overnight_preview")


def test_unknown_league_key_fails_clearly() -> None:
    with pytest.raises(KeyError) as error_info:
        sport_sources.get_source_by_league_key("soccer_unknown_league")

    assert "Unknown league_key" in str(error_info.value)


def test_secondary_sources_are_marked_as_candidates_not_required() -> None:
    for source in sport_sources.list_enabled_sources():
        assert source.primary_odds_source == "The Odds API"
        assert source.secondary_schedule_source.startswith("candidate: ")
        assert "Candidate only" in source.notes
        assert "missing" in source.missing_data_policy.lower()


def test_no_real_api_calls_are_made() -> None:
    source_text = (PROJECT_ROOT / "src" / "config" / "sport_sources.py").read_text(encoding="utf-8")
    forbidden_network_markers = [
        "requests.",
        "urlopen(",
        "http://",
        "https://",
        "socket.",
    ]

    for marker in forbidden_network_markers:
        assert marker not in source_text


def test_no_secrets_are_hardcoded() -> None:
    source_text = (PROJECT_ROOT / "src" / "config" / "sport_sources.py").read_text(encoding="utf-8")
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"https?://[^\\s\"']+[?&](?:api_?key|key|token)=",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, source_text) is None
