from __future__ import annotations

from src.contracts.report_input import ReportInput
from src.schemas import GameReport, Region, ReportPayload


def get_mock_east_report() -> ReportPayload:
    return ReportPayload(
        report_id="mock-east-2026-05-13",
        region="east",
        title="AI Sports Analyst Agent - East Mock Report",
        generated_at="2026-05-13 21:00 KST",
        overview=(
            "This East mock report is a safe sample for Phase 1-A. "
            "It demonstrates report structure only and does not reflect live schedules."
        ),
        games=[
            GameReport(
                game_id="east-kbo-001",
                league="KBO",
                match_time_local="2026-05-14 18:30 KST",
                home_team="Seoul Mock Club",
                away_team="Busan Mock Club",
                label="강력 추천 경기",
                analysis_summary=(
                    "The base metadata is complete and easy to read, "
                    "so this sample works well as a "
                    "featured mock analysis card."
                ),
                watch_points=[
                    "League, teams, and start time are all present in the mock input.",
                    "The summary uses only visible mock fields without extra assumptions.",
                ],
                risk_factors=[
                    "This is sample content only and should not be read as a live prediction.",
                    "Player availability and late lineup updates are missing.",
                ],
                market_note=(
                    "Mock market note: broad price context is present, "
                    "but no live market feed is attached."
                ),
                missing_data=[
                    "confirmed lineup missing",
                    "weather input missing",
                ],
            ),
            GameReport(
                game_id="east-npb-002",
                league="NPB",
                match_time_local="2026-05-14 18:00 JST",
                home_team="Tokyo Sample Nine",
                away_team="Osaka Sample Nine",
                label="고신뢰 분석 경기",
                analysis_summary=(
                    "This sample has steady structure across its core fields, "
                    "which makes it easy to "
                    "read and compare in a mock report."
                ),
                watch_points=[
                    "The game card has a clear label, summary, and risk section.",
                    "Mock notes remain descriptive instead of acting like betting advice.",
                ],
                risk_factors=[
                    "No live injuries or player news are connected in this phase.",
                ],
                market_note=(
                    "Mock market note: internal notes are aligned with the visible metadata."
                ),
                missing_data=[
                    "player news missing",
                ],
            ),
            GameReport(
                game_id="east-kleague-003",
                league="K League",
                match_time_local="2026-05-14 19:30 KST",
                home_team="Incheon Demo FC",
                away_team="Daegu Demo FC",
                label="시장 괴리 높은 경기",
                analysis_summary=(
                    "This mock card shows how a report can describe a gap "
                    "between internal notes and "
                    "external market context without inventing live numbers."
                ),
                watch_points=[
                    "The label highlights a market-interpretation case for renderer testing.",
                    "The text explains the scenario without creating unsupported probabilities.",
                ],
                risk_factors=[
                    "No live odds feed is connected yet, "
                    "so the gap is only described at a mock level.",
                ],
                market_note=(
                    "Mock market note: internal qualitative grade is stronger than the placeholder "
                    "market tone shown in the sample input."
                ),
                missing_data=[
                    "live odds missing",
                    "market probability missing",
                ],
            ),
            GameReport(
                game_id="east-cup-004",
                league="East Regional Cup",
                match_time_local="2026-05-14 20:00 KST",
                home_team="Jeju Practice XI",
                away_team="Sapporo Practice XI",
                label="데이터 부족 경기",
                analysis_summary=(
                    "This mock card intentionally leaves several fields unavailable "
                    "so the report can "
                    "show a cautious presentation for thin data."
                ),
                watch_points=[
                    "The renderer should display missing information clearly.",
                ],
                risk_factors=[
                    "Several comparison points are unavailable in mock mode.",
                    "Use this sample to confirm that missing data is shown instead of guessed.",
                ],
                market_note=None,
                missing_data=[
                    "market note missing",
                    "recent form summary missing",
                    "weather input missing",
                ],
            ),
        ],
    )


