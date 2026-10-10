"""Pipeline steps: extract (fetch) -> transform (parse) -> load (upsert).

Each step is a plain function that takes a DB connection and a fetcher, so
it can be called from the CLI today and from an Airflow task in Step 3.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from . import db
from .http import PoliteFetcher
from .parsers import pfr
from .teams import team_rows

log = logging.getLogger(__name__)


@dataclass
class RunStats:
    pages_fetched: int = 0
    pages_cached: int = 0
    rows_loaded: int = 0
    failures: list[str] = field(default_factory=list)

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


def load_teams(conn) -> int:
    n = db.upsert(conn, "teams", team_rows(), key_cols=["team_code"], touch_updated_at=False)
    conn.commit()
    return n


def scrape_schedule(conn, fetcher: PoliteFetcher, season: int, stats: RunStats,
                    refresh: bool = True) -> int:
    """Fetch & load every game for a season.

    ``refresh`` defaults to True because the schedule page changes every week
    as games are played (scores, box-score links).
    """
    load_teams(conn)
    result = fetcher.get(pfr.schedule_url(season), refresh=refresh)
    stats.record_fetch(result.from_cache)
    games = pfr.parse_schedule(result.html, season)
    n = db.upsert(conn, "games", games, key_cols=["game_id"])
    conn.commit()
    stats.rows_loaded += n
    log.info("season %s: loaded %d games", season, n)
    return n


def scrape_positions(conn, fetcher: PoliteFetcher, season: int, stats: RunStats,
                     refresh: bool = False) -> int:
    result = fetcher.get(pfr.fantasy_url(season), refresh=refresh)
    stats.record_fetch(result.from_cache)
    rows = pfr.parse_fantasy_positions(result.html, season)
    db.upsert(conn, "players", rows, key_cols=["player_id"], columns=["player_id", "player_name"])
    n = db.upsert(
        conn, "player_seasons", rows, key_cols=["player_id", "season"],
        columns=["player_id", "season", "team_abbr", "position", "age"],
    )
    conn.commit()
    stats.rows_loaded += n
    log.info("season %s: loaded %d player-season positions", season, n)
    return n


def games_needing_box_scores(conn, season: int, week: int | None, force: bool) -> list[str]:
    p = db.param
    sql = (
        "SELECT g.game_id FROM games g "
        f"WHERE g.season = {p(conn, 'season')} AND g.is_completed "
    )
    params: dict = {"season": season}
    if week is not None:
        sql += f"AND g.week = {p(conn, 'week')} "
        params["week"] = week
    if not force:
        sql += ("AND NOT EXISTS (SELECT 1 FROM player_game_offense o "
                "WHERE o.game_id = g.game_id) ")
    sql += "ORDER BY g.game_date, g.game_id"
    return [r[0] for r in conn.execute(sql, params).fetchall()]


def load_box_score(conn, html: str, game_id: str) -> int:
    rows = pfr.parse_player_offense(html, game_id)
    db.upsert(conn, "players", rows, key_cols=["player_id"], columns=["player_id", "player_name"])
    cols = ["game_id", "player_id", "team_abbr"] + [c for c, _ in pfr.OFFENSE_STATS.values()]
    n = db.upsert(conn, "player_game_offense", rows, key_cols=["game_id", "player_id"],
                  columns=cols)
    conn.commit()
    return n


def scrape_box_scores(conn, fetcher: PoliteFetcher, season: int, stats: RunStats,
                      week: int | None = None, force: bool = False) -> int:
    """Fetch box scores for completed games that don't have stats yet.

    One bad page shouldn't kill a 270-game run: failures are logged, collected
    in ``stats.failures`` and the loop continues.
    """
    game_ids = games_needing_box_scores(conn, season, week, force)
    log.info("season %s week %s: %d box scores to process", season, week or "all", len(game_ids))
    total = 0
    for i, game_id in enumerate(game_ids, 1):
        try:
            result = fetcher.get(pfr.boxscore_url(game_id))
            stats.record_fetch(result.from_cache)
            n = load_box_score(conn, result.html, game_id)
            total += n
            log.info("[%d/%d] %s: %d player rows", i, len(game_ids), game_id, n)
        except Exception as exc:  # noqa: BLE001 — keep going, report at the end
            conn.rollback()
            log.error("[%d/%d] %s failed: %s", i, len(game_ids), game_id, exc)
            stats.failures.append(game_id)
    stats.rows_loaded += total
    return total
