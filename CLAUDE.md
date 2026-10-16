# CLAUDE.md: project context for Claude Code

Read this first, then `docs/dev_log.md` (newest entry at the top) for detailed history.

## About the user (Cory)
- Learning data engineering and analytics through this project. **New to developer tooling** (first time using
  Git, Docker, a terminal, and Python virtual environments).
- **Explain things in plain language. Go one step at a time** and say what each command does and what output to
  expect before running it.
- **Ask before making changes** to files, the database, or Git. Explain *why* a change is needed.
- Keep documentation updated as you go: `docs/dev_log.md` for every working session, plus the other docs when
  relevant.
- Prefers the VS Code Source Control panel for commits, but knows the terminal equivalents.

## The bigger plan
This repo is Step 1 of a 14-step learning roadmap: Python + SQL → AWS → Airflow → AWS pipeline → Databricks →
Microsoft Fabric → analytics layer (dimensional model) → Power BI → AI/RAG → portfolio. The design deliberately
mirrors later stages: `data/raw/` becomes S3, CLI commands become Airflow tasks, and SQL views become gold tables.
See `README.md` (roadmap table) and `docs/architecture.md`.

## What this project does (Step 1)
Scrapes NFL data from Pro-Football-Reference (PFR) → saves raw HTML to `data/raw/` → parses it with Python → loads it
into PostgreSQL (Docker) with idempotent upserts → SQL views calculate fantasy points (standard, half-PPR, PPR).

## Environment (Windows 11, x64 Intel)
- Project path: `C:\Users\coryh\Documents\fantasy-football-data-platform`. This is NOT `OneDrive\Documents`.
- Python **3.15.0**, virtual environment at `.venv`. Activate with `.venv\Scripts\activate` (PowerShell). All
  requirements are installed. If you see `ModuleNotFoundError`, the venv isn't active.
- Docker Desktop must be running ("Engine running") before `docker compose up -d`. The container is `ffdata-postgres`.
- **Cory's `.env` uses custom values** (not the defaults in `.env.example`): `POSTGRES_DB=nfl_fantasy`,
  `POSTGRES_USER=cholbein`, and his own password. Use these names in psql or DBeaver commands, e.g.
  `docker exec -it ffdata-postgres psql -U cholbein -d nfl_fantasy`. Never commit `.env` or print the password.
- GitHub: https://github.com/datanerdcory238/fantasy-football-data-platform (branch `main`). CI runs `pytest` and
  `init-db` on every push (`.github/workflows/ci.yml`).

## Current status (as of 2026-10-16)
- [x] Repo created and pushed. Docs written.
- [x] venv created and dependencies installed.
- [x] `docker compose up -d` and `python -m ffdata init-db`: the 7 tables exist (empty) in `nfl_fantasy`.
- [x] `pytest -q`: 16 passed.
- [ ] **NEXT: first live scrape.** `python -m ffdata schedule --season 2025` hit `ModuleNotFoundError: dotenv` because
  the venv wasn't active. Activate it and re-run. Then: `positions --season 2025`, `boxscores --season 2025 --week 1`,
  `build-models`, `status`.
- [ ] **The parsers have never run against the live PFR site.** They were built against hand-made fixtures that
  mirror PFR's markup (`data-stat` attributes; tables hidden in HTML comments). If parsing fails, save the real
  page from `data/raw/` as a new fixture in `tests/fixtures/`, fix `ffdata/parsers/pfr.py`, and add a test.
- [ ] Then: query results (SQL/DBeaver), write `docs/user_guide.md` with example queries, backfill the full 2025
  season, add data-quality checks.

## Code map
| Path | Purpose |
|---|---|
| `ffdata/http.py` | `PoliteFetcher`: robots.txt, 4s rate limit (PFR bans >20 req/min), retries, raw cache |
| `ffdata/parsers/pfr.py` | Pure HTML→dict parsers: schedule, box score `player_offense`, season fantasy positions |
| `ffdata/teams.py` | PFR franchise code ↔ abbreviation map (crd↔ARI etc.) |
| `ffdata/db.py` | psycopg connection, migrations, `build_models`, generic `upsert`, `scrape_runs` logging |
| `ffdata/pipeline.py` | Extract→transform→load steps |
| `ffdata/cli.py` | `python -m ffdata init-db / schedule / positions / boxscores / season / build-models / status` |
| `sql/schema/` | Versioned table migrations (applied once, tracked in `schema_migrations`) |
| `sql/models/` | Views: `vw_player_game_fantasy`, `vw_player_season_fantasy` |
| `tests/` | pytest suite. Uses SQLite in memory + HTML fixtures, no network needed |

Tables: `teams`, `games`, `players`, `player_seasons`, `player_game_offense` (fact table), `scrape_runs`.
Full column definitions are in `docs/data_dictionary.md`. Design rationale is in `docs/decisions.md`.

## Conventions
- Keep loads idempotent (upsert on natural keys). Never hit PFR faster than the configured delay.
- Schema changes go in a new numbered migration (`sql/schema/002_*.sql`). Don't edit 001 after data exists.
- Fantasy points are calculated in views, not stored (decision: one source of truth). Materialize them in Step 7.
- Cory decided to keep the current table names (no `dim_`/`fact_` prefixes yet) and the current scope (no
  kickers/DST yet).
- Run `pytest -q` after code changes. Update docs and `docs/dev_log.md` with each session.
