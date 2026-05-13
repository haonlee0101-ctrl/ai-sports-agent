# AI Sports Analyst Agent

AI Sports Analyst Agent is a Fast Track automation project for generating sports analysis reports in small, safe phases.

This repository is currently in `Phase 0`, which means we are preparing the project basics only. The application code, CLI, mock renderer, and tests for report generation will be added in later phases.

## Current Goal

Build the repository foundation for the V7.2 Fast Track workflow:

- set up project guidance and task logging
- prepare runtime and development dependencies
- define environment variable names without secrets
- configure Ruff and pre-commit
- get ready for Phase 1 mock HTML report generation

## Project Roles

- Codex: main developer
- ChatGPT: PM and senior engineer
- User: operator, approver, and secret owner

## Setup

### 1. Create and activate a virtual environment

Mac or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Install pre-commit hooks

```bash
pre-commit install
```

## Environment Variables

Copy `.env.example` to `.env` and fill in real values only on your local machine. Do not commit `.env`.

Required names for later phases:

- `API_SPORTS_KEY`
- `ODDS_API_KEY`
- `SENDGRID_API_KEY`
- `REPORT_FROM_EMAIL`
- `REPORT_TO_EMAIL`
- `OPENAI_API_KEY`
- `HEALTHCHECKS_EAST_URL`
- `HEALTHCHECKS_WEST_URL`

## Mock Run Plan

Phase 1 will add the first mock CLI and HTML output flow. These commands are planned, but they do not work yet because `run_report.py` has not been created:

```bash
python run_report.py --region east --mode mock
python run_report.py --region west --mode mock
```

Expected output files in Phase 1:

- `out/report_east.html`
- `out/report_west.html`

## Quality Commands

Format the repository:

```bash
ruff format .
```

Run lint checks:

```bash
ruff check .
```

Run tests:

```bash
pytest
```

Note: `pytest` may report that no tests ran during Phase 0 because application code and test files are not created yet.

## Safety Notes

- Never hardcode API keys, emails, tokens, or secrets.
- Treat reports as analysis content, not betting advice.
- If data is missing, mark it as missing instead of guessing.
- Do not invent injuries, lineups, player names, weather, news, or probabilities.

Forbidden expressions:

- `무조건`
- `필승`
- `확실`
- `100% 보장`
- `돈 걸어도 됨`
- `적중 확정`

## Next Phase

The next task is `Phase 1 mock HTML report`.

Planned first files:

- `run_report.py`
- `src/schemas.py`
- `src/mock_data.py`
- `src/reports/html_renderer.py`
