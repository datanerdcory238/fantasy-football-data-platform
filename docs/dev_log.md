# Development Log

Newest entries at the top. Each entry covers what was done, what was learned, and what's next.

---

## 2026-10-16: PFR blocked us, switched to nflverse, loaded 2025 + 2026

**Done**
- First live run against Pro-Football-Reference: **HTTP 403 Forbidden**. Tried a browser User-Agent in `.env`:
  still 403 (bot protection checks more than the label). Put the honest User-Agent back.
- Decided to switch to **nflverse** (open data, CC-BY 4.0, updated ~daily in season) because the project will be
  automated and needs a source that allows it. Decisions D-008 to D-011 in `decisions.md`.
- Found that GitHub's robots.txt disallows `/*/download` for bots, so files are fetched through the **GitHub API**.
  Each raw file gets a `.meta.json` with its nflverse version, so unchanged files aren't downloaded again.
- Code: new `ffdata/sources/nflverse.py`; `http.py` gained `get_json` and `download`; `pipeline.py` and `cli.py`
  now have `games`, `stats [--week]`, `season`; `teams.py` uses nflverse abbreviations; PFR parser code removed.
- Migration `002_nflverse_source.sql`: cleared the old PFR team rows; added `pass_2pt`, `rush_2pt`, `rec_2pt`,
  `st_td`, and `src_pts_standard` / `src_pts_ppr` (nflverse's points, for checking only). The view now scores
  2-point conversions (+2) and special-teams TDs (+6).
- Tests rewritten around small CSV fixtures of real rows (Rodgers, Aaron Jones, Mike Evans, a FB, a K, an LB):
  `pytest -q` → **29 passed**.
- Loaded data, one step at a time:
  - 2026 Week 5 → 346 rows; then all of 2026 → 1,821 rows (weeks 1–5 + Thursday of week 6), 272 games.
  - 2025 full season → 285 games (272 REG + 13 playoff), 6,396 rows.
  - **Data-quality check: our points = nflverse's points on all 8,217 rows (0 mismatches).**
- 2025 PPR leaders (regular season): McCaffrey 416.6, Nacua 375.0, Bijan Robinson 370.8.

**Learned**
- Reading a traceback: the **last line** is the actual error. `403` = "understood, but refused".
- User-Agent = the label a client sends to identify itself. Bot protection can also check connection
  fingerprints and run JavaScript challenges, which is why changing the label alone didn't work.
- robots.txt rules use `*` wildcards that Python's `robotparser` doesn't understand, so read it yourself for new sources.
- An **API** is a door built for programs. GitHub's API also says *when* a file last changed, which enables
  **incremental loading** (we saw it: `pages_cached: 2`, nothing downloaded). nflverse republished `games.csv`
  two minutes after our first load, and the pipeline correctly downloaded the new version.
- **Upserts in practice**: reloading Week 5 inside the full-season load updated 346 rows instead of duplicating them.
- **Migrations** are the database's version history (`schema_migrations`). `ALTER TABLE ... ADD COLUMN` adds
  columns at the end.
- Timestamps in the database are **UTC** (4 hours ahead of Eastern time in October).
- **Python 3.15** now refuses to parse a date without a year (`"September 8"`) because Feb 29 would be ambiguous.
  A language upgrade can break code that hasn't changed (this hit the old PFR parser, now removed).
- **Fakes in tests** must keep up with the real thing: adding a `headers=` argument broke the fake HTTP session.
- Scoring formats change who's valuable: Gibbs and Nacua tied at 37.7 PPR in 2026 Week 5, but Gibbs led by 12 in
  standard. Compare players across seasons with **per-game** numbers, not totals.

**Next**
- [ ] Commit and push; check CI on GitHub.
- [ ] Re-run `python -m ffdata stats --season 2026` after each game day.
- [ ] Explore the data in SQL/DBeaver; write `docs/user_guide.md`; make the points check a repeatable command.

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
