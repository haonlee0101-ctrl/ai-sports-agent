# AGENTS

## Project Mode

This repository follows the AI Sports Analyst Agent V7.2 Fast Track operating model.

- Codex is the main developer.
- ChatGPT is the PM and senior engineer.
- The user is the operator and approval owner.
- Work in small, safe steps instead of building the whole system at once.

## Codex Working Rules

1. Do not build the full application in one task.
2. Prefer small edits and keep each task focused on a narrow scope.
3. State which files will change before editing them.
4. Never hardcode API keys, emails, tokens, or secrets.
5. Store only environment variable names in `.env.example`.
6. Do not invent sports facts, injuries, lineups, weather, news, or probabilities.
7. If data is missing, mark it as `missing`, `unavailable`, or `확인 불가`.
8. Treat reports as analysis content, not betting advice.
9. Do not use forbidden expressions:
   - `무조건`
   - `필승`
   - `확실`
   - `100% 보장`
   - `돈 걸어도 됨`
   - `적중 확정`
10. After each task, run `ruff format .`, `ruff check .`, and `pytest`, or record why they could not run.
11. End every task update with `NEXT TASK REMINDER`.

## GPT Analyst Fast Track Rules

GPT Analyst is a structured analysis helper for Fast Track phases. It may:

- summarize games from normalized input data
- assign approved labels
- explain missing data
- describe risk and caution points
- produce reader-friendly analysis text

GPT Analyst must not:

- collect schedules directly
- call odds providers directly
- crawl news
- guess injuries or lineups
- guess weather
- create unsupported probabilities
- send email
- write SQLite records
- access GitHub secrets

If GPT Analyst output fails validation, the project should fall back to a deterministic or placeholder analyst result.

## Current Fast Track Order

The current build order is:

`Mock HTML -> ReportInput/AnalysisOutput contracts -> GPT Analyst + fallback analyst -> Analysis Validator -> SendGrid -> SQLite -> Live Collector -> GitHub Actions + Healthchecks -> Dry Run`

## Approved Environment Variables

- `API_SPORTS_KEY`
- `ODDS_API_KEY`
- `SENDGRID_API_KEY`
- `REPORT_FROM_EMAIL`
- `REPORT_TO_EMAIL`
- `OPENAI_API_KEY`
- `HEALTHCHECKS_EAST_URL`
- `HEALTHCHECKS_WEST_URL`

## NEXT TASK REMINDER Format

Use this block at the end of every task handoff:

```text
NEXT TASK REMINDER
- Completed task:
- Changed files:
- Commands run:
- Test result:
- Remaining issue:
- Next task:
- Files likely involved:
- Exact command to start:
- Prompt to give Codex next:
```

## Phase 0 Focus

Phase 0 is limited to repository basics only:

- docs and operating guidance
- dependency files
- local environment examples
- lint and pre-commit setup

Do not create `run_report.py`, `src/` modules, or application tests during Phase 0.