def get_mock_west_report() -> ReportPayload:
    return ReportPayload(
        report_id="mock-west-2026-05-13",
        region="west",
        title="AI Sports Analyst Agent - West Mock Report",
        generated_at="2026-05-13 09:00 EDT",
        overview=(
            "This West mock report mirrors the East sample with a different league mix. "
            "It is for structure validation only and does not reflect live schedules."
        ),
        games=[
            GameReport(
                game_id="west-mlb-001",
                league="MLB",
                match_time_local="2026-05-13 19:05 EDT",
                home_team="New York Demo Club",
                away_team="Boston Demo Club",
                label="강력 추천 경기",
                analysis_summary=(
                    "This sample card has the fullest set of mock notes "
                    "in the West report, making it "
                    "useful for the featured section layout."
                ),
                watch_points=[
                    "All core text fields are available.",
                    "The game card demonstrates the main label badge style.",
                ],
                risk_factors=[
                    "Pitcher confirmation is not connected in mock mode.",
                ],
                market_note=(
                    "Mock market note: overall tone is slightly favorable, "
                    "but still placeholder-only."
                ),
                missing_data=[
                    "starting pitcher confirmation missing",
                ],
            ),
            GameReport(
                game_id="west-epl-002",
                league="EPL",
                match_time_local="2026-05-13 20:00 BST",
                home_team="London Example FC",
                away_team="Liverpool Example FC",
                label="고신뢰 분석 경기",
                analysis_summary=(
                    "This sample keeps the structure consistent and readable, "
                    "which makes it a useful "
                    "high-confidence mock example."
                ),
                watch_points=[
                    "The summary stays inside the information already present in the payload.",
                    "Risk notes remain visible even when the main card reads cleanly.",
                ],
                risk_factors=[
                    "Late squad availability is missing.",
                ],
                market_note=(
                    "Mock market note: the visible context is stable "
                    "and not in conflict with the summary."
                ),
                missing_data=[
                    "squad availability missing",
                ],
            ),
            GameReport(
                game_id="west-seriea-003",
                league="Serie A",
                match_time_local="2026-05-13 20:45 CEST",
                home_team="Milan Example Club",
                away_team="Rome Example Club",
                label="시장 괴리 높은 경기",
                analysis_summary=(
                    "This sample illustrates a disagreement between internal "
                    "mock notes and market tone "
                    "without using live prices or implied probabilities."
                ),
                watch_points=[
                    "Useful for testing the market note block in the renderer.",
                ],
                risk_factors=[
                    "Live market feeds are unavailable in this phase.",
                    "Any gap described here is only a mock scenario.",
                ],
                market_note=(
                    "Mock market note: placeholder market sentiment looks softer than the internal "
                    "qualitative read."
                ),
                missing_data=[
                    "live odds missing",
                    "market probability missing",
                ],
            ),
            GameReport(
                game_id="west-ucl-004",
                league="UCL",
                match_time_local="2026-05-13 21:00 CEST",
                home_team="Madrid Training XI",
                away_team="Munich Training XI",
                label="데이터 부족 경기",
                analysis_summary=(
                    "This sample is intentionally sparse so the renderer can "
                    "prove that unavailable "
                    "sections are shown honestly."
                ),
                watch_points=[
                    "The card should still render cleanly when several fields are thin.",
                ],
                risk_factors=[
                    "Recent trend notes are unavailable.",
                    "Context depth is limited in mock mode.",
                ],
                market_note=None,
                missing_data=[
                    "market note missing",
                    "recent trend summary missing",
                    "lineup input missing",
                ],
            ),
        ],
    )


def get_mock_report(region: Region) -> ReportPayload:
    if region == "east":
        return get_mock_east_report()
    if region == "west":
        return get_mock_west_report()
    raise ValueError(f"Unsupported mock region: {region}")


def get_mock_report_input(region: Region) -> ReportInput:
    if region == "east":
        return get_mock_east_report_input()
    if region == "west":
        return get_mock_west_report_input()
    raise ValueError(f"Unsupported mock region: {region}")


