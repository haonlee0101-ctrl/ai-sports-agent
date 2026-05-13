from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path("data/sports_agent.sqlite")
KST = timezone(timedelta(hours=9))
TIMEZONE_OFFSETS = {
    "UTC": 0,
    "JST": 9,
    "KST": 9,
    "EDT": -4,
    "EST": -5,
    "BST": 1,
    "CEST": 2,
}
REPORT_TIME_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2}) (?P<tz>[A-Z]{2,4})$"
)


class PredictionLogError(RuntimeError):
    """Raised when the local prediction log cannot be created or written."""


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sqlite3.connect(path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS prediction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_time_kst TEXT NOT NULL,
                    region TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    analysis_mode TEXT NOT NULL,
                    game_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    data_trust_level TEXT,
                    prediction_confidence_level TEXT,
                    market_discrepancy_level TEXT,
                    recommended_side TEXT,
                    summary TEXT NOT NULL,
                    input_snapshot_json TEXT NOT NULL,
                    analysis_output_json TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(report_time_kst, game_id)
                )
                """
            )
            connection.commit()
    except sqlite3.Error as error:
        raise PredictionLogError(
            f"Failed to initialize SQLite database at {path}: {error}"
        ) from error

    return path


def save_prediction_log(
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    report_time_kst: str,
    region: str,
    mode: str,
    analysis_mode: str,
    game_id: str,
    label: str,
    data_trust_level: str | None,
    prediction_confidence_level: str | None,
    market_discrepancy_level: str | None,
    recommended_side: str | None,
    summary: str,
    input_snapshot_json: str,
    analysis_output_json: str | None,
    created_at: str | None = None,
) -> bool:
    path = init_db(db_path)
    normalized_report_time = normalize_report_time_kst(report_time_kst)
    created_timestamp = created_at or _build_created_at()

    try:
        with sqlite3.connect(path) as connection:
            before_changes = connection.total_changes
            connection.execute(
                """
                INSERT OR IGNORE INTO prediction_log (
                    report_time_kst,
                    region,
                    mode,
                    analysis_mode,
                    game_id,
                    label,
                    data_trust_level,
                    prediction_confidence_level,
                    market_discrepancy_level,
                    recommended_side,
                    summary,
                    input_snapshot_json,
                    analysis_output_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_report_time,
                    region,
                    mode,
                    analysis_mode,
                    game_id,
                    label,
                    data_trust_level,
                    prediction_confidence_level,
                    market_discrepancy_level,
                    recommended_side,
                    summary,
                    input_snapshot_json,
                    analysis_output_json,
                    created_timestamp,
                ),
            )
            connection.commit()
            return connection.total_changes > before_changes
    except sqlite3.Error as error:
        raise PredictionLogError(
            f"Failed to save prediction log row for {game_id}: {error}"
        ) from error


def normalize_report_time_kst(report_time: str) -> str:
    match = REPORT_TIME_PATTERN.match(report_time.strip())
    if match is None:
        return report_time.strip()

    timezone_name = match.group("tz")
    offset_hours = TIMEZONE_OFFSETS.get(timezone_name)
    if offset_hours is None:
        return report_time.strip()

    naive_datetime = datetime.strptime(
        f"{match.group('date')} {match.group('time')}",
        "%Y-%m-%d %H:%M",
    )
    source_timezone = timezone(timedelta(hours=offset_hours))
    localized_datetime = naive_datetime.replace(tzinfo=source_timezone)
    kst_datetime = localized_datetime.astimezone(KST)
    return kst_datetime.strftime("%Y-%m-%d %H:%M KST")


def _build_created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
