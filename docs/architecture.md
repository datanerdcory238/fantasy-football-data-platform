# Architecture — Step 1 (local)

## Flow

```
            ┌──────────────────────────── python -m ffdata <command> ───────────────────────────┐
            │                                                                                     │
 PFR site ──► EXTRACT                  ──► RAW LAYER          ──► TRANSFORM          ──► LOAD           ──► MODEL
            │ http.PoliteFetcher         data/raw/<host>/<path>   parsers/pfr.py         db.upsert          sql/models/*.sql
            │ • robots.txt check         exact HTML as fetched    • HTML -> list[dict]   • INSERT ...       • vw_player_game_fantasy
            │ • ≥4s between requests     (cache; re-parse         • typed, cleaned         ON CONFLICT      • vw_player_season_fantasy
            │ • retries w/ backoff        without re-scraping)    • no I/O (testable)      DO UPDATE
            └──────────────────────────────── scrape_runs table logs every run ──────────────────┘
```

## Pages scraped

| Page | URL pattern | Table | Feeds |
|------|-------------|-------|-------|
| Season schedule/results | `/years/{season}/games.htm` | `#games` | `games` |
| Season fantasy page | `/years/{season}/fantasy.htm` | `#fantasy` | `players`, `player_seasons` (position) |
| Game box score | `/boxscores/{game_id}.htm` | `#player_offense` (inside an HTML comment) | `players`, `player_game_offense` |

A season costs 2 + about 285 page requests (272 regular-season games plus playoffs).

## Design principles

1. **Separate extract, transform, and load.** Fetching, parsing, and loading are separate modules, so each one
   can be tested on its own and later replaced (S3 for `data/raw`, Airflow tasks for the CLI).
2. **Keep the raw data.** If a parser bug turns up, delete the bad rows and re-run the command. Parsing reruns
   from the cache, and the site isn't hit again.
3. **Make every load idempotent.** Upserts on natural keys mean re-runs, retries, and backfills never create
   duplicates.
4. **Load incrementally.** `boxscores` only fetches completed games that have no stats yet. Use `--force` to reload.
5. **Expect partial failure.** One bad box score is logged in `scrape_runs.error` and skipped, and the run
   continues. Re-running the command retries only the missing games.
6. **Keep the schema in version control.** `sql/schema/NNN_*.sql` migrations are applied once each and tracked
   in `schema_migrations`. Views in `sql/models/` are rebuilt on demand.

## How this evolves

| Today (Step 1) | Step 2–4 (AWS + Airflow) | Step 5–6 (Databricks / Fabric) |
|---|---|---|
| `data/raw/` folder | S3 raw bucket | Bronze Delta tables |
| Python parsers | Glue / Lambda / Airflow tasks | PySpark → Silver |
| PostgreSQL tables | Athena / Redshift tables | Silver tables |
| SQL views | Curated tables | Gold tables |
| CLI run manually | Airflow DAG with schedule & retries | Databricks Jobs / Fabric pipelines |
| `scrape_runs` table | Airflow task logs + data-quality checks | Job monitoring |
