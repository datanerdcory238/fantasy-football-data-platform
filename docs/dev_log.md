# Development Log

Newest entries at the top. Each entry covers what was done, what was learned, and what's next.

---

## 2026-10-10 (later): Development environment set up on Windows

**Done**
- Installed VS Code, Python 3.15.0, Git, and Docker Desktop. `docker run hello-world` works.
- Fixed Docker's "Virtual Machine Platform not enabled / No virtualization available" error: enabled the
  Windows features, ran `wsl --update`, and restarted the computer. See [setup_windows.md](setup_windows.md).

**Learned**
- Terminal vs. shell, text editor vs. IDE, Git vs. GitHub, and what Docker containers, images, and volumes are.

**Watch out for**
- Python 3.15 is very new, so some libraries (psycopg, lxml) may not have Windows packages for it yet. If
  `pip install` fails, install Python 3.13 alongside it and create the venv with `py -3.13 -m venv .venv`.

**Next**
- [ ] Create the GitHub repo, then `git init` and the first push.
- [ ] Create the venv, install requirements, `docker compose up -d`, `python -m ffdata init-db`.
- [ ] First live scrape: `schedule` and `boxscores --week 1` for 2025.

---

## 2026-10-10 — Step 1 kickoff: repo scaffold + first scraper

**Built**
- Repo structure, `.env` config, and Docker Compose PostgreSQL 16.
- `PoliteFetcher`: robots.txt check, 4 s rate limit, retries with exponential backoff, and a raw HTML cache in `data/raw/`.
- PFR parsers for the season schedule (`games`), box-score offense (`player_offense`, including tables hidden in
  HTML comments), and season fantasy positions.
- Schema migration `001_initial_tables.sql`: teams, games, players, player_seasons, player_game_offense,
  scrape_runs.
- SQL models: `vw_player_game_fantasy` (standard, half-PPR, and PPR points) and `vw_player_season_fantasy`.
- CLI commands: `init-db`, `schedule`, `positions`, `boxscores`, `season`, `build-models`, `status`.
- Tests for the parsers, fetcher, and loader (idempotency, incremental loading, failure handling), plus a GitHub
  Actions CI workflow.

**Verified**
- 16 tests pass.
- The schema and views apply cleanly on PostgreSQL 16, and fantasy points from the fixture data match hand
  calculations (e.g. 6 rec / 110 yds / 1 TD = 17.0 std, 20.0 half, 23.0 PPR).

**Not yet verified**
- No live run against pro-football-reference.com yet. The parsers were built against PFR's known page structure
  (`data-stat` attributes). The first real run of `schedule` and `boxscores --week 1` will confirm it.

**Next**
- [ ] Run `schedule`, `positions`, and `boxscores --week 1` for 2025 and check the results with SQL.
- [ ] If PFR markup differs, save the real page as a new fixture, fix the parser, and add a test.
- [ ] Backfill the full 2025 season, then 2024.
- [ ] Add data-quality checks (e.g. team passing yards in box scores vs. team totals; no orphan rows).
- [ ] Add kicking and defense, team game stats, and snap counts.
- [ ] Write the first analysis queries: weekly top scorers, target share, consistency.
