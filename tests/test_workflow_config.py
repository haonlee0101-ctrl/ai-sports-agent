from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "report.yml"
SCHEDULED_FIXTURE_MODE = (
    "REPORT_MODE: ${{ github.event_name == 'workflow_dispatch' && inputs.mode || 'fixture' }}"
)
SCHEDULED_FALLBACK_ANALYSIS = (
    "ANALYSIS_MODE: ${{ github.event_name == 'workflow_dispatch' "
    "&& inputs.analysis || 'fallback' }}"
)
SCHEDULED_SEND_TRUE = (
    "SEND_REPORT: ${{ github.event_name == 'workflow_dispatch' && inputs.send || 'true' }}"
)
SCHEDULED_SAVE_TRUE = (
    "SAVE_REPORT: ${{ github.event_name == 'workflow_dispatch' && inputs.save || 'true' }}"
)


def load_workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def get_job_section(workflow_text: str, job_name: str) -> str:
    pattern = re.compile(
        rf"^  {re.escape(job_name)}:\n(?P<section>.*?)(?=^  [a-z0-9-]+:\n|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(workflow_text)
    assert match is not None, f"Could not find workflow job section for {job_name}."
    return match.group("section")


def test_workflow_file_exists() -> None:
    assert WORKFLOW_PATH.exists()


def test_workflow_uses_neutral_display_labels() -> None:
    workflow_text = load_workflow_text()

    assert "name: Report Workflow" in workflow_text
    assert "run-name:" in workflow_text
    assert "manual report {0} {1} {2}" in workflow_text
    assert "scheduled report east fixture fallback" in workflow_text
    assert "scheduled report west fixture fallback" in workflow_text
    assert "name: East Report" in workflow_text
    assert "name: West Report" in workflow_text
    assert "Generate east report" in workflow_text
    assert "Generate west report" in workflow_text
    assert "Mock Report Workflow" not in workflow_text
    assert "East Mock Report" not in workflow_text
    assert "West Mock Report" not in workflow_text


def test_workflow_includes_workflow_dispatch() -> None:
    workflow_text = load_workflow_text()

    assert "workflow_dispatch:" in workflow_text


def test_workflow_includes_schedule() -> None:
    workflow_text = load_workflow_text()

    assert "schedule:" in workflow_text


def test_workflow_includes_both_cron_values() -> None:
    workflow_text = load_workflow_text()

    assert 'cron: "10 21 * * *"' in workflow_text
    assert 'cron: "10 9 * * *"' in workflow_text


def test_workflow_mentions_kst_schedule_times() -> None:
    workflow_text = load_workflow_text()

    assert "06:10 KST" in workflow_text
    assert "18:10 KST" in workflow_text


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


def test_workflow_supports_mode_fixture() -> None:
    workflow_text = load_workflow_text()

    assert 'description: "Choose mock mode or local fixture mode."' in workflow_text
    assert "mode:" in workflow_text
    assert "  - fixture" in workflow_text
    assert "--mode fixture" in workflow_text


def test_workflow_still_supports_mode_mock() -> None:
    workflow_text = load_workflow_text()

    assert "  - mock" in workflow_text
    assert 'description: "Choose which report region to run."' in workflow_text
    assert '--mode "${REPORT_MODE}"' in workflow_text
    assert 'default: "mock"' in workflow_text


def test_manual_workflow_dispatch_still_supports_region_input() -> None:
    workflow_text = load_workflow_text()

    assert "region:" in workflow_text
    assert "  - east" in workflow_text
    assert "  - west" in workflow_text
    assert "  - both" in workflow_text


def test_workflow_references_fixture_mode_files() -> None:
    workflow_text = load_workflow_text()

    assert "--fixtures-file" in workflow_text
    assert "--odds-file" in workflow_text
    assert "tests/fixtures/api_sports_fixtures_sample.json" in workflow_text
    assert "tests/fixtures/odds_api_events_sample.json" in workflow_text
    assert "tests/fixtures/api_sports_fixtures_west_sample.json" in workflow_text
    assert "tests/fixtures/odds_api_events_west_sample.json" in workflow_text


def test_workflow_uses_region_specific_fixture_paths() -> None:
    workflow_text = load_workflow_text()

    east_fixture_pattern = re.compile(
        r"--region east\s+--mode fixture\s+--fixtures-file "
        r"tests/fixtures/api_sports_fixtures_sample\.json\s+--odds-file "
        r"tests/fixtures/odds_api_events_sample\.json",
        re.MULTILINE,
    )
    west_fixture_pattern = re.compile(
        r"--region west\s+--mode fixture\s+--fixtures-file "
        r"tests/fixtures/api_sports_fixtures_west_sample\.json\s+--odds-file "
        r"tests/fixtures/odds_api_events_west_sample\.json",
        re.MULTILINE,
    )

    assert east_fixture_pattern.search(workflow_text) is not None
    assert west_fixture_pattern.search(workflow_text) is not None


def test_scheduled_east_run_maps_to_east_region_with_fixture_defaults() -> None:
    workflow_text = load_workflow_text()
    east_section = get_job_section(workflow_text, "east-report")

    assert "github.event.schedule == '10 21 * * *'" in east_section
    assert "--region east" in east_section
    assert SCHEDULED_FIXTURE_MODE in east_section
    assert SCHEDULED_FALLBACK_ANALYSIS in east_section
    assert SCHEDULED_SEND_TRUE in east_section
    assert SCHEDULED_SAVE_TRUE in east_section
    assert "tests/fixtures/api_sports_fixtures_sample.json" in east_section
    assert "tests/fixtures/odds_api_events_sample.json" in east_section


def test_scheduled_west_run_maps_to_west_region_with_fixture_defaults() -> None:
    workflow_text = load_workflow_text()
    west_section = get_job_section(workflow_text, "west-report")

    assert "github.event.schedule == '10 9 * * *'" in west_section
    assert "--region west" in west_section
    assert SCHEDULED_FIXTURE_MODE in west_section
    assert SCHEDULED_FALLBACK_ANALYSIS in west_section
    assert SCHEDULED_SEND_TRUE in west_section
    assert SCHEDULED_SAVE_TRUE in west_section
    assert "tests/fixtures/api_sports_fixtures_west_sample.json" in west_section
    assert "tests/fixtures/odds_api_events_west_sample.json" in west_section


def test_workflow_references_healthchecks_secrets() -> None:
    workflow_text = load_workflow_text()

    assert "HEALTHCHECKS_EAST_URL" in workflow_text
    assert "HEALTHCHECKS_WEST_URL" in workflow_text
    assert "secrets.HEALTHCHECKS_EAST_URL" in workflow_text
    assert "secrets.HEALTHCHECKS_WEST_URL" in workflow_text


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
