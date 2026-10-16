"""Pipeline steps: extract (download) -> transform -> load (upsert).

Each step is a plain function that takes a DB connection and a fetcher, so
it can be called from the CLI today and from an Airflow task in Step 3.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from . import db
from .http import PoliteFetcher
from .sources import nflverse as nv
from .teams import team_rows

log = logging.getLogger(__name__)


@dataclass
class RunStats:
    # "pages" are downloaded files now; the names match the scrape_runs columns.
    pages_fetched: int = 0
    pages_cached: int = 0
    rows_loaded: int = 0

    def record_fetch(self, from_cache: bool) -> None:
        if from_cache:
            self.pages_cached += 1
        else:
            self.pages_fetched += 1

    def as_dict(self) -> dict[str, int]:
        return {
            "pages_fetched": self.pages_fetched,
            "pages_cached": self.pages_cached,
            "rows_loaded": self.rows_loaded,
        }


def extract(fetcher: PoliteFetcher, file: tuple[str, str], stats: RunStats) -> list[dict]:
    """Download one nflverse file (if it changed) and return its CSV rows."""
    asset = nv.find_asset(fetcher, *file)
    result = nv.fetch_asset(fetcher, asset)
    stats.record_fetch(result.from_cache)
    return nv.read_csv(result.text)


def load_teams(conn) -> int:
    n = db.upsert(conn, "teams", team_rows(), key_cols=["team_code"], touch_updated_at=False)
    conn.commit()
    return n


def load_games(conn, fetcher: PoliteFetcher, season: int, stats: RunStats) -> int:
    """Load every game of a season (played and upcoming) into ``games``."""
    load_teams(conn)
    games = nv.transform_games(extract(fetcher, nv.GAMES_FILE, stats), season)
    n = db.upsert(conn, "games", games, key_cols=["game_id"])
    conn.commit()
    stats.rows_loaded += n
    log.info("season %s: loaded %d games", season, n)
    return n


def load_player_stats(conn, fetcher: PoliteFetcher, season: int, stats: RunStats,
                      week: int | None = None) -> int:
    """Load players, player_seasons and player_game_offense for a season (or one week).

    Games must be loaded first: every stats row points at a game (foreign key).
    """
    p = db.param
    n_games = conn.execute(f"SELECT COUNT(*) FROM games WHERE season = {p(conn, 's')}",
                           {"s": season}).fetchone()[0]
    if n_games == 0:
        raise RuntimeError(f"no games for {season} yet: run `python -m ffdata games "
                           f"--season {season}` first")

    season_rows = nv.transform_player_stats(extract(fetcher, nv.stats_file(season), stats), season)
    births = nv.birth_dates(extract(fetcher, nv.PLAYERS_FILE, stats))

    # Players and player_seasons always use the whole season, so "latest team"
    # stays right even when loading a single week.
    db.upsert(conn, "players", nv.unique_players(season_rows), key_cols=["player_id"])
    db.upsert(conn, "player_seasons", nv.transform_player_seasons(season_rows, season, births),
              key_cols=["player_id", "season"])

    rows = [r for r in season_rows if week is None or r["week"] == week]
    n = db.upsert(conn, "player_game_offense", rows, key_cols=["game_id", "player_id"],
                  columns=nv.OFFENSE_COLUMNS)
    conn.commit()
    stats.rows_loaded += n
    log.info("season %s week %s: loaded %d player-game rows", season, week or "all", n)
    return n
