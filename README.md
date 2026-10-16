# Fantasy Football Data Platform

An end-to-end NFL / fantasy-football data platform, built step by step as a hands-on path through
data engineering, analytics, and applied AI.

**Current stage: Step 1 – Python + SQL data engineering foundations.**
This stage downloads open NFL game and player data from [nflverse](https://github.com/nflverse/nflverse-data)
through the GitHub API, keeps the raw files, transforms them with Python, loads them into PostgreSQL with
idempotent upserts, and builds SQL models for weekly and season fantasy scoring.

```
 nflverse (GitHub API) ──► PoliteFetcher ──► data/raw/ (raw CSV)    ──► transforms ──► PostgreSQL ──► SQL views
   (games, weekly           robots.txt,        "bronze" layer;           pure            tables        fantasy points
    player stats, players)  rate limit, retry  download only if changed  functions       (upserts)     per game / season
```

## Roadmap

| # | Stage | Status |
|---|-------|--------|
| 1 | Python + SQL foundations: ingestion → PostgreSQL → SQL models | 🟡 In progress |
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

**Prerequisites:** Python 3.11+ (tested on 3.15), Git, and Docker Desktop. On Windows, see [docs/setup_windows.md](docs/setup_windows.md).

```bash
# 1. Python environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# 2. Config + database
cp .env.example .env               # Windows: copy .env.example .env
docker compose up -d               # starts PostgreSQL 16 on localhost:5432
python -m ffdata init-db           # creates tables + views

# 3. Load data (each request waits ~4s to be polite)
python -m ffdata games  --season 2026            # teams + every game of the season
python -m ffdata stats  --season 2026 --week 5   # one week of player stats (omit --week for all)
python -m ffdata season --season 2025            # games + stats + views in one go
python -m ffdata status

# 4. Run tests
pytest -q
```

A full season takes under a minute (about 6 requests). Re-running a command is always safe: files that
haven't changed on nflverse aren't downloaded again, and upserts don't create duplicates. During the season,
re-run `stats` after each game day to pick up new games and stat corrections.

## Try some SQL

```bash
docker exec -it ffdata-postgres psql -U fantasy -d fantasy
```

```sql
-- Top 10 PPR performances of week 5
SELECT player_name, position, team_abbr, opponent, pts_ppr
FROM vw_player_game_fantasy
WHERE season = 2026 AND week = 5
ORDER BY pts_ppr DESC
LIMIT 10;
```

## Repository layout

```
ffdata/               Python package
  config.py           settings from .env
  http.py             polite fetcher (robots.txt, rate limit, retries)
  sources/nflverse.py find + download nflverse files; CSV -> rows (pure functions)
  teams.py            team abbreviation reference data
  db.py               connection, migrations, models, upserts, run log
  pipeline.py         extract -> transform -> load steps
  cli.py              `python -m ffdata ...`
sql/schema/           versioned table migrations (applied once each)
sql/models/           SQL views rebuilt on demand (fantasy scoring)
tests/                pytest suite + small CSV fixtures of real rows (no network needed)
docs/                 architecture, data dictionary, decisions, dev log
data/raw/             raw downloaded files (git-ignored)
```

## Documentation

- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data_dictionary.md)
- [Decision log](docs/decisions.md)
- [Development log](docs/dev_log.md)
- [Learning notes – Step 1 concepts](docs/learning_notes.md)
- [Windows setup & troubleshooting](docs/setup_windows.md)

## Data source & etiquette

NFL data comes from **[nflverse](https://github.com/nflverse/nflverse-data)**, which publishes open football data
for programmatic use under the [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) license (free to use with
credit). Thank you, nflverse!

This project is personal and educational. It downloads files through the
[GitHub REST API](https://docs.github.com/rest) (GitHub's robots.txt asks automated clients to use the API rather
than plain download links), identifies itself with an honest User-Agent, waits between requests, and only
downloads a file again when nflverse has published a new version.

The project originally scraped Pro-Football-Reference, but its bot protection blocks automated access, so the
source was changed. See [decision D-008](docs/decisions.md).
