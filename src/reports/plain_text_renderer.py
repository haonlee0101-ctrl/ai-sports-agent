from __future__ import annotations

import re
from html import unescape

from src.schemas import ReportPayload


def render_plain_text_report(report_or_html: ReportPayload | dict | str) -> str:
    if isinstance(report_or_html, str):
        return _render_from_html(report_or_html)

    report = (
        report_or_html
        if isinstance(report_or_html, ReportPayload)
        else ReportPayload.model_validate(report_or_html)
    )
    return _render_from_payload(report)


def _render_from_payload(report: ReportPayload) -> str:
    lines = [
        report.title,
        f"Region: {report.region.upper()}",
        f"Generated At: {report.generated_at}",
        f"Mode: {report.mode}",
        "",
        report.overview,
        report.disclaimer,
        "",
    ]

    for game in report.games:
        lines.extend(
            [
                f"[{game.label}] {game.away_team} at {game.home_team}",
                f"League: {game.league}",
                f"Start: {game.match_time_local}",
                f"Summary: {game.analysis_summary}",
                "Watch Points:",
                *_format_list(game.watch_points),
                "Risk Factors:",
                *_format_list(game.risk_factors),
                f"Market Note: {_display_text(game.market_note)}",
                "Missing Data:",
                *_format_list(game.missing_data),
                "",
            ]
        )

    return "\n".join(lines).strip()


def _render_from_html(html: str) -> str:
    normalized = html
    for marker in (
        "</p>",
        "</li>",
        "</h1>",
        "</h2>",
        "</h3>",
        "</h4>",
        "</div>",
        "</section>",
        "</article>",
        "<br>",
        "<br/>",
        "<br />",
    ):
        normalized = normalized.replace(marker, f"{marker}\n")

    text = re.sub(r"<[^>]+>", "", normalized)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _format_list(items: list[str]) -> list[str]:
    if not items:
        return ["- missing"]
    return [f"- {item}" for item in items]


def _display_text(value: str | None) -> str:
    if value is None:
        return "missing"
    cleaned = value.strip()
    if not cleaned:
        return "missing"
    return cleaned
