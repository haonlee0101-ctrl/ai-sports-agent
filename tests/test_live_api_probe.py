from __future__ import annotations

import json
import re
import sys
from io import StringIO
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import probe_live_apis  # noqa: E402


def load_fixture(filename: str):
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def collect_repo_files() -> set[Path]:
    return {
        path.relative_to(PROJECT_ROOT)
        for path in PROJECT_ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


def test_no_network_call_occurs_without_confirm_live() -> None:
    api_sports_called = False
    odds_called = False
    output = StringIO()

    def raising_api_sports_transport(url, headers):
        nonlocal api_sports_called
        api_sports_called = True
        raise AssertionError("API-Sports transport should not be called without --confirm-live.")

    def raising_odds_transport(url, headers):
        nonlocal odds_called
        odds_called = True
        raise AssertionError("Odds transport should not be called without --confirm-live.")

    exit_code = probe_live_apis.main(
        ["--provider", "both"],
        env={"API_SPORTS_KEY": "test-key", "ODDS_API_KEY": "test-odds-key"},
        stdout=output,
        api_sports_transport=raising_api_sports_transport,
        odds_transport=raising_odds_transport,
    )

    assert exit_code == 1
    assert "Refusing live API probe without --confirm-live." in output.getvalue()
    assert api_sports_called is False
    assert odds_called is False


def test_missing_api_sports_key_fails_clearly_before_network_call() -> None:
    transport_called = False
    output = StringIO()

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called before API key validation.")

    exit_code = probe_live_apis.main(
        ["--provider", "api-sports", "--confirm-live"],
        env={},
        stdout=output,
        api_sports_transport=raising_transport,
    )

    assert exit_code == 1
    assert "API_SPORTS_KEY is required for api-sports live probe." in output.getvalue()
    assert transport_called is False


def test_missing_odds_key_fails_clearly_before_network_call() -> None:
    transport_called = False
    output = StringIO()

    def raising_transport(url, headers):
        nonlocal transport_called
        transport_called = True
        raise AssertionError("Transport should not be called before API key validation.")

    exit_code = probe_live_apis.main(
        ["--provider", "odds", "--confirm-live"],
        env={},
        stdout=output,
        odds_transport=raising_transport,
    )

    assert exit_code == 1
    assert "ODDS_API_KEY is required for odds live probe." in output.getvalue()
    assert transport_called is False


def test_fake_injected_transport_can_simulate_api_sports_response() -> None:
    output = StringIO()
    fake_response = load_fixture("api_sports_fixtures_sample.json")

    def fake_transport(url, headers):
        assert "test-api-sports-key" not in url
        return fake_response

    exit_code = probe_live_apis.main(
        ["--provider", "api-sports", "--confirm-live"],
        env={"API_SPORTS_KEY": "test-api-sports-key"},
        stdout=output,
        api_sports_transport=fake_transport,
    )

    stdout_text = output.getvalue()

    assert exit_code == 0
    assert "provider: api-sports" in stdout_text
    assert "status: success" in stdout_text
    assert "top_level_keys: generated_at, mode, region, response" in stdout_text
    assert "item_count: 2" in stdout_text
    assert "sample_refs: 501001, 501002" in stdout_text
    assert "test-api-sports-key" not in stdout_text


def test_fake_injected_transport_can_simulate_odds_response() -> None:
    output = StringIO()
    fake_response = load_fixture("odds_api_events_sample.json")

    def fake_transport(url, headers):
        assert "https://api.the-odds-api.com" in url
        return fake_response

    exit_code = probe_live_apis.main(
        ["--provider", "odds", "--confirm-live"],
        env={"ODDS_API_KEY": "test-odds-key"},
        stdout=output,
        odds_transport=fake_transport,
    )

    stdout_text = output.getvalue()

    assert exit_code == 0
    assert "provider: odds" in stdout_text
    assert "status: success" in stdout_text
    assert "top_level_keys: events" in stdout_text
    assert "item_count: 2" in stdout_text
    assert "sample_refs: odds-event-001, odds-event-002" in stdout_text
    assert "test-odds-key" not in stdout_text


def test_api_keys_are_not_printed() -> None:
    output = StringIO()
    fake_response = load_fixture("api_sports_fixtures_sample.json")
    secret_value = "super-secret-api-key"

    exit_code = probe_live_apis.main(
        ["--provider", "api-sports", "--confirm-live"],
        env={"API_SPORTS_KEY": secret_value},
        stdout=output,
        api_sports_transport=lambda url, headers: fake_response,
    )

    assert exit_code == 0
    assert secret_value not in output.getvalue()


def test_raw_responses_are_not_written_to_repository() -> None:
    before_files = collect_repo_files()
    output = StringIO()
    fake_response = load_fixture("odds_api_events_sample.json")

    exit_code = probe_live_apis.main(
        ["--provider", "odds", "--confirm-live"],
        env={"ODDS_API_KEY": "test-odds-key"},
        stdout=output,
        odds_transport=lambda url, headers: fake_response,
    )

    after_files = collect_repo_files()

    assert exit_code == 0
    assert before_files == after_files


def test_unsupported_provider_fails_clearly() -> None:
    output = StringIO()

    exit_code = probe_live_apis.main(
        ["--provider", "invalid-provider", "--confirm-live"],
        env={},
        stdout=output,
    )

    assert exit_code == 1
    assert "Unsupported provider. Use one of: api-sports, odds, both." in output.getvalue()


def test_no_secrets_are_hardcoded() -> None:
    probe_source = (PROJECT_ROOT / "scripts" / "probe_live_apis.py").read_text(encoding="utf-8")
    suspicious_patterns = [
        r"sk-[A-Za-z0-9]{16,}",
        r"SG\.[A-Za-z0-9._-]{20,}",
        r"https?://[^\\s\"']+[?&](?:api_?key|key|token)=",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]

    for pattern in suspicious_patterns:
        assert re.search(pattern, probe_source) is None
