# CLAUDE.md: project context for Claude Code

Read this first, then `docs/dev_log.md` (newest entry at the top) for detailed history.

## About the user (Cory)
- Learning data engineering and analytics through this project. **New to developer tooling** (first time using
  Git, Docker, a terminal, and Python virtual environments).
- **Explain things in plain language. Go one step at a time** and say what each command does and what output to
  expect before running it.
- **Ask before making changes** to files, the database, or Git. Explain *why* a change is needed.
- Wants this to be a learning experience: **stop after each step**, explain the result (what the output means),
  and say what the next step will do before doing it.
- Keep documentation updated as you go: `docs/dev_log.md` for every working session, plus the other docs when
  relevant.
- Prefers the VS Code Source Control panel for commits, but knows the terminal equivalents.

## The bigger plan
This repo is Step 1 of a 14-step learning roadmap: Python + SQL → AWS → Airflow → AWS pipeline → Databricks →
Microsoft Fabric → analytics layer (dimensional model) → Power BI → AI/RAG → portfolio. The design deliberately
mirrors later stages: `data/raw/` becomes S3, CLI commands become Airflow tasks, and SQL views become gold tables.
See `README.md` (roadmap table) and `docs/architecture.md`.

## What this project does (Step 1)
Downloads open NFL data from **nflverse** (CSV files on GitHub Releases, via the GitHub API) → saves raw files to
`data/raw/nflverse/` (re-downloads only when nflverse publishes a new version) → transforms with Python → loads into
PostgreSQL (Docker) with idempotent upserts → SQL views calculate fantasy points (standard, half-PPR, PPR).
The project first scraped Pro-Football-Reference, but PFR returns 403 to automated clients; switched 2026-10-16
(`docs/decisions.md` D-008). Cory wants sources that **allow** automation. Don't suggest bypassing bot protection.

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
- [x] Switched source to nflverse; migration 002 applied; `pytest -q`: 29 passed.
- [x] Loaded **2025** (285 games incl. playoffs, 6,396 player-game rows) and **2026 through Week 6 Thursday**
  (272 games, 1,821 rows). Our fantasy points match nflverse's on every row (0 mismatches).
- [ ] **NEXT:** commit + push (Cory uses the VS Code Source Control panel). Check that CI passes on GitHub.
- [ ] Re-run `python -m ffdata stats --season 2026` after each game day (e.g. Tuesday) to add new games.
- [ ] Then: explore with SQL/DBeaver, write `docs/user_guide.md` with example queries, turn the points check into a
  repeatable data-quality command, and consider more checks (row counts per week, no NULL positions).

## Code map
| Path | Purpose |
|---|---|
| `ffdata/http.py` | `PoliteFetcher`: robots.txt, 4s delay, retries; `get_json` (APIs) and `download` (files) |
| `ffdata/sources/nflverse.py` | Extract: `find_asset` (GitHub API) + `fetch_asset` (raw file + `.meta.json`, skip if unchanged). Transform: pure CSV→row functions |
| `ffdata/teams.py` | 32 teams with nflverse abbreviations (GB, KC, LA, LV, NE, NO, SF, TB…) |
| `ffdata/db.py` | psycopg connection, migrations, `build_models`, generic `upsert`, `scrape_runs` logging |
| `ffdata/pipeline.py` | `load_games`, `load_player_stats` (games must be loaded first) |
| `ffdata/cli.py` | `python -m ffdata init-db / games / stats [--week] / season / build-models / status` |
| `sql/schema/` | Versioned migrations: 001 tables, 002 nflverse switch (2-pt, ST TD, `src_pts_*` check columns) |
| `sql/models/` | Views: `vw_player_game_fantasy`, `vw_player_season_fantasy` |
| `tests/` | pytest suite. SQLite in memory + small CSV fixtures of real nflverse rows, no network needed |

Tables: `teams`, `games`, `players`, `player_seasons`, `player_game_offense` (fact table), `scrape_runs`.
Full column definitions are in `docs/data_dictionary.md`. Design rationale is in `docs/decisions.md`.

## Conventions
- Keep loads idempotent (upsert on natural keys). Never request faster than the configured delay.
- Schema changes go in a new numbered migration (next: `sql/schema/003_*.sql`). Never edit applied migrations.
- `src_pts_standard` / `src_pts_ppr` are nflverse's points, for checking the view only (D-010).
- Fantasy points are calculated in views, not stored (decision: one source of truth). Materialize them in Step 7.
- Cory decided to keep the current table names (no `dim_`/`fact_` prefixes yet) and the current scope (no
  kickers/DST yet).
- Run `pytest -q` after code changes. Update docs and `docs/dev_log.md` with each session.
