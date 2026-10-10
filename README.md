# Fantasy Football Data Platform

An end-to-end NFL / fantasy-football data platform, built step by step as a hands-on path through
data engineering, analytics, and applied AI.

**Current stage: Step 1 – Python + SQL data engineering foundations.**
This stage scrapes NFL game and player data from Pro-Football-Reference, keeps the raw HTML, parses it
with Python, loads it into PostgreSQL with idempotent upserts, and builds SQL models for weekly and
season fantasy scoring.

```
 Pro-Football-Reference ──► PoliteFetcher ──► data/raw/ (raw HTML)  ──► parsers ──► PostgreSQL ──► SQL views
   (games, box scores,      robots.txt,        "bronze" layer,           pure          tables        fantasy points
    fantasy positions)      rate limit, retry  re-parseable              functions     (upserts)     per game / season
```

## Roadmap

| # | Stage | Status |
|---|-------|--------|
| 1 | Python + SQL foundations: scraper → PostgreSQL → SQL models | 🟡 In progress |
| 2 | AWS data engineering (raw data → S3, Glue/Athena) | ⬜ |
| 3 | Apache Airflow orchestration | ⬜ |
| 4 | AWS NFL data pipeline | ⬜ |
| 5 | Databricks (bronze/silver/gold) | ⬜ |
| 6 | Microsoft Fabric | ⬜ |
| 7 | Analytics layer (dimensional model) | ⬜ |
| 8 | Power BI dashboards | ⬜ |
| 9–13 | AI integration, RAG, GenAI analytics | ⬜ |
| 14 | Portfolio packaging | ⬜ |

## Quick start

**Prerequisites:** Python 3.11+, Git, and Docker Desktop.

```bash
# 1. Python environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# 2. Config + database
cp .env.example .env               # Windows: copy .env.example .env
docker compose up -d               # starts PostgreSQL 16 on localhost:5432
python -m ffdata init-db           # creates tables + views

# 3. Scrape (start small — each page waits ~4s to be polite)
python -m ffdata schedule  --season 2025
python -m ffdata positions --season 2025
python -m ffdata boxscores --season 2025 --week 1
python -m ffdata build-models
python -m ffdata status

# 4. Run tests
pytest -q
```

A full regular season is about 270 box scores, which takes roughly 20 minutes at the polite rate.
Re-running a command is always safe: cached pages aren't re-downloaded, and upserts don't create duplicates.

## Try some SQL

```bash
docker exec -it ffdata-postgres psql -U fantasy -d fantasy
```

```sql
-- Top 10 PPR performances of week 1
SELECT player_name, position, team_abbr, opponent, pts_ppr
FROM vw_player_game_fantasy
WHERE season = 2025 AND week = 1
ORDER BY pts_ppr DESC
LIMIT 10;
```

## Repository layout

```
ffdata/               Python package
  config.py           settings from .env
  http.py             polite fetcher (robots.txt, rate limit, retries, raw cache)
  parsers/pfr.py      HTML -> rows (pure functions)
  teams.py            team code/abbreviation reference data
  db.py               connection, migrations, models, upserts, run log
  pipeline.py         extract -> transform -> load steps
  cli.py              `python -m ffdata ...`
sql/schema/           versioned table migrations (applied once each)
sql/models/           SQL views rebuilt on demand (fantasy scoring)
tests/                pytest suite + HTML fixtures (no network needed)
docs/                 architecture, data dictionary, decisions, dev log
data/raw/             cached raw HTML (git-ignored)
```

## Documentation

- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data_dictionary.md)
- [Decision log](docs/decisions.md)
- [Development log](docs/dev_log.md)
- [Learning notes – Step 1 concepts](docs/learning_notes.md)
- [Windows setup & troubleshooting](docs/setup_windows.md)

## Data source & etiquette

Data comes from [Pro-Football-Reference](https://www.pro-football-reference.com/) (Sports Reference LLC).
This project is personal and educational. The scraper identifies itself, checks `robots.txt`,
stays under Sports Reference's published limit of 20 requests per minute, and caches every page so it is
downloaded only once. Please review Sports Reference's
[terms of use](https://www.sports-reference.com/termsofuse.html) and
[bot policy](https://www.sports-reference.com/bot-traffic.html) before running it, and don't redistribute their data.
