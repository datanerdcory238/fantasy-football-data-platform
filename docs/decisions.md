# Decision Log

Short records of *why* things are the way they are (lightweight ADRs). Add new decisions at the bottom.

---

### D-001 · Data source: Pro-Football-Reference HTML (2026-10-10)
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
**Decision:** Save every fetched page under `data/raw/` and read from that cache by default.
**Why:** It's the raw/bronze layer. Parsers can be fixed and re-run without re-scraping, and it maps directly to
S3 in Step 2. The raw files are git-ignored because they're reproducible.

### D-004 · Idempotent upserts on natural keys (2026-10-10)
**Decision:** All loads use `INSERT … ON CONFLICT DO UPDATE` on PFR's natural IDs.
**Why:** Re-runs, retries, and backfills are safe, which is a prerequisite for Airflow in Step 3.

### D-005 · Plain SQL + psycopg instead of an ORM (2026-10-10)
**Decision:** Hand-written SQL migrations and views, with psycopg 3 for access.
**Why:** The goal is to learn SQL, and the same SQL skills transfer to Athena, Databricks SQL, and Fabric.
dbt may replace `sql/models/` later.

### D-006 · Position from the season fantasy page (2026-10-10)
**Decision:** Get player positions from `/years/{season}/fantasy.htm` at player-season grain.
**Why:** Box scores don't list positions. One page per season covers every fantasy-relevant player.
**Trade-off:** Players with no fantasy stats that season have a NULL position.

### D-007 · Tests run on in-memory SQLite and fixtures (2026-10-10)
**Decision:** Parser and load tests use saved HTML fixtures and SQLite. CI also applies the real schema and views
to PostgreSQL.
**Why:** The tests are fast and need no network or DB server. SQLite supports the same upsert syntax.
