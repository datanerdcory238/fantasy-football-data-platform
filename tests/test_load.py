"""Integration-style tests for the load step, using in-memory SQLite.

SQLite understands the same CREATE TABLE and INSERT ... ON CONFLICT syntax we
use for PostgreSQL, so we can test idempotent loading without a server.
(The SQL *views* use Postgres-only functions and are checked in CI instead.)
"""
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from ffdata import db, pipeline
from ffdata.parsers import pfr

FIXTURES = Path(__file__).parent / "fixtures"
sqlite3.register_adapter(date, lambda d: d.isoformat())


class FakeFetcher:
    """Serves fixture HTML instead of hitting the network."""

    def __init__(self):
        self.pages = {
            pfr.schedule_url(2025): "games_sample.html",
            pfr.fantasy_url(2025): "fantasy_sample.html",
            pfr.boxscore_url("202509040phi"): "boxscore_sample.html",
        }

    def get(self, url, refresh=False):
        if url not in self.pages:
            raise RuntimeError(f"404 {url}")
        html = (FIXTURES / self.pages[url]).read_text(encoding="utf-8")
        return type("R", (), {"html": html, "from_cache": True})()


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    db.apply_migrations(c)
    yield c
    c.close()


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_migrations_are_applied_once(conn):
    assert db.apply_migrations(conn) == []  # second call is a no-op


def test_full_season_load_is_idempotent(conn):
    fetcher, stats = FakeFetcher(), pipeline.RunStats()
    for _ in range(2):  # run everything twice — counts must not change
        pipeline.scrape_schedule(conn, fetcher, 2025, stats)
        pipeline.scrape_positions(conn, fetcher, 2025, stats)
        pipeline.scrape_box_scores(conn, fetcher, 2025, stats, force=True)

    assert count(conn, "teams") == 32
    assert count(conn, "games") == 4
    assert count(conn, "player_seasons") == 3
    assert count(conn, "players") == 3
    assert count(conn, "player_game_offense") == 3


def test_box_scores_only_for_completed_games_without_stats(conn):
    fetcher, stats = FakeFetcher(), pipeline.RunStats()
    pipeline.scrape_schedule(conn, fetcher, 2025, stats)
    todo = pipeline.games_needing_box_scores(conn, 2025, week=None, force=False)
    assert "202601040oti" not in todo  # unplayed game is skipped
    assert len(todo) == 3

    pipeline.scrape_box_scores(conn, fetcher, 2025, stats, week=1)
    # 202509070crd has no fixture -> recorded as a failure, run continues
    assert stats.failures == ["202509070crd"]
    assert pipeline.games_needing_box_scores(conn, 2025, week=1, force=False) == ["202509070crd"]


def test_run_log(conn):
    run_id = db.start_run(conn, "schedule", "season=2025")
    db.finish_run(conn, run_id, "success", {"pages_fetched": 1, "rows_loaded": 4})
    status, rows = conn.execute(
        "SELECT status, rows_loaded FROM scrape_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert (status, rows) == ("success", 4)
