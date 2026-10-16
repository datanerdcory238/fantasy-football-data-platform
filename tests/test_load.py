"""Integration-style tests for the load step, using in-memory SQLite.

SQLite understands the same CREATE TABLE and INSERT ... ON CONFLICT syntax we
use for PostgreSQL, so we can test idempotent loading without a server.
(The SQL *views* use Postgres-only functions and are checked in CI instead.)
"""
import shutil
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from ffdata import db, pipeline

FIXTURES = Path(__file__).parent / "fixtures" / "nflverse"
sqlite3.register_adapter(date, lambda d: d.isoformat())

# release tag -> {file name nflverse publishes: our fixture file}
RELEASES = {
    "schedules": {"games.csv": "games_sample.csv"},
    "players": {"players.csv": "players_sample.csv"},
    "stats_player": {"stats_player_week_2026.csv": "stats_player_week_sample.csv"},
}


class FakeFetcher:
    """Pretends to be the GitHub API, serving fixture files instead of the network."""

    def __init__(self, raw_dir):
        self.raw_dir = raw_dir

    def get_json(self, url):
        tag = url.rsplit("/", 1)[-1]
        return {"assets": [
            {"name": name, "url": f"fixture://{fixture}", "updated_at": "2026-10-16T00:00:00Z"}
            for name, fixture in RELEASES[tag].items()
        ]}

    def download(self, url, dest, headers=None):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURES / url.removeprefix("fixture://"), dest)
        return dest


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    db.apply_migrations(c)
    yield c
    c.close()


@pytest.fixture
def fetcher(tmp_path):
    return FakeFetcher(tmp_path)


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_migrations_are_applied_once(conn):
    assert db.apply_migrations(conn) == []  # second call is a no-op


def test_full_season_load_is_idempotent(conn, fetcher):
    for _ in range(2):  # run everything twice — counts must not change
        stats = pipeline.RunStats()
        pipeline.load_games(conn, fetcher, 2026, stats)
        pipeline.load_player_stats(conn, fetcher, 2026, stats)

    assert count(conn, "teams") == 32
    assert count(conn, "games") == 8
    assert count(conn, "players") == 4
    assert count(conn, "player_seasons") == 4
    assert count(conn, "player_game_offense") == 5


def test_second_run_reuses_downloaded_files(conn, fetcher):
    first, second = pipeline.RunStats(), pipeline.RunStats()
    for stats in (first, second):
        pipeline.load_games(conn, fetcher, 2026, stats)
        pipeline.load_player_stats(conn, fetcher, 2026, stats)
    assert (first.pages_fetched, first.pages_cached) == (3, 0)
    assert (second.pages_fetched, second.pages_cached) == (0, 3)


def test_stats_need_games_first(conn, fetcher):
    with pytest.raises(RuntimeError, match="games --season 2026"):
        pipeline.load_player_stats(conn, fetcher, 2026, pipeline.RunStats())


def test_single_week_load(conn, fetcher):
    stats = pipeline.RunStats()
    pipeline.load_games(conn, fetcher, 2026, stats)
    pipeline.load_player_stats(conn, fetcher, 2026, stats, week=4)
    assert count(conn, "player_game_offense") == 1
    # player_seasons still reflects the whole season file (Rodgers' latest game is week 5)
    assert count(conn, "player_seasons") == 4


def test_loaded_values(conn, fetcher):
    stats = pipeline.RunStats()
    pipeline.load_games(conn, fetcher, 2026, stats)
    pipeline.load_player_stats(conn, fetcher, 2026, stats)
    row = conn.execute(
        "SELECT o.team_abbr, o.rush_yds, o.rush_td, o.fumbles_lost, o.src_pts_ppr, ps.age "
        "FROM player_game_offense o JOIN players p ON p.player_id = o.player_id "
        "JOIN player_seasons ps ON ps.player_id = o.player_id "
        "WHERE p.player_name = 'Aaron Jones'"
    ).fetchone()
    assert row == ("MIN", 113, 1, 1, 18.7, 31)


def test_run_log(conn):
    run_id = db.start_run(conn, "games", "season=2026")
    db.finish_run(conn, run_id, "success", {"pages_fetched": 1, "rows_loaded": 4})
    status, rows = conn.execute(
        "SELECT status, rows_loaded FROM scrape_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert (status, rows) == ("success", 4)
