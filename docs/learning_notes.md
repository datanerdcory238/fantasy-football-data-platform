# Learning Notes — Step 1 concepts

Concepts this stage exercises, where to find each one in the code, and what to study next.

| Concept | Where in the repo | Try this |
|---|---|---|
| **HTTP status codes** | `PoliteFetcher._request` | Our first PFR run got `403 Forbidden`: the server understood but refused. What do `200`, `404`, `429` and `503` mean? |
| **APIs (JSON over HTTP)** | `ffdata/sources/nflverse.py` (`find_asset`) | Open https://api.github.com/repos/nflverse/nflverse-data/releases/tags/stats_player in your browser and find `updated_at` for this season's file. |
| **robots.txt & rate limiting** | `PoliteFetcher._check_robots`, `_wait_for_rate_limit` | Read https://github.com/robots.txt and find the `User-agent: *` section. Why does `Disallow: /*/download` matter to us? |
| **Retries / exponential backoff** | `PoliteFetcher._request` | Why does the wait double each attempt? |
| **Raw / bronze layer** | `data/raw/nflverse/` | Open a raw CSV in Excel. Delete a row from `player_game_offense`, re-run `stats`, and check it's back without a new download (`cached=` in the output). |
| **Pure functions & unit testing** | `tests/test_nflverse.py` | Add a test for a player who changed teams mid-season. |
| **Relational modeling, PK/FK, grain** | `sql/schema/001_initial_tables.sql` | What's the grain of each table? Why is position in `player_seasons`, not `players`? |
| **Idempotency / upserts** | `db.upsert` | Run `python -m ffdata games --season 2026` twice, then check `SELECT COUNT(*) FROM games`. |
| **Incremental loading** | `nflverse.fetch_asset`, `*.meta.json` | Run `stats` twice in a row and compare `fetched=` / `cached=` in `status`. |
| **Schema migrations** | `db.apply_migrations`, `schema_migrations`, `sql/schema/002_*.sql` | Read 002 and find it in `SELECT * FROM schema_migrations`. |
| **SQL modeling (CTEs, CASE, joins, aggregates)** | `sql/models/*.sql` | Write a view for each team's weekly fantasy points allowed by position. |
| **Data-quality checks** | `src_pts_*` columns, query in `data_dictionary.md` | Change the reception value in a copy of the view's formula and watch the mismatch count jump. |
| **Pipeline observability** | `scrape_runs`, `python -m ffdata status` | Run `stats` before `games` for a new season and look at the `failed` run and its error. |
| **Language upgrades break code** | (removed PFR parser, see `dev_log.md` 2026-10-16) | Python 3.15 refuses `strptime("September 8", "%B %d")`. Why is a date with no year ambiguous? |
| **Config & secrets hygiene** | `.env.example`, `.gitignore` | Why is `.env` never committed? |
| **CI** | `.github/workflows/ci.yml` | After you push, open the *Actions* tab on GitHub. |

## Practice SQL questions (answer with the views)
1. Top 5 PPR scorers by position for week 1.
2. Each WR's target share: targets ÷ team total targets for that game.
3. Most consistent RBs: lowest standard deviation of weekly PPR points (min. 4 games).
4. Which defenses allowed the most fantasy points to QBs?
