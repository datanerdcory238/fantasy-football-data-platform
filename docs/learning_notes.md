# Learning Notes — Step 1 concepts

Concepts this stage exercises, where to find each one in the code, and what to study next.

| Concept | Where in the repo | Try this |
|---|---|---|
| **HTTP & web scraping** | `ffdata/http.py`, `ffdata/parsers/pfr.py` | Open a PFR box score, right-click → *View Page Source*, and search for `player_offense`. You'll find the table inside `<!-- -->`. |
| **robots.txt & rate limiting** | `PoliteFetcher._check_robots`, `_wait_for_rate_limit` | Read https://www.pro-football-reference.com/robots.txt |
| **Retries / exponential backoff** | `PoliteFetcher._download` | Why does the wait double each attempt? |
| **Raw / bronze layer** | `data/raw/` | Delete a row from `player_game_offense`, re-run `boxscores`, and watch it reload from cache (`cached=` in the output). |
| **Pure functions & unit testing** | `tests/test_parsers.py` | Add a test for a tie game. |
| **Relational modeling, PK/FK, grain** | `sql/schema/001_initial_tables.sql` | What's the grain of each table? Why is position in `player_seasons`, not `players`? |
| **Idempotency / upserts** | `db.upsert` | Run `python -m ffdata schedule --season 2025` twice, then check `SELECT COUNT(*) FROM games`. |
| **Incremental loading** | `pipeline.games_needing_box_scores` | Compare a run with and without `--force`. |
| **Schema migrations** | `db.apply_migrations`, `schema_migrations` | Add `002_add_column.sql` and run `init-db`. |
| **SQL modeling (CTEs, CASE, joins, aggregates)** | `sql/models/*.sql` | Write a view for each team's weekly fantasy points allowed by position. |
| **Pipeline observability** | `scrape_runs`, `python -m ffdata status` | Simulate a failure and look at the `partial` status. |
| **Config & secrets hygiene** | `.env.example`, `.gitignore` | Why is `.env` never committed? |
| **CI** | `.github/workflows/ci.yml` | After you push, open the *Actions* tab on GitHub. |

## Practice SQL questions (answer with the views)
1. Top 5 PPR scorers by position for week 1.
2. Each WR's target share: targets ÷ team total targets for that game.
3. Most consistent RBs: lowest standard deviation of weekly PPR points (min. 4 games).
4. Which defenses allowed the most fantasy points to QBs?
