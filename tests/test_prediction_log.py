from __future__ import annotations

import importlib
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_prediction_log_module():
    return importlib.import_module("src.evaluation.prediction_log")


def fetch_row_count(db_path: Path) -> int:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT COUNT(*) FROM prediction_log").fetchone()
    return int(row[0])


def test_init_db_creates_the_prediction_log_table(tmp_path) -> None:
    module = load_prediction_log_module()
    db_path = tmp_path / "logs" / "sports_agent.sqlite"

    created_path = module.init_db(db_path)

    assert created_path == db_path
    assert db_path.exists()

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'prediction_log'
            """
        ).fetchone()

    assert row == ("prediction_log",)


def test_save_prediction_log_inserts_rows(tmp_path) -> None:
    module = load_prediction_log_module()
    db_path = tmp_path / "logs" / "sports_agent.sqlite"

    inserted = module.save_prediction_log(
        db_path,
        report_time_kst="2026-05-13 21:00 KST",
        region="east",
        mode="mock",
        analysis_mode="fallback",
        game_id="east-kbo-001",
        label="강력 추천 경기",
        data_trust_level="high",
        prediction_confidence_level="high",
        market_discrepancy_level="low",
        recommended_side=None,
        summary="Stored fallback summary for a safe mock example.",
        input_snapshot_json=json.dumps({"game_id": "east-kbo-001"}, ensure_ascii=False),
        analysis_output_json=json.dumps(
            {"game_id": "east-kbo-001", "label": "강력 추천 경기"},
            ensure_ascii=False,
        ),
    )

    assert inserted is True
    assert fetch_row_count(db_path) == 1

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT report_time_kst, region, analysis_mode, game_id, label
            FROM prediction_log
            """
        ).fetchone()

    assert row == (
        "2026-05-13 21:00 KST",
        "east",
        "fallback",
        "east-kbo-001",
        "강력 추천 경기",
    )


def test_duplicate_report_time_and_game_id_is_not_inserted_twice(tmp_path) -> None:
    module = load_prediction_log_module()
    db_path = tmp_path / "logs" / "sports_agent.sqlite"
    row_payload = {
        "report_time_kst": "2026-05-13 09:00 EDT",
        "region": "west",
        "mode": "mock",
        "analysis_mode": "gpt",
        "game_id": "west-mlb-001",
        "label": "강력 추천 경기",
        "data_trust_level": "high",
        "prediction_confidence_level": "medium",
        "market_discrepancy_level": "low",
        "recommended_side": None,
        "summary": "Duplicate prevention should keep this row unique.",
        "input_snapshot_json": json.dumps({"game_id": "west-mlb-001"}, ensure_ascii=False),
        "analysis_output_json": json.dumps(
            {"game_id": "west-mlb-001", "label": "강력 추천 경기"},
            ensure_ascii=False,
        ),
    }

    first_inserted = module.save_prediction_log(db_path, **row_payload)
    second_inserted = module.save_prediction_log(db_path, **row_payload)

    assert first_inserted is True
    assert second_inserted is False
    assert fetch_row_count(db_path) == 1

    with sqlite3.connect(db_path) as connection:
        stored_report_time = connection.execute(
            "SELECT report_time_kst FROM prediction_log WHERE game_id = ?",
            ("west-mlb-001",),
        ).fetchone()[0]

    assert stored_report_time == "2026-05-13 22:00 KST"


def test_missing_data_can_be_stored(tmp_path) -> None:
    module = load_prediction_log_module()
    db_path = tmp_path / "logs" / "sports_agent.sqlite"
    missing_input = {
        "game_id": "west-ucl-004",
        "missing_data": ["market note missing", "lineup input missing"],
    }
    missing_analysis = {
        "game_id": "west-ucl-004",
        "missing_data": [
            "market_discrepancy_level unavailable",
            "recent trend summary missing",
        ],
    }

    inserted = module.save_prediction_log(
        db_path,
        report_time_kst="2026-05-13 09:00 EDT",
        region="west",
        mode="mock",
        analysis_mode="fallback",
        game_id="west-ucl-004",
        label="데이터 부족 경기",
        data_trust_level="low",
        prediction_confidence_level="low",
        market_discrepancy_level="low",
        recommended_side=None,
        summary="Missing data stays explicit in the stored payload.",
        input_snapshot_json=json.dumps(missing_input, ensure_ascii=False),
        analysis_output_json=json.dumps(missing_analysis, ensure_ascii=False),
    )

    assert inserted is True

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT input_snapshot_json, analysis_output_json
            FROM prediction_log
            WHERE game_id = ?
            """,
            ("west-ucl-004",),
        ).fetchone()

    stored_input = json.loads(row[0])
    stored_analysis = json.loads(row[1])

    assert "lineup input missing" in stored_input["missing_data"]
    assert "market_discrepancy_level unavailable" in stored_analysis["missing_data"]
