# Development Log

Newest entries at the top. Each entry covers what was done, what was learned, and what's next.

---

## 2026-10-15/16: Database created, tests passing, switching to Claude Code

**Done**
- Created `.env` with custom values: database `nfl_fantasy`, user `cholbein`, own password. `.env` is git-ignored.
- `docker compose up -d` started PostgreSQL. `python -m ffdata init-db` created the 7 tables (empty).
- `pytest -q`: **16 passed** on Cory's machine.
- Added `CLAUDE.md` (project context for Claude Code) so work can continue there.

**Learned**
- Server vs. database: `docker compose up -d` starts the PostgreSQL server (and creates the DB the first time).
  `init-db` creates tables. Data lives in a Docker volume, not the project folder. You browse it with psql or DBeaver.
- Table vs. view: fantasy points (`pts_standard`, `pts_half_ppr`, `pts_ppr`) are calculated in
  `vw_player_game_fantasy`, not stored.
- Interpreter = the `python.exe` that runs the code. `.venv` has its own interpreter with the project libraries.
- Everything in Step 1 is free. Costs start with AWS in Step 2 (set a budget alert first).

**Issues hit**
- `ModuleNotFoundError: No module named 'dotenv'` when the venv wasn't active. Fix: `.venv\Scripts\activate`.
- Ctrl+Shift+X didn't work (Bluetooth keyboard problem). Use **View → Extensions** instead.

**Next**
- [ ] Activate the venv and run the first live scrape: `python -m ffdata schedule --season 2025`.

---

## 2026-10-10 (evening): Published to GitHub + Python environment ready

**Done**
- Repo published: https://github.com/datanerdcory238/fantasy-football-data-platform (first commit `5d4e7aa`, 34 files).
- Moved `ci.yml` into `.github/workflows/` so GitHub Actions runs the tests on every push.
- Created the virtual environment `.venv` with **Python 3.15.0** and installed `requirements-dev.txt`.
  Installed versions: requests 2.34.2, beautifulsoup4 4.15.0, lxml 6.1.3, psycopg 3.3.6 (binary),
  python-dotenv 1.2.4, pytest 9.1.1. The earlier worry that Python 3.15 wouldn't be supported turned out to be fine.
- Added Git/GitHub and virtual-environment sections to [setup_windows.md](setup_windows.md).

**Learned**
- Git commands must run inside the project folder. Running `git init` in the home folder tried to track the
  whole user profile (fixed by deleting the stray `.git`/`.github` there).
- VS Code's Source Control panel is a button version of `git add` / `commit` / `push`.
- `.md` files are written instructions (Markdown) that GitHub displays as web pages. They don't run anything.
- File Explorer's "Documents" may point to OneDrive\Documents. The project is in `C:\Users\coryh\Documents`.

**Next (where to pick up)**
- [ ] Commit and push the latest doc changes.
- [ ] `docker compose up -d` → `python -m ffdata init-db`
- [ ] `pytest -q` (all 16 tests should pass)
- [ ] First live scrape: `schedule --season 2025`, `positions --season 2025`, `boxscores --season 2025 --week 1`
- [ ] Check results with SQL, then write a user guide (`docs/user_guide.md`) with example queries.

---

## 2026-10-10 (later): Development environment set up on Windows

**Done**
- Installed VS Code, Python 3.15.0, Git, and Docker Desktop. `docker run hello-world` works.
- Fixed Docker's "Virtual Machine Platform not enabled / No virtualization available" error: enabled the
  Windows features, ran `wsl --update`, and restarted the computer. See [setup_windows.md](setup_windows.md).

**Learned**
- Terminal vs. shell, text editor vs. IDE, Git vs. GitHub, and what Docker containers, images, and volumes are.

**Watch out for**
- Python 3.15 is very new, so some libraries might not support it yet. *(Update: all libraries installed fine. See the
  next entry.)*

**Next**
- [x] Create the GitHub repo, then `git init` and the first push.
- [x] Create the venv and install requirements.

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
