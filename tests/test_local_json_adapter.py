from __future__ import annotations

import importlib
import json
import socket
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_adapter_tools():
    adapter_module = importlib.import_module("src.collectors.local_json_adapter")
    mock_data_module = importlib.import_module("src.mock_data")
    contracts_module = importlib.import_module("src.contracts.report_input")
    return (
        adapter_module.load_report_input_from_json,
        adapter_module.LocalJsonAdapterError,
        mock_data_module.get_mock_report_input,
        contracts_module.ReportInput,
    )


def write_json_file(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_loading_valid_east_sample_json_into_report_input(tmp_path) -> None:
    load_report_input_from_json, _, get_mock_report_input, ReportInput = load_adapter_tools()
    json_path = write_json_file(
        tmp_path / "sample_report_input_east.json",
        get_mock_report_input("east").model_dump(),
    )

    report_input = load_report_input_from_json(json_path)

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "east"
    assert report_input.report_id == "mock-east-2026-05-13"


def test_loading_valid_west_sample_json_into_report_input(tmp_path) -> None:
    load_report_input_from_json, _, get_mock_report_input, ReportInput = load_adapter_tools()
    json_path = write_json_file(
        tmp_path / "sample_report_input_west.json",
        get_mock_report_input("west").model_dump(),
    )

    report_input = load_report_input_from_json(json_path)

    assert isinstance(report_input, ReportInput)
    assert report_input.region == "west"
    assert report_input.report_id == "mock-west-2026-05-13"


def test_invalid_json_fails_clearly(tmp_path) -> None:
    load_report_input_from_json, LocalJsonAdapterError, _, _ = load_adapter_tools()
    json_path = tmp_path / "broken_report_input.json"
    json_path.write_text('{"report_id": "broken",', encoding="utf-8")

    with pytest.raises(LocalJsonAdapterError, match="Invalid JSON"):
        load_report_input_from_json(json_path)


def test_missing_required_fields_fail_clearly(tmp_path) -> None:
    load_report_input_from_json, LocalJsonAdapterError, _, _ = load_adapter_tools()
    incomplete_payload = {
        "report_id": "missing-fields-report",
        "region": "east",
        "mode": "mock",
        "generated_at": "2026-05-13 21:00 KST",
        "report_name": "Incomplete Sample",
        "games": [],
    }
    json_path = write_json_file(tmp_path / "missing_fields.json", incomplete_payload)

    with pytest.raises(LocalJsonAdapterError, match="ReportInput validation failed"):
        load_report_input_from_json(json_path)


def test_missing_data_can_be_represented_explicitly(tmp_path) -> None:
    load_report_input_from_json, _, get_mock_report_input, _ = load_adapter_tools()
    payload = get_mock_report_input("east").model_dump()
    payload["missing_data"].append("manual review note missing")
    payload["games"][0]["missing_data"] = ["home lineup confirmation missing"]
    payload["games"][0]["data_quality"]["lineup_status"] = "partial"
    payload["games"][0]["data_quality"]["missing_data"] = [
        "home lineup confirmation missing",
    ]
    json_path = write_json_file(tmp_path / "missing_data_sample.json", payload)

    report_input = load_report_input_from_json(json_path)

    assert "manual review note missing" in report_input.missing_data
    assert "home lineup confirmation missing" in report_input.games[0].missing_data
    assert "home lineup confirmation missing" in report_input.games[0].data_quality.missing_data


def test_no_external_api_call_is_made(tmp_path, monkeypatch) -> None:
    load_report_input_from_json, _, get_mock_report_input, _ = load_adapter_tools()
    json_path = write_json_file(
        tmp_path / "local_only_report_input.json",
        get_mock_report_input("west").model_dump(),
    )

    def fail_on_network(*args, **kwargs):
        raise AssertionError("External network access should not be used.")

    monkeypatch.setattr(socket, "create_connection", fail_on_network)

    report_input = load_report_input_from_json(json_path)

    assert report_input.region == "west"