def get_mock_east_report_input() -> ReportInput:
    return ReportInput.model_validate(
        {
            "report_id": "mock-east-2026-05-13",
            "region": "east",
            "mode": "mock",
            "generated_at": "2026-05-13 21:00 KST",
            "report_name": "AI Sports Analyst Agent East Mock Report",
            "report_context": "Structured mock input for fallback CLI report generation.",
            "source_notes": [
                "Mock contract input only.",
            ],
            "missing_data": [
                "league-wide injury feed missing",
            ],
            "games": [
                {
                    "game_id": "east-kbo-001",
                    "league": "KBO",
                    "match_time_local": "2026-05-14 18:30 KST",
                    "home_team": "Seoul Mock Club",
                    "away_team": "Busan Mock Club",
                    "market_probability": {
                        "source_name": "Mock Odds Board",
                        "market_name": "moneyline",
                        "selection": "Seoul Mock Club",
                        "implied_probability": 0.64,
                        "confidence_level": "high",
                        "missing_data": [],
                    },
                    "reference_probability": {
                        "source_name": "Mock Reference Model",
                        "selection": "Seoul Mock Club",
                        "win_probability": 0.62,
                        "trust_level": "high",
                        "missing_data": [],
                    },
                    "data_quality": {
                        "trust_level": "high",
                        "odds_status": "available",
                        "lineup_status": "available",
                        "injury_status": "available",
                        "weather_status": "available",
                        "missing_data": [],
                        "notes": [
                            "All core mock fields are present.",
                        ],
                    },
                    "input_notes": [
                        "Structured sample for the strongest label path.",
                    ],
                    "missing_data": [],
                },
                {
                    "game_id": "east-npb-002",
                    "league": "NPB",
                    "match_time_local": "2026-05-14 18:00 JST",
                    "home_team": "Tokyo Sample Nine",
                    "away_team": "Osaka Sample Nine",
                    "market_probability": {
                        "source_name": "Mock Odds Board",
                        "market_name": "moneyline",
                        "selection": "Tokyo Sample Nine",
                        "implied_probability": 0.55,
                        "confidence_level": "medium",
                        "missing_data": [],
                    },
                    "reference_probability": {
                        "source_name": "Mock Reference Model",
                        "selection": "Tokyo Sample Nine",
                        "win_probability": 0.52,
                        "trust_level": "medium",
                        "missing_data": [],
                    },
                    "data_quality": {
                        "trust_level": "medium",
                        "odds_status": "available",
                        "lineup_status": "available",
                        "injury_status": "available",
                        "weather_status": "available",
                        "missing_data": [],
                        "notes": [
                            "The mock inputs are complete but not especially strong.",
                        ],
                    },
                    "input_notes": [
                        "Structured sample for a high-trust label path.",
                    ],
                    "missing_data": [],
                },
                {
                    "game_id": "east-kleague-003",
                    "league": "K League",
                    "match_time_local": "2026-05-14 19:30 KST",
                    "home_team": "Incheon Demo FC",
                    "away_team": "Daegu Demo FC",
                    "market_probability": {
                        "source_name": "Mock Odds Board",
                        "market_name": "moneyline",
                        "selection": "Incheon Demo FC",
                        "implied_probability": 0.70,
                        "confidence_level": "high",
                        "missing_data": [],
                    },
                    "reference_probability": {
                        "source_name": "Mock Reference Model",
                        "selection": "Incheon Demo FC",
                        "win_probability": 0.52,
                        "trust_level": "high",
                        "missing_data": [],
                    },
                    "data_quality": {
                        "trust_level": "high",
                        "odds_status": "available",
                        "lineup_status": "available",
                        "injury_status": "available",
                        "weather_status": "available",
                        "missing_data": [],
                        "notes": [
                            "The provided market and reference values are far apart.",
                        ],
                    },
                    "input_notes": [
                        "Structured sample for a market-gap label path.",
                    ],
                    "missing_data": [],
                },
                {
                    "game_id": "east-cup-004",
                    "league": "East Regional Cup",
                    "match_time_local": "2026-05-14 20:00 KST",
                    "home_team": "Jeju Practice XI",
                    "away_team": "Sapporo Practice XI",
                    "market_probability": {
                        "source_name": "Mock Odds Board",
                        "market_name": "moneyline",
                        "selection": "Jeju Practice XI",
                        "implied_probability": None,
                        "confidence_level": "low",
                        "missing_data": [
                            "market probability missing",
                        ],
                    },
                    "reference_probability": {
                        "source_name": "Mock Reference Model",
                        "selection": "Jeju Practice XI",
                        "win_probability": 0.48,
                        "trust_level": "medium",
                        "missing_data": [],
                    },
                    "data_quality": {
                        "trust_level": "medium",
                        "odds_status": "missing",
                        "lineup_status": "missing",
                        "injury_status": "missing",
                        "weather_status": "partial",
                        "missing_data": [
                            "odds feed missing",
                            "starting lineup missing",
                            "injury feed missing",
                            "full weather note missing",
                        ],
                        "notes": [
                            "Use this game to keep missing data explicit.",
                        ],
                    },
                    "input_notes": [
                        "Structured sample for a data-shortage label path.",
                    ],
                    "missing_data": [
                        "market probability missing",
                    ],
                },
            ],
        }
    )


