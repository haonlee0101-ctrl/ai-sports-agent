from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "report.yml"


def load_workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_workflow_file_exists() -> None:
    assert WORKFLOW_PATH.exists()


def test_workflow_includes_workflow_dispatch() -> None:
    workflow_text = load_workflow_text()

    assert "workflow_dispatch:" in workflow_text


def test_workflow_includes_schedule() -> None:
    workflow_text = load_workflow_text()

    assert "schedule:" in workflow_text


def test_workflow_includes_both_cron_values() -> None:
    workflow_text = load_workflow_text()

    assert 'cron: "7 16 * * *"' in workflow_text
    assert 'cron: "7 4 * * *"' in workflow_text


def test_workflow_references_python_311() -> None:
    workflow_text = load_workflow_text()

    assert 'python-version: "3.11"' in workflow_text


def test_workflow_runs_ruff_check() -> None:
    workflow_text = load_workflow_text()

    assert "ruff check ." in workflow_text


def test_workflow_runs_pytest() -> None:
    workflow_text = load_workflow_text()

    assert re.search(r"(^|\n)\s*run:\s+pytest\b", workflow_text)


def test_workflow_runs_run_report_py() -> None:
    workflow_text = load_workflow_text()

    assert "python run_report.py" in workflow_text


def test_workflow_references_healthchecks_secrets() -> None:
    workflow_text = load_workflow_text()

    assert "HEALTHCHECKS_EAST_URL" in workflow_text
    assert "HEALTHCHECKS_WEST_URL" in workflow_text


def test_workflow_uploads_html_artifacts() -> None:
    workflow_text = load_workflow_text()

    assert "actions/upload-artifact@v4" in workflow_text
    assert "out/*.html" in workflow_text
    assert "html-report-east-" in workflow_text
    assert "html-report-west-" in workflow_text


def test_workflow_uploads_sqlite_artifacts() -> None:
    workflow_text = load_workflow_text()

    assert "data/sports_agent.sqlite" in workflow_text
    assert "sqlite-db-east-" in workflow_text
    assert "sqlite-db-west-" in workflow_text
    assert "if-no-files-found: ignore" in workflow_text


def test_workflow_artifact_names_include_run_specific_parts() -> None:
    workflow_text = load_workflow_text()

    assert "ARTIFACT_TS=$(date -u +%Y%m%dT%H%M%SZ)" in workflow_text
    assert "github.run_number" in workflow_text
    assert "steps.east_artifact_ts.outputs.artifact_ts" in workflow_text
    assert "steps.west_artifact_ts.outputs.artifact_ts" in workflow_text


def test_workflow_does_not_contain_hardcoded_secret_looking_values() -> None:
    workflow_text = load_workflow_text()

    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"https://hc-ping\.com/[A-Za-z0-9-]+",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, workflow_text) is None
