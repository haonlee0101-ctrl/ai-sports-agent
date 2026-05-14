from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from src.contracts.report_input import ReportInput


class LocalJsonAdapterError(ValueError):
    """Raised when a local ReportInput JSON file cannot be loaded safely."""


def load_report_input_from_json(path: str | Path) -> ReportInput:
    """Load a local JSON file and validate it as a ReportInput payload."""

    file_path = Path(path)
    payload = _read_json_payload(file_path)

    try:
        return ReportInput.model_validate(payload)
    except ValidationError as error:
        raise LocalJsonAdapterError(
            f"ReportInput validation failed for {file_path}: {error}"
        ) from error


def _read_json_payload(file_path: Path) -> dict:
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as error:
        raise LocalJsonAdapterError(
            f"Could not read local ReportInput JSON file: {file_path}"
        ) from error

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise LocalJsonAdapterError(
            f"Invalid JSON in local ReportInput file {file_path}: {error.msg}"
        ) from error

    if not isinstance(payload, dict):
        raise LocalJsonAdapterError(
            f"Local ReportInput file must contain a JSON object: {file_path}"
        )

    return payload
