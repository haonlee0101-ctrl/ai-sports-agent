from __future__ import annotations

from collections import Counter
from html import escape

from src.schemas import GameReport, ReportPayload


def _display_text(value: str | None) -> str:
    if value is None:
        return "missing"
    cleaned = value.strip()
    if not cleaned:
        return "missing"
    return escape(cleaned)


def _render_list(items: list[str]) -> str:
    cleaned_items = [escape(item.strip()) for item in items if item.strip()]
    if not cleaned_items:
        return "<li>missing</li>"
    return "".join(f"<li>{item}</li>" for item in cleaned_items)


def _render_game_card(game: GameReport) -> str:
    matchup = f"{escape(game.away_team)} at {escape(game.home_team)}"
    return f"""
    <article class="game-card">
      <div class="game-card__header">
        <p class="label-badge">{escape(game.label)}</p>
        <h3>{matchup}</h3>
        <p class="meta">{escape(game.league)} | {escape(game.match_time_local)}</p>
      </div>
      <div class="game-card__body">
        <section>
          <h4>Analysis Summary</h4>
          <p>{escape(game.analysis_summary)}</p>
        </section>
        <section>
          <h4>Watch Points</h4>
          <ul>{_render_list(game.watch_points)}</ul>
        </section>
        <section>
          <h4>Risk Factors</h4>
          <ul>{_render_list(game.risk_factors)}</ul>
        </section>
        <section>
          <h4>Market Note</h4>
          <p>{_display_text(game.market_note)}</p>
        </section>
        <section>
          <h4>Missing Data</h4>
          <ul>{_render_list(game.missing_data)}</ul>
        </section>
      </div>
      <footer class="game-card__footer">game_id: {escape(game.game_id)}</footer>
    </article>
    """


def render_report_html(report: ReportPayload | dict) -> str:
    report_model = (
        report if isinstance(report, ReportPayload) else ReportPayload.model_validate(report)
    )
    label_counts = Counter(game.label for game in report_model.games)
    label_summary = "".join(
        f"<li><strong>{escape(label)}</strong>: {count}</li>"
        for label, count in sorted(label_counts.items())
    )
    game_cards = "".join(_render_game_card(game) for game in report_model.games)

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{escape(report_model.title)}</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f5f0e8;
        --surface: #fffaf3;
        --surface-strong: #fff;
        --ink: #1e1f24;
        --muted: #5f6675;
        --accent: #b45f06;
        --line: #dfd4c4;
        --shadow: 0 12px 28px rgba(32, 24, 10, 0.08);
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top, rgba(180, 95, 6, 0.12), transparent 35%),
          linear-gradient(180deg, #f8f4ec 0%, #f2ebe0 100%);
      }}

      .page {{
        max-width: 1080px;
        margin: 0 auto;
        padding: 32px 20px 48px;
      }}

      .hero {{
        background: var(--surface-strong);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 28px;
        box-shadow: var(--shadow);
      }}

      .hero h1 {{
        margin: 0 0 8px;
        font-size: clamp(2rem, 5vw, 3.25rem);
        line-height: 1.05;
      }}

      .hero p {{
        margin: 10px 0;
        color: var(--muted);
      }}

      .meta-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin-top: 20px;
      }}

      .meta-card,
      .summary-card,
      .game-card {{
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 20px;
        box-shadow: var(--shadow);
      }}

      .meta-card {{
        padding: 16px;
      }}

      .meta-card strong {{
        display: block;
        margin-bottom: 6px;
      }}

      .section-title {{
        margin: 30px 0 14px;
        font-size: 1.25rem;
      }}

      .summary-card {{
        padding: 20px;
      }}

      .summary-card ul,
      .game-card ul {{
        margin: 10px 0 0;
        padding-left: 20px;
      }}

      .games {{
        display: grid;
        gap: 18px;
      }}

      .game-card {{
        overflow: hidden;
      }}

      .game-card__header {{
        padding: 20px 20px 12px;
        background: linear-gradient(135deg, rgba(180, 95, 6, 0.12), rgba(255, 250, 243, 0.95));
        border-bottom: 1px solid var(--line);
      }}

      .game-card__header h3 {{
        margin: 10px 0 6px;
        font-size: 1.35rem;
      }}

      .label-badge {{
        display: inline-block;
        margin: 0;
        padding: 6px 12px;
        border-radius: 999px;
        background: rgba(180, 95, 6, 0.14);
        color: #7b3d00;
        font-size: 0.9rem;
        font-weight: 700;
      }}

      .meta {{
        margin: 0;
        color: var(--muted);
      }}

      .game-card__body {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        padding: 18px 20px 20px;
      }}

      .game-card__body section {{
        min-width: 0;
      }}

      .game-card__body h4 {{
        margin: 0 0 8px;
        font-size: 1rem;
      }}

      .game-card__body p {{
        margin: 0;
        line-height: 1.55;
      }}

      .game-card__footer {{
        padding: 12px 20px 18px;
        color: var(--muted);
        font-size: 0.9rem;
      }}

      @media (max-width: 640px) {{
        .page {{
          padding: 20px 14px 36px;
        }}

        .hero,
        .summary-card,
        .game-card__header,
        .game-card__body,
        .game-card__footer {{
          padding-left: 16px;
          padding-right: 16px;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      <header class="hero">
        <h1>{escape(report_model.title)}</h1>
        <p>{escape(report_model.overview)}</p>
        <p>{escape(report_model.disclaimer)}</p>
        <div class="meta-grid">
          <div class="meta-card">
            <strong>Region</strong>
            <span>{escape(report_model.region.upper())}</span>
          </div>
          <div class="meta-card">
            <strong>Mode</strong>
            <span>{escape(report_model.mode)}</span>
          </div>
          <div class="meta-card">
            <strong>Generated At</strong>
            <span>{escape(report_model.generated_at)}</span>
          </div>
          <div class="meta-card">
            <strong>Games</strong>
            <span>{len(report_model.games)}</span>
          </div>
        </div>
      </header>

      <section>
        <h2 class="section-title">Label Summary</h2>
        <div class="summary-card">
          <ul>{label_summary}</ul>
        </div>
      </section>

      <section>
        <h2 class="section-title">Game Analysis</h2>
        <div class="games">
          {game_cards}
        </div>
      </section>
    </main>
  </body>
</html>
"""
