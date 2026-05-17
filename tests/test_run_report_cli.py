from __future__ import annotations

import importlib
import json
import re
import socket
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.api_clients import ApiSportsClient  # noqa: E402

FORBIDDEN_EXPRESSIONS = [
    "무조건",
    "필승",
    "확실",
    "100% 보장",
    "돈 걸어도 됨",
    "적중 확정",
]

REQUIRED_LABELS = [
    "강력 추천 경기",
    "고신뢰 분석 경기",
    "시장 괴리 높은 경기",
    "데이터 부족 경기",
]

UNAVAILABLE_MARKET_DISCREPANCY = "market_discrepancy_level unavailable"
MULTISPORT_ODDS_FIXTURE_PATH = (
    PROJECT_ROOT / "tests" / "fixtures" / "odds_api_multisport_events_sample.json"
)


def load_run_report_tools():
    return load_run_report_module().main


def load_run_report_module():
    return importlib.import_module("run_report")


def assert_html_has_expected_content(html: str) -> None:
    for label in REQUIRED_LABELS:
        assert label in html

    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in html


def fetch_prediction_log_summary(db_path: Path) -> tuple[str, str, str, int]:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT region, mode, analysis_mode, COUNT(*)
            FROM prediction_log
            GROUP BY region, mode, analysis_mode
            """
        ).fetchone()

    return (row[0], row[1], row[2], int(row[3]))


def get_api_sports_fixture_path(region: str = "east") -> Path:
    fixture_filename = (
        "api_sports_fixtures_west_sample.json"
        if region == "west"
        else "api_sports_fixtures_sample.json"
    )
    return PROJECT_ROOT / "tests" / "fixtures" / fixture_filename


def get_odds_fixture_path(region: str = "east") -> Path:
    fixture_filename = (
        "odds_api_events_west_sample.json" if region == "west" else "odds_api_events_sample.json"
    )
    return PROJECT_ROOT / "tests" / "fixtures" / fixture_filename


def assert_report_slot_summary(
    output_text: str,
    *,
    report_slot: str,
    compatibility_region: str,
    delivery_time_kst: str,
) -> None:
    assert "Selected report slot plan:" in output_text
    assert f"report_slot={report_slot}" in output_text
    assert f"compatibility_region={compatibility_region}" in output_text
    assert f"delivery_time_kst={delivery_time_kst}" in output_text


class RecordingFakeMailer:
    def __init__(self, expected_output_path: Path | None = None):
        self.expected_output_path = expected_output_path
        self.call_count = 0
        self.subjects: list[str] = []
        self.html_bodies: list[str] = []
        self.plain_text_bodies: list[str] = []

    def send_report(self, *, subject: str, html_content: str, plain_text_content: str):
        if self.expected_output_path is not None:
            assert self.expected_output_path.exists()
        self.call_count += 1
        self.subjects.append(subject)
        self.html_bodies.append(html_content)
        self.plain_text_bodies.append(plain_text_content)
        return 202


class RecordingFakeClient:
    def __init__(self):
        self.call_count = 0
        self.report_ids: list[str] = []
        self.prompt_snippets: list[str] = []

    def create_analysis(self, *, prompt, report_input):
        self.call_count += 1
        self.report_ids.append(report_input.report_id)
        self.prompt_snippets.append(prompt[:120])
        return build_fake_analysis_output_payload(report_input)


def build_fake_analysis_output_payload(report_input) -> dict:
    games = []
    labels = [
        "강력 추천 경기",
        "고신뢰 분석 경기",
        "시장 괴리 높은 경기",
        "데이터 부족 경기",
    ]

    for index, game in enumerate(report_input.games):
        missing_data = list(
            dict.fromkeys(
                [
                    *game.missing_data,
                    *game.market_probability.missing_data,
                    *game.reference_probability.missing_data,
                    *game.data_quality.missing_data,
                ]
            )
        )
        requires_unavailable_discrepancy = (
            game.market_probability.implied_probability is None
            or game.reference_probability.win_probability is None
        )
        if requires_unavailable_discrepancy:
            missing_data = list(dict.fromkeys([*missing_data, UNAVAILABLE_MARKET_DISCREPANCY]))
            discrepancy_level = "low"
            market_note = None
            confidence_level = "low"
        else:
            discrepancy_level = "high" if index == 2 else "low"
            market_note = (
                "The provided market and reference values are far apart."
                if discrepancy_level == "high"
                else "The provided market and reference values are closely aligned."
            )
            confidence_level = "high" if index == 0 else "medium"

        games.append(
            {
                "game_id": game.game_id,
                "label": labels[index % len(labels)],
                "confidence_level": confidence_level,
                "trust_level": game.data_quality.trust_level,
                "discrepancy_level": discrepancy_level,
                "analysis_summary": (
                    "This structured GPT sample uses only the provided input values "
                    "without adding new sports facts."
                ),
                "supporting_points": [
                    "Only provided input fields were used for this structured sample.",
                ],
                "caution_notes": [
                    "This remains a mock analysis example and not betting advice.",
                ],
                "market_note": market_note,
                "missing_data": missing_data,
            }
        )

    return {
        "report_id": report_input.report_id,
        "region": report_input.region,
        "generated_at": report_input.generated_at,
        "summary": {
            "headline": f"GPT sample summary for {report_input.region}",
            "overview": (
                "This structured GPT sample uses only provided input data and keeps missing "
                "data explicit."
            ),
            "confidence_level": "low",
            "trust_level": "medium",
            "discrepancy_level": "high",
            "key_points": [
                "Each required label appears at least once in this fake GPT response.",
                "Missing market discrepancy is called out explicitly when needed.",
            ],
            "missing_data": [
                *report_input.missing_data,
                UNAVAILABLE_MARKET_DISCREPANCY,
            ],
        },
        "games": games,
    }


def get_sample_report_input_fixture_path(region: str) -> Path:
    return PROJECT_ROOT / "tests" / "fixtures" / f"sample_report_input_{region}.json"


def write_fixture_mode_api_sports_file(tmp_path: Path, region: str) -> Path:
    first_home = "Seoul Fixture Club" if region == "east" else "New York Fixture Club"
    first_away = "Busan Fixture Club" if region == "east" else "Boston Fixture Club"
    second_home = "Tokyo Fixture Nine" if region == "east" else "London Fixture FC"
    second_away = "Osaka Fixture Nine" if region == "east" else "Liverpool Fixture FC"
    third_home = "Incheon Fixture FC" if region == "east" else "Milan Fixture Club"
    third_away = "Daegu Fixture FC" if region == "east" else "Rome Fixture Club"
    fourth_home = "Jeju Fixture XI" if region == "east" else "Madrid Fixture XI"
    fourth_away = "Sapporo Fixture XI" if region == "east" else "Munich Fixture XI"
    intro_note = "Fixture metadata only. Market and reference data are intentionally unavailable."
    fixture_payload = {
        "region": region,
        "mode": "mock",
        "generated_at": "2026-05-14 08:00 KST" if region == "east" else "2026-05-14 08:00 EDT",
        "response": [
            {
                "fixture": {
                    "id": 601001 if region == "east" else 701001,
                    "date": "2026-05-14 18:30 KST" if region == "east" else "2026-05-14 19:05 EDT",
                    "status": {"long": "Not Started"},
                },
                "league": {"name": "KBO" if region == "east" else "MLB"},
                "teams": {
                    "home": {"name": first_home},
                    "away": {"name": first_away},
                },
                "notes": [intro_note],
            },
            {
                "fixture": {
                    "id": 601002 if region == "east" else 701002,
                    "date": "2026-05-14 19:00 JST" if region == "east" else "2026-05-14 20:00 BST",
                    "status": {"long": "Not Started"},
                },
                "league": {"name": "NPB" if region == "east" else "EPL"},
                "teams": {
                    "home": {"name": second_home},
                    "away": {"name": second_away},
                },
                "notes": ["Second fixture sample for CLI fixture mode coverage."],
            },
            {
                "fixture": {
                    "id": 601003 if region == "east" else 701003,
                    "date": "2026-05-14 19:30 KST" if region == "east" else "2026-05-14 20:45 CEST",
                    "status": {"long": "Not Started"},
                },
                "league": {"name": "K League" if region == "east" else "Serie A"},
                "teams": {
                    "home": {"name": third_home},
                    "away": {"name": third_away},
                },
                "notes": ["Third fixture sample for multi-label rendering."],
            },
            {
                "fixture": {
                    "id": 601004 if region == "east" else 701004,
                    "date": "2026-05-14 20:00 KST" if region == "east" else "2026-05-14 21:00 CEST",
                    "status": {"long": "Not Started"},
                },
                "league": {"name": "East Regional Cup" if region == "east" else "UCL"},
                "teams": {
                    "home": {"name": fourth_home},
                    "away": {"name": fourth_away},
                },
                "notes": ["Fourth fixture sample for data-shortage coverage."],
            },
        ],
    }
    output_path = tmp_path / f"fixture_mode_api_sports_{region}.json"
    output_path.write_text(
        json.dumps(fixture_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def write_fixture_mode_odds_file(tmp_path: Path, region: str) -> Path:
    first_home = "Seoul Fixture Club" if region == "east" else "New York Fixture Club"
    first_away = "Busan Fixture Club" if region == "east" else "Boston Fixture Club"
    odds_payload = {
        "events": [
            {
                "id": f"{region}-odds-event-001",
                "sport_key": "baseball_kbo" if region == "east" else "baseball_mlb",
                "sport_title": "KBO" if region == "east" else "MLB",
                "commence_time": "2026-05-14T09:30:00Z",
                "home_team": first_home,
                "away_team": first_away,
                "bookmakers": [
                    {
                        "title": "SampleBook",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {
                                        "name": first_home,
                                        "price": 1.8,
                                    },
                                    {
                                        "name": first_away,
                                        "price": 2.1,
                                    },
                                ],
                            }
                        ],
                    }
                ],
            },
            {
                "id": f"{region}-odds-event-002",
                "sport_key": "soccer_kleague" if region == "east" else "soccer_epl",
                "sport_title": "K League" if region == "east" else "EPL",
                "commence_time": "2026-05-14T10:00:00Z",
                "home_team": "Unmatched Odds Home",
                "away_team": "Unmatched Odds Away",
                "bookmakers": [],
            },
        ]
    }
    output_path = tmp_path / f"fixture_mode_odds_{region}.json"
    output_path.write_text(
        json.dumps(odds_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def test_help_includes_report_slot() -> None:
    run_report_module = load_run_report_module()

    help_text = run_report_module.build_parser().format_help()

    assert "--report-slot" in help_text
    assert "asia_day_preview" in help_text
    assert "global_night_preview" in help_text


def test_help_includes_multisport_odds_file_and_sport_key() -> None:
    run_report_module = load_run_report_module()

    help_text = run_report_module.build_parser().format_help()

    assert "--multisport-odds-file" in help_text
    assert "--sport-key" in help_text


def test_report_slot_asia_day_preview_derives_region_east_when_omitted(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--report-slot", "asia_day_preview", "--mode", "mock"])

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert_report_slot_summary(
        captured.out,
        report_slot="asia_day_preview",
        compatibility_region="east",
        delivery_time_kst="01:00 KST",
    )


def test_report_slot_global_night_preview_derives_region_west_when_omitted(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--report-slot", "global_night_preview", "--mode", "mock"])

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert_report_slot_summary(
        captured.out,
        report_slot="global_night_preview",
        compatibility_region="west",
        delivery_time_kst="13:00 KST",
    )


def test_report_slot_asia_day_preview_with_region_east_is_allowed(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--report-slot",
            "asia_day_preview",
            "--region",
            "east",
            "--mode",
            "mock",
        ]
    )

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_east.html"

    assert exit_code == 0
    assert output_path.exists()
    assert "report_slot=asia_day_preview" in captured.out


def test_report_slot_global_night_preview_with_region_west_is_allowed(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--report-slot",
            "global_night_preview",
            "--region",
            "west",
            "--mode",
            "mock",
        ]
    )

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_west.html"

    assert exit_code == 0
    assert output_path.exists()
    assert "report_slot=global_night_preview" in captured.out


def test_multisport_odds_file_works_with_global_night_preview_and_save(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("API_SPORTS_KEY", raising=False)
    monkeypatch.delenv("ODDS_API_KEY", raising=False)

    def fail_on_network(*args, **kwargs):
        raise AssertionError("External network access should not be used.")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)
    db_path = tmp_path / "data" / "multisport_west.sqlite"

    exit_code = main(
        [
            "--report-slot",
            "global_night_preview",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--analysis",
            "fallback",
            "--save",
            "--db-path",
            str(db_path),
        ]
    )

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert db_path.exists()
    assert "report_slot=global_night_preview" in captured.out
    assert "compatibility_region=west" in captured.out
    assert "Auto-selected sport keys for report_slot global_night_preview:" in captured.out
    assert "London Sample FC" in html
    assert "New York Sample Club" in html
    assert "LA Sample Hoops" in html
    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in html
    assert fetch_prediction_log_summary(db_path) == ("west", "fixture", "fallback", 3)


def test_multisport_odds_file_with_single_sport_key_creates_only_matching_games(
    tmp_path, monkeypatch
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "data" / "multisport_single_sport.sqlite"

    exit_code = main(
        [
            "--report-slot",
            "global_night_preview",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--sport-key",
            "baseball_mlb",
            "--analysis",
            "fallback",
            "--save",
            "--db-path",
            str(db_path),
        ]
    )

    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert "New York Sample Club" in html
    assert "London Sample FC" not in html
    assert "LA Sample Hoops" not in html
    assert fetch_prediction_log_summary(db_path) == ("west", "fixture", "fallback", 1)


def test_multisport_odds_file_works_with_asia_day_preview(tmp_path, monkeypatch, capsys) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "data" / "multisport_east.sqlite"

    exit_code = main(
        [
            "--report-slot",
            "asia_day_preview",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--analysis",
            "fallback",
            "--save",
            "--db-path",
            str(db_path),
        ]
    )

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert "report_slot=asia_day_preview" in captured.out
    assert "compatibility_region=east" in captured.out
    assert "Auto-selected sport keys for report_slot asia_day_preview:" in captured.out
    assert "Tokyo Sample Nine" in html
    assert "Seoul Sample FC" in html
    assert fetch_prediction_log_summary(db_path) == ("east", "fixture", "fallback", 2)


def test_multisport_odds_file_with_global_slot_auto_derives_catalog_sport_keys(
    tmp_path, monkeypatch, capsys
) -> None:
    run_report_module = load_run_report_module()
    monkeypatch.chdir(tmp_path)
    seen_sport_keys = []
    original_loader = run_report_module.load_report_input_from_multisport_odds_file

    def recording_loader(*, odds_fixture_path, region=None, sport_keys=None):
        seen_sport_keys.append(list(sport_keys) if sport_keys is not None else None)
        return original_loader(
            odds_fixture_path=odds_fixture_path,
            region=region,
            sport_keys=sport_keys,
        )

    monkeypatch.setattr(
        run_report_module,
        "load_report_input_from_multisport_odds_file",
        recording_loader,
    )

    exit_code = run_report_module.main(
        [
            "--report-slot",
            "global_night_preview",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert seen_sport_keys == [
        [
            "baseball_mlb",
            "basketball_nba",
            "soccer_epl",
            "soccer_spain_la_liga",
            "soccer_italy_serie_a",
            "soccer_germany_bundesliga",
            "soccer_uefa_champs_league",
        ]
    ]
    assert "Auto-selected sport keys for report_slot global_night_preview:" in captured.out
    assert "baseball_mlb" in captured.out
    assert "basketball_nba" in captured.out
    assert "soccer_epl" in captured.out


def test_multisport_odds_file_with_asia_slot_auto_derives_catalog_sport_keys(
    tmp_path, monkeypatch, capsys
) -> None:
    run_report_module = load_run_report_module()
    monkeypatch.chdir(tmp_path)
    seen_sport_keys = []
    original_loader = run_report_module.load_report_input_from_multisport_odds_file

    def recording_loader(*, odds_fixture_path, region=None, sport_keys=None):
        seen_sport_keys.append(list(sport_keys) if sport_keys is not None else None)
        return original_loader(
            odds_fixture_path=odds_fixture_path,
            region=region,
            sport_keys=sport_keys,
        )

    monkeypatch.setattr(
        run_report_module,
        "load_report_input_from_multisport_odds_file",
        recording_loader,
    )

    exit_code = run_report_module.main(
        [
            "--report-slot",
            "asia_day_preview",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert seen_sport_keys == [
        [
            "baseball_kbo",
            "baseball_npb",
            "soccer_korea_kleague1",
            "soccer_japan_j_league",
        ]
    ]
    assert "Auto-selected sport keys for report_slot asia_day_preview:" in captured.out
    assert "baseball_kbo" in captured.out
    assert "baseball_npb" in captured.out
    assert "soccer_korea_kleague1" in captured.out
    assert "soccer_japan_j_league" in captured.out


def test_multisport_odds_file_with_explicit_compatible_region_is_allowed(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--report-slot",
            "global_night_preview",
            "--region",
            "west",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_west.html"

    assert exit_code == 0
    assert output_path.exists()
    assert "report_slot=global_night_preview" in captured.out


def test_explicit_global_sport_key_baseball_mlb_remains_allowed(
    tmp_path, monkeypatch, capsys
) -> None:
    run_report_module = load_run_report_module()
    monkeypatch.chdir(tmp_path)
    seen_sport_keys = []
    original_loader = run_report_module.load_report_input_from_multisport_odds_file

    def recording_loader(*, odds_fixture_path, region=None, sport_keys=None):
        seen_sport_keys.append(list(sport_keys) if sport_keys is not None else None)
        return original_loader(
            odds_fixture_path=odds_fixture_path,
            region=region,
            sport_keys=sport_keys,
        )

    monkeypatch.setattr(
        run_report_module,
        "load_report_input_from_multisport_odds_file",
        recording_loader,
    )

    exit_code = run_report_module.main(
        [
            "--report-slot",
            "global_night_preview",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--sport-key",
            "baseball_mlb",
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert seen_sport_keys == [["baseball_mlb"]]
    assert "Auto-selected sport keys" not in captured.out


def test_repeated_sport_key_values_are_preserved(tmp_path, monkeypatch) -> None:
    run_report_module = load_run_report_module()
    monkeypatch.chdir(tmp_path)
    seen_sport_keys = []
    original_loader = run_report_module.load_report_input_from_multisport_odds_file

    def recording_loader(*, odds_fixture_path, region=None, sport_keys=None):
        seen_sport_keys.append(list(sport_keys) if sport_keys is not None else None)
        return original_loader(
            odds_fixture_path=odds_fixture_path,
            region=region,
            sport_keys=sport_keys,
        )

    monkeypatch.setattr(
        run_report_module,
        "load_report_input_from_multisport_odds_file",
        recording_loader,
    )

    exit_code = run_report_module.main(
        [
            "--report-slot",
            "global_night_preview",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--sport-key",
            "baseball_mlb",
            "--sport-key",
            "baseball_mlb",
            "--analysis",
            "fallback",
        ]
    )

    assert exit_code == 0
    assert seen_sport_keys == [["baseball_mlb", "baseball_mlb"]]


def test_explicit_baseball_mlb_fails_clearly_for_asia_day_preview(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--report-slot",
            "asia_day_preview",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--sport-key",
            "baseball_mlb",
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "--sport-key baseball_mlb is not enabled for --report-slot asia_day_preview." in (
        captured.out
    )


def test_multisport_odds_file_with_conflicting_report_slot_and_region_fails_clearly(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--report-slot",
            "asia_day_preview",
            "--region",
            "west",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "only compatible with --region east" in captured.out


def test_multisport_odds_file_with_input_file_fails_clearly(tmp_path, monkeypatch, capsys) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    input_path = get_sample_report_input_fixture_path("east")

    exit_code = main(
        [
            "--region",
            "east",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--input-file",
            str(input_path),
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "--multisport-odds-file cannot be used together with --input-file." in captured.out


def test_multisport_odds_file_with_fixture_paths_fails_clearly(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    fixtures_path = get_api_sports_fixture_path("east")
    odds_path = get_odds_fixture_path("east")

    exit_code = main(
        [
            "--region",
            "east",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--fixtures-file",
            str(fixtures_path),
            "--odds-file",
            str(odds_path),
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert (
        "--multisport-odds-file cannot be used together with --fixtures-file or --odds-file."
        in captured.out
    )


def test_region_only_multisport_odds_file_preserves_existing_behavior(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--region",
            "west",
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert "New York Sample Club" in html
    assert "London Sample FC" in html
    assert "LA Sample Hoops" in html
    assert "Auto-selected sport keys" not in captured.out


def test_multisport_odds_file_without_region_or_report_slot_fails_clearly(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--mode",
            "fixture",
            "--multisport-odds-file",
            str(MULTISPORT_ODDS_FIXTURE_PATH),
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Either --region or --report-slot is required." in captured.out


def test_unknown_report_slot_fails_clearly(tmp_path, monkeypatch, capsys) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--report-slot", "overnight_preview", "--mode", "mock"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Report generation failed:" in captured.out
    assert "Unknown report_slot" in captured.out


def test_report_slot_asia_day_preview_with_region_west_fails_clearly(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--report-slot",
            "asia_day_preview",
            "--region",
            "west",
            "--mode",
            "mock",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "only compatible with --region east" in captured.out


def test_report_slot_global_night_preview_with_region_east_fails_clearly(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--report-slot",
            "global_night_preview",
            "--region",
            "east",
            "--mode",
            "mock",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "only compatible with --region west" in captured.out


def test_existing_mock_command_still_works_for_east(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--region", "east", "--mode", "mock"])

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_existing_mock_command_still_works_for_west(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--region", "west", "--mode", "mock"])

    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_fallback_analysis_works_for_east(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--region", "east", "--mode", "mock", "--analysis", "fallback"])

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_fallback_analysis_works_for_west(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--region", "west", "--mode", "mock", "--analysis", "fallback"])

    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_input_file_east_sample_works_with_fallback_analysis(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    input_path = get_sample_report_input_fixture_path("east")

    exit_code = main(
        [
            "--region",
            "east",
            "--mode",
            "mock",
            "--analysis",
            "fallback",
            "--input-file",
            str(input_path),
        ]
    )

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_input_file_west_sample_works_with_fallback_analysis(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    input_path = get_sample_report_input_fixture_path("west")

    exit_code = main(
        [
            "--region",
            "west",
            "--mode",
            "mock",
            "--analysis",
            "fallback",
            "--input-file",
            str(input_path),
        ]
    )

    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_fixture_mode_works_for_east_with_api_sports_fixture_and_odds_fixture(
    tmp_path, monkeypatch
) -> None:
    main = load_run_report_tools()
    fake_client = RecordingFakeClient()
    monkeypatch.chdir(tmp_path)
    fixtures_path = write_fixture_mode_api_sports_file(tmp_path, "east")
    odds_path = write_fixture_mode_odds_file(tmp_path, "east")

    exit_code = main(
        [
            "--region",
            "east",
            "--mode",
            "fixture",
            "--analysis",
            "gpt",
            "--fixtures-file",
            str(fixtures_path),
            "--odds-file",
            str(odds_path),
        ],
        gpt_client=fake_client,
    )

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert fake_client.call_count == 1


def test_fixture_mode_works_for_west_with_api_sports_fixture_and_odds_fixture(
    tmp_path, monkeypatch
) -> None:
    main = load_run_report_tools()
    fake_client = RecordingFakeClient()
    monkeypatch.chdir(tmp_path)
    fixtures_path = write_fixture_mode_api_sports_file(tmp_path, "west")
    odds_path = write_fixture_mode_odds_file(tmp_path, "west")

    exit_code = main(
        [
            "--region",
            "west",
            "--mode",
            "fixture",
            "--analysis",
            "gpt",
            "--fixtures-file",
            str(fixtures_path),
            "--odds-file",
            str(odds_path),
        ],
        gpt_client=fake_client,
    )

    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert fake_client.call_count == 1


def test_gpt_analysis_works_with_fake_response(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    fake_client = RecordingFakeClient()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        ["--region", "east", "--mode", "mock", "--analysis", "gpt"],
        gpt_client=fake_client,
    )

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert fake_client.call_count == 1


def test_gpt_analysis_uses_fake_client_without_real_api(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    fake_client = RecordingFakeClient()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main(
        ["--region", "west", "--mode", "mock", "--analysis", "gpt"],
        gpt_client=fake_client,
    )

    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert fake_client.call_count == 1
    assert fake_client.report_ids == ["mock-west-2026-05-13"]


def test_invalid_input_file_path_fails_clearly(tmp_path, monkeypatch, capsys) -> None:
    main = load_run_report_tools()
    missing_input_path = tmp_path / "missing_report_input.json"
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--region",
            "east",
            "--mode",
            "mock",
            "--analysis",
            "fallback",
            "--input-file",
            str(missing_input_path),
        ]
    )

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_east.html"

    assert exit_code == 1
    assert "Report generation failed:" in captured.out
    assert "Could not read local ReportInput JSON file" in captured.out
    assert not output_path.exists()


def test_cli_uses_source_orchestrator_for_safe_source_loading(tmp_path, monkeypatch) -> None:
    run_report_module = load_run_report_module()
    monkeypatch.chdir(tmp_path)
    seen_configs = []
    original_loader = run_report_module.load_report_input_from_config

    def recording_loader(config, **kwargs):
        seen_configs.append(config)
        return original_loader(config, **kwargs)

    monkeypatch.setattr(run_report_module, "load_report_input_from_config", recording_loader)

    exit_code = run_report_module.main(
        ["--region", "east", "--mode", "mock", "--analysis", "fallback"]
    )

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert len(seen_configs) == 1
    assert seen_configs[0].source == "mock"
    assert seen_configs[0].allow_live is False


def test_report_slot_uses_source_orchestrator_plan_and_safe_mock_loading(
    tmp_path, monkeypatch, capsys
) -> None:
    run_report_module = load_run_report_module()
    monkeypatch.chdir(tmp_path)
    seen_slots = []
    seen_configs = []
    original_plan_builder = run_report_module.build_report_slot_plan
    original_loader = run_report_module.load_report_input_from_config

    def recording_plan_builder(report_slot):
        seen_slots.append(report_slot)
        return original_plan_builder(report_slot)

    def recording_loader(config, **kwargs):
        seen_configs.append(config)
        return original_loader(config, **kwargs)

    monkeypatch.setattr(run_report_module, "build_report_slot_plan", recording_plan_builder)
    monkeypatch.setattr(run_report_module, "load_report_input_from_config", recording_loader)

    exit_code = run_report_module.main(
        ["--report-slot", "asia_day_preview", "--mode", "mock", "--analysis", "fallback"]
    )

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert seen_slots == ["asia_day_preview"]
    assert len(seen_configs) == 1
    assert seen_configs[0].region == "east"
    assert seen_configs[0].source == "mock"
    assert seen_configs[0].allow_live is False
    assert "report_slot=asia_day_preview" in captured.out


def test_fixture_mode_fails_clearly_when_fixtures_file_is_missing(
    tmp_path, monkeypatch, capsys
) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--region",
            "east",
            "--mode",
            "fixture",
            "--analysis",
            "fallback",
        ]
    )

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_east.html"

    assert exit_code == 1
    assert "Report generation failed:" in captured.out
    assert "--fixtures-file is required when --mode fixture is used." in captured.out
    assert not output_path.exists()


def test_internal_live_source_remains_blocked_before_any_network_call() -> None:
    run_report_module = load_run_report_module()
    transport_called = False

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called when live source is blocked.")

    api_sports_client = ApiSportsClient(
        base_url="https://example.invalid",
        transport=raising_transport,
    )

    with pytest.raises(
        run_report_module.ReportInputSelectionError,
        match="source='live' is disabled by default",
    ):
        run_report_module._load_report_input_for_cli(
            region="east",
            mode="mock",
            source_override="live",
            api_sports_client=api_sports_client,
        )

    assert transport_called is False


def test_report_slot_resolution_does_not_require_api_keys(tmp_path, monkeypatch, capsys) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("API_SPORTS_KEY", raising=False)
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main(
        ["--report-slot", "global_night_preview", "--mode", "mock", "--analysis", "fallback"]
    )

    captured = capsys.readouterr()
    output_path = tmp_path / "out" / "report_west.html"

    assert exit_code == 0
    assert output_path.exists()
    assert "report_slot=global_night_preview" in captured.out


def test_fixture_mode_handles_missing_odds_file_without_inventing_market_probability(
    tmp_path, monkeypatch
) -> None:
    main = load_run_report_tools()
    fake_client = RecordingFakeClient()
    monkeypatch.chdir(tmp_path)
    fixtures_path = write_fixture_mode_api_sports_file(tmp_path, "east")

    exit_code = main(
        [
            "--region",
            "east",
            "--mode",
            "fixture",
            "--analysis",
            "gpt",
            "--fixtures-file",
            str(fixtures_path),
        ],
        gpt_client=fake_client,
    )

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert_html_has_expected_content(html)
    assert "API-Sports fixture sample does not include odds data." in html


def test_send_flag_generates_html_before_trying_to_send(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    expected_output_path = tmp_path / "out" / "report_east.html"
    fake_mailer = RecordingFakeMailer(expected_output_path=expected_output_path)

    exit_code = main(
        ["--region", "east", "--mode", "mock", "--send"],
        mailer=fake_mailer,
    )

    html = expected_output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert expected_output_path.exists()
    assert fake_mailer.call_count == 1
    assert_html_has_expected_content(html)
    assert "Region:" in fake_mailer.plain_text_bodies[0]


def test_save_flag_writes_to_a_test_safe_temporary_db_path(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "data" / "test_sports_agent.sqlite"

    exit_code = main(
        [
            "--region",
            "east",
            "--mode",
            "mock",
            "--analysis",
            "fallback",
            "--save",
            "--db-path",
            str(db_path),
        ]
    )

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert db_path.exists()
    assert_html_has_expected_content(html)

    with sqlite3.connect(db_path) as connection:
        row_count = connection.execute("SELECT COUNT(*) FROM prediction_log").fetchone()[0]
        labels = {
            row[0]
            for row in connection.execute("SELECT label FROM prediction_log ORDER BY game_id")
        }

    assert row_count == 4
    assert labels == set(REQUIRED_LABELS)
    assert fetch_prediction_log_summary(db_path) == ("east", "mock", "fallback", 4)


def test_fixture_mode_save_uses_fixture_mode_in_prediction_log(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "data" / "fixture_mode_sports_agent.sqlite"
    fixtures_path = get_api_sports_fixture_path("east")
    odds_path = get_odds_fixture_path("east")

    exit_code = main(
        [
            "--region",
            "east",
            "--mode",
            "fixture",
            "--analysis",
            "fallback",
            "--fixtures-file",
            str(fixtures_path),
            "--odds-file",
            str(odds_path),
            "--save",
            "--db-path",
            str(db_path),
        ]
    )

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert db_path.exists()
    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in html
    assert fetch_prediction_log_summary(db_path) == ("east", "fixture", "fallback", 2)


def test_west_fixture_mode_save_uses_fixture_mode_in_prediction_log(tmp_path, monkeypatch) -> None:
    main = load_run_report_tools()
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "data" / "fixture_mode_west_sports_agent.sqlite"
    fixtures_path = get_api_sports_fixture_path("west")
    odds_path = get_odds_fixture_path("west")

    exit_code = main(
        [
            "--region",
            "west",
            "--mode",
            "fixture",
            "--analysis",
            "fallback",
            "--fixtures-file",
            str(fixtures_path),
            "--odds-file",
            str(odds_path),
            "--save",
            "--db-path",
            str(db_path),
        ]
    )

    output_path = tmp_path / "out" / "report_west.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert db_path.exists()
    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in html
    assert fetch_prediction_log_summary(db_path) == ("west", "fixture", "fallback", 2)


def test_sqlite_failure_does_not_delete_generated_html(tmp_path, monkeypatch) -> None:
    run_report_module = load_run_report_module()
    monkeypatch.chdir(tmp_path)

    def raise_sqlite_error(*args, **kwargs):
        raise run_report_module.PredictionLogError("simulated SQLite write failure")

    monkeypatch.setattr(run_report_module, "save_prediction_log", raise_sqlite_error)

    exit_code = run_report_module.main(
        [
            "--region",
            "east",
            "--mode",
            "mock",
            "--analysis",
            "fallback",
            "--save",
            "--db-path",
            str(tmp_path / "data" / "broken.sqlite"),
        ]
    )

    output_path = tmp_path / "out" / "report_east.html"
    html = output_path.read_text(encoding="utf-8")

    assert exit_code == 1
    assert output_path.exists()
    assert_html_has_expected_content(html)


def test_run_report_does_not_contain_hardcoded_secret_looking_values() -> None:
    run_report_source = (PROJECT_ROOT / "run_report.py").read_text(encoding="utf-8")
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, run_report_source) is None


def test_workflow_file_remains_on_report_slot_schedule() -> None:
    workflow_text = (PROJECT_ROOT / ".github" / "workflows" / "report.yml").read_text(
        encoding="utf-8"
    )

    assert 'cron: "0 16 * * *"' in workflow_text
    assert 'cron: "0 4 * * *"' in workflow_text
    assert "report_slot:" in workflow_text


def test_sport_sources_catalog_file_remains_report_slot_based() -> None:
    catalog_text = (PROJECT_ROOT / "src" / "config" / "sport_sources.py").read_text(
        encoding="utf-8"
    )

    assert "asia_day_preview" in catalog_text
    assert "global_night_preview" in catalog_text
    assert "baseball_kbo" in catalog_text
    assert "soccer_uefa_champs_league" in catalog_text
