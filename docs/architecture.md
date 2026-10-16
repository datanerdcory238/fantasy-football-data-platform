# Architecture — Step 1 (local)

## Flow

```
               ┌──────────────────────────── python -m ffdata <command> ────────────────────────────┐
               │                                                                                       │
 nflverse    ──► EXTRACT                   ──► RAW LAYER              ──► TRANSFORM            ──► LOAD           ──► MODEL
 (GitHub        │ sources/nflverse.py         data/raw/nflverse/         sources/nflverse.py      db.upsert          sql/models/*.sql
  Releases,     │ • ask the GitHub API         <release>/<file>.csv       • CSV -> list[dict]      • INSERT ...       • vw_player_game_fantasy
  via API)      │   which version is newest    + .meta.json (version)     • rename, filter,          ON CONFLICT      • vw_player_season_fantasy
               │ • download only if changed   exact file as downloaded     sum fumbles              DO UPDATE
               │ • http.PoliteFetcher:        (re-transform without      • no I/O (testable)
               │   robots.txt, ≥4s delay,      downloading again)
               │   retries w/ backoff
               └──────────────────────────────── scrape_runs table logs every run ────────────────────┘
```

## Files loaded

| nflverse file | Release tag | Size | Feeds |
|---|---|---|---|
| `games.csv` (every game since 1999) | `schedules` | ~2 MB | `teams` check, `games` |
| `stats_player_week_<season>.csv` | `stats_player` | ~9 MB per full season | `players`, `player_seasons`, `player_game_offense` |
| `players.csv` (every player) | `players` | ~7 MB | birth dates → `player_seasons.age` |

Each file costs 2 API requests: one to look up the release (file list + `updated_at`), one to download. A full
season load (`season --season N`) is 6 requests; files that haven't changed since the last run are not downloaded
again. Unauthenticated GitHub API limit: 60 requests/hour.

## Commands

| Command | Does |
|---|---|
| `init-db` | Apply new migrations in `sql/schema/`, rebuild views |
| `games --season N` | Load the 32 teams and every game of season N (played and upcoming) |
| `stats --season N [--week W]` | Load players, player seasons, and player-game stats (games must be loaded first) |
| `season --season N` | `games` + `stats` + `build-models` |
| `build-models` | Rebuild the views in `sql/models/` |
| `status` | Row counts and the last 10 runs |

## Design principles

1. **Separate extract, transform, and load.** Downloading, transforming, and loading are separate functions, so
   each one can be tested on its own and later replaced (S3 for `data/raw`, Airflow tasks for the CLI).
2. **Keep the raw data.** If a transform bug turns up, fix it and re-run the command. The CSVs are read from
   `data/raw/` and nflverse isn't contacted for a new download unless the file changed.
3. **Make every load idempotent.** Upserts on natural keys mean re-runs, retries, and backfills never create
   duplicates.
4. **Load incrementally.** Each raw file has a `.meta.json` with the nflverse version saved; unchanged files are
   reused. Re-running `stats` during the season picks up new games and stat corrections.
5. **Respect the source.** Use sources that allow automated access, follow robots.txt, prefer an official API,
   and identify the client honestly (see D-008, D-009 in `decisions.md`).
6. **Check the data.** nflverse's own fantasy points are stored next to the stats so the scoring view can be
   verified with one query (see `data_dictionary.md`).
7. **Keep the schema in version control.** `sql/schema/NNN_*.sql` migrations are applied once each and tracked
   in `schema_migrations`. Views in `sql/models/` are rebuilt on demand.

## How this evolves

| Today (Step 1) | Step 2–4 (AWS + Airflow) | Step 5–6 (Databricks / Fabric) |
|---|---|---|
| `data/raw/` folder | S3 raw bucket | Bronze Delta tables |
| Python transforms | Glue / Lambda / Airflow tasks | PySpark → Silver |
| PostgreSQL tables | Athena / Redshift tables | Silver tables |
| SQL views | Curated tables | Gold tables |
| CLI run manually | Airflow DAG with schedule & retries | Databricks Jobs / Fabric pipelines |
| `scrape_runs` table | Airflow task logs + data-quality checks | Job monitoring |