def get_mock_west_report_input() -> ReportInput:
    return ReportInput.model_validate(
        {
            "report_id": "mock-west-2026-05-13",
            "region": "west",
            "mode": "mock",
            "generated_at": "2026-05-13 09:00 EDT",
            "report_name": "AI Sports Analyst Agent West Mock Report",
            "report_context": "Structured mock input for fallback CLI report generation.",
            "source_notes": [
                "Mock contract input only.",
            ],
            "missing_data": [
                "league-wide injury feed missing",
            ],
            "games": [
                {
                    "game_id": "west-mlb-001",
                    "league": "MLB",
                    "match_time_local": "2026-05-13 19:05 EDT",
                    "home_team": "New York Demo Club",
                    "away_team": "Boston Demo Club",
                    "market_probability": {
                        "source_name": "Mock Odds Board",
                        "market_name": "moneyline",
                        "selection": "New York Demo Club",
                        "implied_probability": 0.64,
                        "confidence_level": "high",
                        "missing_data": [],
                    },
                    "reference_probability": {
                        "source_name": "Mock Reference Model",
                        "selection": "New York Demo Club",
                        "win_probability": 0.62,
                        "trust_level": "high",
                        "missing_data": [],
                    },
                    "data_quality": {
                        "trust_level": "high",
                        "odds_status": "available",
                        "lineup_status": "available",
                        "injury_status": "available",
                        "weather_status": "available",
                        "missing_data": [],
                        "notes": [
                            "All core mock fields are present.",
                        ],
                    },
                    "input_notes": [
                        "Structured sample for the strongest label path.",
                    ],
                    "missing_data": [],
                },
                {
                    "game_id": "west-epl-002",
                    "league": "EPL",
                    "match_time_local": "2026-05-13 20:00 BST",
                    "home_team": "London Example FC",
                    "away_team": "Liverpool Example FC",
                    "market_probability": {
                        "source_name": "Mock Odds Board",
                        "market_name": "match result",
                        "selection": "London Example FC",
                        "implied_probability": 0.55,
                        "confidence_level": "medium",
                        "missing_data": [],
                    },
                    "reference_probability": {
                        "source_name": "Mock Reference Model",
                        "selection": "London Example FC",
                        "win_probability": 0.52,
                        "trust_level": "medium",
                        "missing_data": [],
                    },
                    "data_quality": {
                        "trust_level": "medium",
                        "odds_status": "available",
                        "lineup_status": "available",
                        "injury_status": "available",
                        "weather_status": "available",
                        "missing_data": [],
                        "notes": [
                            "The mock inputs are complete but not especially strong.",
                        ],
                    },
                    "input_notes": [
                        "Structured sample for a high-trust label path.",
                    ],
                    "missing_data": [],
                },
                {
                    "game_id": "west-seriea-003",
                    "league": "Serie A",
                    "match_time_local": "2026-05-13 20:45 CEST",
                    "home_team": "Milan Example Club",
                    "away_team": "Rome Example Club",
                    "market_probability": {
                        "source_name": "Mock Odds Board",
                        "market_name": "match result",
                        "selection": "Milan Example Club",
                        "implied_probability": 0.70,
                        "confidence_level": "high",
                        "missing_data": [],
                    },
                    "reference_probability": {
                        "source_name": "Mock Reference Model",
                        "selection": "Milan Example Club",
                        "win_probability": 0.52,
                        "trust_level": "high",
                        "missing_data": [],
                    },
                    "data_quality": {
                        "trust_level": "high",
                        "odds_status": "available",
                        "lineup_status": "available",
                        "injury_status": "available",
                        "weather_status": "available",
                        "missing_data": [],
                        "notes": [
                            "The provided market and reference values are far apart.",
                        ],
                    },
                    "input_notes": [
                        "Structured sample for a market-gap label path.",
                    ],
                    "missing_data": [],
                },
                {
                    "game_id": "west-ucl-004",
                    "league": "UCL",
                    "match_time_local": "2026-05-13 21:00 CEST",
                    "home_team": "Madrid Training XI",
                    "away_team": "Munich Training XI",
                    "market_probability": {
                        "source_name": "Mock Odds Board",
                        "market_name": "match result",
                        "selection": "Madrid Training XI",
                        "implied_probability": None,
                        "confidence_level": "low",
                        "missing_data": [
                            "market probability missing",
                        ],
                    },
                    "reference_probability": {
                        "source_name": "Mock Reference Model",
                        "selection": "Madrid Training XI",
                        "win_probability": 0.48,
                        "trust_level": "medium",
                        "missing_data": [],
                    },
                    "data_quality": {
                        "trust_level": "medium",
                        "odds_status": "missing",
                        "lineup_status": "missing",
                        "injury_status": "missing",
                        "weather_status": "partial",
                        "missing_data": [
                            "odds feed missing",
                            "starting lineup missing",
                            "injury feed missing",
                            "full weather note missing",
                        ],
                        "notes": [
                            "Use this game to keep missing data explicit.",
                        ],
                    },
                    "input_notes": [
                        "Structured sample for a data-shortage label path.",
                    ],
                    "missing_data": [
                        "market probability missing",
                    ],
                },
            ],
        }
    )
