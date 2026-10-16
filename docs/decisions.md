# Decision Log

Short records of *why* things are the way they are (lightweight ADRs). Add new decisions at the bottom.

---

### D-001 · Data source: Pro-Football-Reference HTML (2026-10-10)
> **Superseded by D-008** (2026-10-16): PFR blocks automated access.

**Decision:** Scrape PFR box scores, schedules, and season fantasy pages.
**Why:** Step 1 is about learning web scraping, and PFR is the canonical HTML-table source with stable
`data-stat` attributes and player IDs.
**Trade-offs:** The rate limit is strict (20 requests/min, with temporary bans above it), some tables are hidden in
HTML comments, and the terms restrict redistribution.
**Alternatives considered:** nflverse (clean CSV/Parquet, but ingestion rather than scraping), and the ESPN/Sleeper
JSON APIs (good for fantasy-specific data later). Both are candidates for a second source.

### D-002 · Database: PostgreSQL 16 in Docker (2026-10-10)
**Decision:** Run Postgres locally with `docker compose`.
**Why:** It matches the roadmap, it's the most common open-source warehouse-style DB, and it has no install
footprint. It can be reset with `docker compose down -v`.

### D-003 · Keep raw HTML on disk (2026-10-10)
> Still applies with nflverse: the raw files are now CSVs under `data/raw/nflverse/` (see D-009).

**Decision:** Save every fetched page under `data/raw/` and read from that cache by default.
**Why:** It's the raw/bronze layer. Parsers can be fixed and re-run without re-scraping, and it maps directly to
S3 in Step 2. The raw files are git-ignored because they're reproducible.

### D-004 · Idempotent upserts on natural keys (2026-10-10)
**Decision:** All loads use `INSERT … ON CONFLICT DO UPDATE` on the source's natural IDs (PFR's at first,
nflverse's since D-008).
**Why:** Re-runs, retries, and backfills are safe, which is a prerequisite for Airflow in Step 3.

### D-005 · Plain SQL + psycopg instead of an ORM (2026-10-10)
**Decision:** Hand-written SQL migrations and views, with psycopg 3 for access.
**Why:** The goal is to learn SQL, and the same SQL skills transfer to Athena, Databricks SQL, and Fabric.
dbt may replace `sql/models/` later.

### D-006 · Position from the season fantasy page (2026-10-10)
> **Superseded by D-011** (2026-10-16).

**Decision:** Get player positions from `/years/{season}/fantasy.htm` at player-season grain.
**Why:** Box scores don't list positions. One page per season covers every fantasy-relevant player.
**Trade-off:** Players with no fantasy stats that season have a NULL position.

### D-007 · Tests run on in-memory SQLite and fixtures (2026-10-10)
> Still applies; since D-008 the fixtures are small CSVs of real nflverse rows in `tests/fixtures/nflverse/`.

**Decision:** Parser and load tests use saved HTML fixtures and SQLite. CI also applies the real schema and views
to PostgreSQL.
**Why:** The tests are fast and need no network or DB server. SQLite supports the same upsert syntax.

### D-008 · Data source: nflverse instead of Pro-Football-Reference (2026-10-16)
**Decision:** Load games and weekly player stats from [nflverse](https://github.com/nflverse/nflverse-data),
open NFL data published as CSV files on GitHub Releases.
**Why:** The first live run against PFR returned **HTTP 403 Forbidden**. A browser-like User-Agent was also
blocked, so PFR's bot protection (Cloudflare) checks more than the label. Getting around that would mean
disguising the scraper, which goes against the site's wishes and risks an IP ban. The project will be automated
(Airflow in Step 3), so the source must *allow* automated access. nflverse is published for programmatic use,
is updated roughly daily during the season, and is open data (credit nflverse).
**Trade-offs:** Less HTML-scraping practice (Step 1 becomes file/API ingestion, which is closer to what the
later AWS/Airflow steps do). Four PFR columns aren't available (`pass_long`, `pass_rating`, `rush_long`,
`rec_long`; they stay NULL). IDs change format: players `00-0023459`, games `2026_05_IND_PIT`, teams `GB`/`KC`/`LA`.
**Gains:** ~4 file downloads per season instead of ~290 page requests; 2-point conversions and special-teams TDs
are available; nflverse's own fantasy points give us a free check of our scoring (D-010).

### D-009 · Download through the GitHub API, only when a file changed (2026-10-16)
**Decision:** Find files with the GitHub REST API (`api.github.com/repos/nflverse/nflverse-data/releases/tags/<tag>`)
and download them by asset ID. Keep a `.meta.json` next to each raw file with the version (`updated_at`) we saved;
skip the download when it matches.
**Why:** GitHub's robots.txt has `Disallow: /*/download` for automated clients and points to its API instead.
(Python's `robotparser` doesn't understand `*` wildcards, so our check would have missed this; read robots.txt
yourself for new sources.) The API also reports when each file changed, which makes incremental loading easy.
**Limits:** 60 API requests/hour without a login; a season load uses ~6. A free GitHub token raises it to 5,000
if needed later.

### D-010 · Keep nflverse's fantasy points for checking only (2026-10-16)
**Decision:** Store nflverse's `fantasy_points` / `fantasy_points_ppr` as `src_pts_standard` / `src_pts_ppr` in
`player_game_offense`.
**Why:** Comparing them with `vw_player_game_fantasy` is a data-quality check on our scoring logic. First result:
0 mismatches across all 8,217 rows of 2025 and 2026. The official numbers are still the ones our view calculates
(fantasy points are calculated in views, per the project convention); these columns are never used for
analysis.

### D-011 · Position and team from the weekly stats file (2026-10-16)
**Decision:** Keep players whose nflverse `position_group` is QB/RB/WR/TE (so fullbacks count as RB, as on
fantasy sites). In `player_seasons`, team and position come from the player's most recent game that season,
and age is age on Sept 1 (birth dates from nflverse `players.csv`).
**Why:** The stats file already lists position and team on every row, so no extra season page is needed.
Building `player_seasons` from the whole season file means loading a single week can't overwrite a traded
player's latest team with an older one.
