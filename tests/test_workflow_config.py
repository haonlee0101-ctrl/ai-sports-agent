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
ASIA_DAY_REPORT_SLOT = (
    "REPORT_SLOT: ${{ github.event_name == 'workflow_dispatch' "
    "&& inputs.report_slot || 'asia_day_preview' }}"
)
GLOBAL_NIGHT_REPORT_SLOT = (
    "REPORT_SLOT: ${{ github.event_name == 'workflow_dispatch' "
    "&& inputs.report_slot || 'global_night_preview' }}"
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


def test_workflow_uses_report_slot_labels() -> None:
    workflow_text = load_workflow_text()

    assert "name: Report Workflow" in workflow_text
    assert "run-name:" in workflow_text
    assert "manual report {0} {1} {2} {3}" in workflow_text
    assert "scheduled report asia_day_preview east-compat fixture fallback" in workflow_text
    assert "scheduled report global_night_preview west-compat fixture fallback" in workflow_text
    assert "Mock Report Workflow" not in workflow_text


def test_workflow_includes_workflow_dispatch_and_schedule() -> None:
    workflow_text = load_workflow_text()

    assert "workflow_dispatch:" in workflow_text
    assert "schedule:" in workflow_text


def test_workflow_includes_new_report_slot_cron_values() -> None:
    workflow_text = load_workflow_text()

    assert 'cron: "0 16 * * *"' in workflow_text
    assert 'cron: "0 4 * * *"' in workflow_text


def test_workflow_does_not_use_old_report_slot_cron_values() -> None:
    workflow_text = load_workflow_text()

    assert 'cron: "10 21 * * *"' not in workflow_text
    assert 'cron: "10 9 * * *"' not in workflow_text


def test_workflow_mentions_new_kst_schedule_times_and_not_old_ones() -> None:
    workflow_text = load_workflow_text()

    assert "01:00 KST" in workflow_text
    assert "13:00 KST" in workflow_text
    assert "06:10 KST" not in workflow_text
    assert "18:10 KST" not in workflow_text


def test_workflow_dispatch_has_report_slot_input_with_expected_choices() -> None:
    workflow_text = load_workflow_text()

    assert "report_slot:" in workflow_text
    assert 'default: "asia_day_preview"' in workflow_text
    assert "  - asia_day_preview" in workflow_text
    assert "  - global_night_preview" in workflow_text


def test_manual_workflow_dispatch_still_supports_region_input() -> None:
    workflow_text = load_workflow_text()

    assert "region:" in workflow_text
    assert "  - east" in workflow_text
    assert "  - west" in workflow_text
    assert "  - both" in workflow_text


def test_workflow_keeps_fixture_mode_available() -> None:
    workflow_text = load_workflow_text()

    assert 'description: "Choose mock mode or local fixture mode."' in workflow_text
    assert "mode:" in workflow_text
    assert "  - mock" in workflow_text
    assert "  - fixture" in workflow_text
    assert SCHEDULED_FIXTURE_MODE in workflow_text


def test_workflow_keeps_fallback_analysis_available() -> None:
    workflow_text = load_workflow_text()

    assert "analysis:" in workflow_text
    assert "  - fallback" in workflow_text
    assert SCHEDULED_FALLBACK_ANALYSIS in workflow_text


def test_workflow_references_python_311_and_runs_checks() -> None:
    workflow_text = load_workflow_text()

    assert 'python-version: "3.11"' in workflow_text
    assert "ruff check ." in workflow_text
    assert re.search(r"(^|\n)\s*run:\s+pytest\b", workflow_text)
    assert "python run_report.py" in workflow_text


def test_scheduled_asia_day_preview_maps_to_east_compatibility_region() -> None:
    workflow_text = load_workflow_text()
    east_section = get_job_section(workflow_text, "east-report")

    assert "github.event.schedule == '0 16 * * *'" in east_section
    assert ASIA_DAY_REPORT_SLOT in east_section
    assert "COMPAT_REGION: east" in east_section
    assert SCHEDULED_FIXTURE_MODE in east_section
    assert SCHEDULED_FALLBACK_ANALYSIS in east_section
    assert SCHEDULED_SEND_TRUE in east_section
    assert SCHEDULED_SAVE_TRUE in east_section
    assert '--region "${COMPAT_REGION}"' in east_section
    assert "tests/fixtures/api_sports_fixtures_sample.json" in east_section
    assert "tests/fixtures/odds_api_events_sample.json" in east_section


def test_scheduled_global_night_preview_maps_to_west_compatibility_region() -> None:
    workflow_text = load_workflow_text()
    west_section = get_job_section(workflow_text, "west-report")

    assert "github.event.schedule == '0 4 * * *'" in west_section
    assert GLOBAL_NIGHT_REPORT_SLOT in west_section
    assert "COMPAT_REGION: west" in west_section
    assert SCHEDULED_FIXTURE_MODE in west_section
    assert SCHEDULED_FALLBACK_ANALYSIS in west_section
    assert SCHEDULED_SEND_TRUE in west_section
    assert SCHEDULED_SAVE_TRUE in west_section
    assert '--region "${COMPAT_REGION}"' in west_section
    assert "tests/fixtures/api_sports_fixtures_west_sample.json" in west_section
    assert "tests/fixtures/odds_api_events_west_sample.json" in west_section


def test_workflow_includes_report_slot_compatibility_comments() -> None:
    workflow_text = load_workflow_text()

    assert "report_slot is the new scheduling concept." in workflow_text
    assert (
        "region remains a compatibility bridge until run_report.py supports report_slot directly."
        in workflow_text
    )
    assert (
        "Region remains a compatibility bridge until the CLI supports report_slot directly."
        in workflow_text
    )


def test_workflow_upload_artifact_steps_are_preserved() -> None:
    workflow_text = load_workflow_text()

    assert "actions/upload-artifact@v4" in workflow_text
    assert "Upload east HTML artifact" in workflow_text
    assert "Upload west HTML artifact" in workflow_text
    assert "Upload east SQLite artifact" in workflow_text
    assert "Upload west SQLite artifact" in workflow_text
    assert "out/*.html" in workflow_text
    assert "data/sports_agent.sqlite" in workflow_text
    assert "if-no-files-found: ignore" in workflow_text


def test_workflow_artifact_names_remain_run_specific() -> None:
    workflow_text = load_workflow_text()

    assert "ARTIFACT_TS=$(date -u +%Y%m%dT%H%M%SZ)" in workflow_text
    assert "github.run_number" in workflow_text
    assert "html-report-east-" in workflow_text
    assert "html-report-west-" in workflow_text
    assert "sqlite-db-east-" in workflow_text
    assert "sqlite-db-west-" in workflow_text


def test_workflow_healthcheck_steps_are_preserved() -> None:
    workflow_text = load_workflow_text()

    assert "Ping Healthchecks start" in workflow_text
    assert "Ping Healthchecks success" in workflow_text
    assert "Ping Healthchecks failure" in workflow_text
    assert "${HEALTHCHECKS_EAST_URL}/fail" in workflow_text
    assert "${HEALTHCHECKS_WEST_URL}/fail" in workflow_text
    assert "secrets.HEALTHCHECKS_EAST_URL" in workflow_text
    assert "secrets.HEALTHCHECKS_WEST_URL" in workflow_text


def test_workflow_does_not_contain_hardcoded_secret_looking_values() -> None:
    workflow_text = load_workflow_text()

    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"https://hc-ping\.com/[A-Za-z0-9-]+",
        r"https?://[^\\s\"']+[?&](?:api_?key|key|token)=",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, workflow_text) is None
