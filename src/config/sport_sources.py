from __future__ import annotations

from dataclasses import dataclass

REPORT_SLOTS = (
    "asia_day_preview",
    "global_night_preview",
)


@dataclass(frozen=True)
class ReportSlotSchedule:
    """Beginner-friendly delivery schedule settings for a report slot."""

    report_slot: str
    delivery_time_kst: str
    description: str


@dataclass(frozen=True)
class SportSource:
    """Catalog entry for one league in one report slot."""

    sport: str
    league_key: str
    display_name: str
    report_slot: str
    region_group: str
    primary_odds_source: str
    secondary_schedule_source: str
    enabled: bool
    notes: str
    missing_data_policy: str


REPORT_SLOT_SCHEDULES: dict[str, ReportSlotSchedule] = {
    "asia_day_preview": ReportSlotSchedule(
        report_slot="asia_day_preview",
        delivery_time_kst="01:00 KST",
        description=(
            "Covers games expected after 01:00 KST on the same Korean calendar day, "
            "with emphasis on East Asia afternoon and evening schedules."
        ),
    ),
    "global_night_preview": ReportSlotSchedule(
        report_slot="global_night_preview",
        delivery_time_kst="13:00 KST",
        description=(
            "Covers games expected after 13:00 KST through the next Korean morning, "
            "with emphasis on overseas night and early-morning schedules."
        ),
    ),
}

DEFAULT_PRIMARY_ODDS_SOURCE = "The Odds API"
DEFAULT_MISSING_DATA_POLICY = (
    "If secondary metadata is unavailable, mark schedule context, injuries, lineups, "
    "weather, or other unsupported fields as missing instead of guessing."
)
SCHEDULE_CANDIDATE_NOTE = (
    "Candidate only for schedule enrichment. No paid secondary source is required yet."
)
KICKOFF_CANDIDATE_NOTE = (
    "Candidate only for kickoff and club metadata. No paid secondary source is required yet."
)
MLB_CANDIDATE_NOTE = (
    "Candidate only for schedule enrichment. MLB Stats API is useful before any paid add-on."
)
EUROPE_CROSS_BORDER_NOTE = (
    "Candidate only for cross-border schedule metadata. No paid secondary source is required yet."
)

SPORT_SOURCE_CATALOG: tuple[SportSource, ...] = (
    SportSource(
        sport="baseball",
        league_key="baseball_kbo",
        display_name="KBO",
        report_slot="asia_day_preview",
        region_group="east_asia",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: API-BASEBALL or Data Sports Group",
        enabled=True,
        notes=SCHEDULE_CANDIDATE_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
    SportSource(
        sport="baseball",
        league_key="baseball_npb",
        display_name="NPB",
        report_slot="asia_day_preview",
        region_group="east_asia",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: API-BASEBALL or Data Sports Group",
        enabled=True,
        notes=SCHEDULE_CANDIDATE_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
    SportSource(
        sport="soccer",
        league_key="soccer_korea_kleague1",
        display_name="K League 1",
        report_slot="asia_day_preview",
        region_group="east_asia",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: API-Football or football-data.org",
        enabled=True,
        notes=KICKOFF_CANDIDATE_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
    SportSource(
        sport="soccer",
        league_key="soccer_japan_j_league",
        display_name="J League",
        report_slot="asia_day_preview",
        region_group="east_asia",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: API-Football or SportMonks",
        enabled=True,
        notes=KICKOFF_CANDIDATE_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
    SportSource(
        sport="baseball",
        league_key="baseball_mlb",
        display_name="MLB",
        report_slot="global_night_preview",
        region_group="north_america",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: MLB Stats API or SportsDataIO",
        enabled=True,
        notes=MLB_CANDIDATE_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
    SportSource(
        sport="basketball",
        league_key="basketball_nba",
        display_name="NBA",
        report_slot="global_night_preview",
        region_group="north_america",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: SportsDataIO",
        enabled=True,
        notes=SCHEDULE_CANDIDATE_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
    SportSource(
        sport="soccer",
        league_key="soccer_epl",
        display_name="Premier League",
        report_slot="global_night_preview",
        region_group="europe",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: football-data.org or API-Football",
        enabled=True,
        notes=KICKOFF_CANDIDATE_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
    SportSource(
        sport="soccer",
        league_key="soccer_spain_la_liga",
        display_name="La Liga",
        report_slot="global_night_preview",
        region_group="europe",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: API-Football or SportMonks",
        enabled=True,
        notes=KICKOFF_CANDIDATE_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
    SportSource(
        sport="soccer",
        league_key="soccer_italy_serie_a",
        display_name="Serie A",
        report_slot="global_night_preview",
        region_group="europe",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: API-Football or SportMonks",
        enabled=True,
        notes=KICKOFF_CANDIDATE_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
    SportSource(
        sport="soccer",
        league_key="soccer_germany_bundesliga",
        display_name="Bundesliga",
        report_slot="global_night_preview",
        region_group="europe",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: football-data.org or API-Football",
        enabled=True,
        notes=KICKOFF_CANDIDATE_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
    SportSource(
        sport="soccer",
        league_key="soccer_uefa_champs_league",
        display_name="UEFA Champions League",
        report_slot="global_night_preview",
        region_group="europe",
        primary_odds_source=DEFAULT_PRIMARY_ODDS_SOURCE,
        secondary_schedule_source="candidate: football-data.org or API-Football",
        enabled=True,
        notes=EUROPE_CROSS_BORDER_NOTE,
        missing_data_policy=DEFAULT_MISSING_DATA_POLICY,
    ),
)


def validate_report_slot(report_slot: str) -> str:
    normalized_report_slot = report_slot.strip().lower()
    if normalized_report_slot not in REPORT_SLOT_SCHEDULES:
        supported_slots = ", ".join(REPORT_SLOTS)
        raise ValueError(f"Unknown report_slot: {report_slot}. Use one of: {supported_slots}.")
    return normalized_report_slot


def list_enabled_sources() -> list[SportSource]:
    return [source for source in SPORT_SOURCE_CATALOG if source.enabled]


def list_sources_by_report_slot(report_slot: str) -> list[SportSource]:
    normalized_report_slot = validate_report_slot(report_slot)
    return [
        source for source in list_enabled_sources() if source.report_slot == normalized_report_slot
    ]


def list_sources_by_region(region_group: str) -> list[SportSource]:
    normalized_region_group = region_group.strip().lower()
    return [
        source
        for source in list_enabled_sources()
        if source.region_group == normalized_region_group
    ]


def list_sources_by_sport(sport: str) -> list[SportSource]:
    normalized_sport = sport.strip().lower()
    return [source for source in list_enabled_sources() if source.sport == normalized_sport]


def get_source_by_league_key(league_key: str) -> SportSource:
    normalized_league_key = league_key.strip().lower()
    for source in SPORT_SOURCE_CATALOG:
        if source.league_key == normalized_league_key:
            return source
    raise KeyError(f"Unknown league_key: {league_key}.")


def get_report_slot_schedule(report_slot: str) -> ReportSlotSchedule:
    normalized_report_slot = validate_report_slot(report_slot)
    return REPORT_SLOT_SCHEDULES[normalized_report_slot]
