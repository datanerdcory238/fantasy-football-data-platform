"""nflverse: open NFL data published as CSV files on GitHub Releases.

Source: https://github.com/nflverse/nflverse-data (open data, CC-BY 4.0; credit
nflverse). Files are updated roughly daily during the season.

**Why the GitHub API instead of the plain download links?** GitHub's robots.txt
disallows ``/*/download`` for automated clients and points to its API instead.
The API is the door built for programs, and it also tells us *when* each file
last changed, so we can skip downloads when nothing is new (incremental loading).

The module has two halves:

* **Extract**: ``find_asset`` asks the API about a file; ``fetch_asset`` saves it
  to ``data/raw/nflverse/<release>/<file>`` (the raw layer) unless our copy is
  already current.
* **Transform**: pure functions that turn CSV rows into rows for our tables.
  No network or database, so they are easy to test.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

log = logging.getLogger(__name__)

API_BASE = "https://api.github.com/repos/nflverse/nflverse-data"

# (release tag, file name) for each file we use.
GAMES_FILE = ("schedules", "games.csv")
PLAYERS_FILE = ("players", "players.csv")


def stats_file(season: int) -> tuple[str, str]:
    return ("stats_player", f"stats_player_week_{season}.csv")


# --------------------------------------------------------------------------- #
# Extract
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Asset:
    """One file attached to a GitHub release."""

    tag: str
    name: str
    api_url: str      # https://api.github.com/repos/.../releases/assets/<id>
    updated_at: str   # e.g. '2026-10-16T13:59:46Z'


@dataclass
class Download:
    path: Path
    text: str
    from_cache: bool


def find_asset(fetcher, tag: str, name: str) -> Asset:
    """Ask the GitHub API for a release's file list and return the one we want."""
    release = fetcher.get_json(f"{API_BASE}/releases/tags/{tag}")
    for a in release.get("assets", []):
        if a["name"] == name:
            return Asset(tag, name, a["url"], a["updated_at"])
    raise FileNotFoundError(f"nflverse release '{tag}' has no file named '{name}'")


def raw_path(raw_dir: Path, asset: Asset) -> Path:
    return raw_dir / "nflverse" / asset.tag / asset.name


def fetch_asset(fetcher, asset: Asset) -> Download:
    """Return the file's text, downloading only if nflverse has a newer version.

    Next to each raw file we keep a small ``.meta.json`` noting which version
    (``updated_at``) we saved. Same version -> reuse the local copy.
    """
    path = raw_path(fetcher.raw_dir, asset)
    meta = path.with_name(path.name + ".meta.json")
    if path.exists() and meta.exists():
        if json.loads(meta.read_text())["updated_at"] == asset.updated_at:
            log.info("%s is up to date (nflverse version %s)", asset.name, asset.updated_at)
            return Download(path, path.read_text(encoding="utf-8"), from_cache=True)

    # Accept: application/octet-stream asks the API for the file itself
    # (it redirects to the real download) instead of a JSON description.
    fetcher.download(asset.api_url, path, headers={"Accept": "application/octet-stream"})
    meta.write_text(json.dumps({"updated_at": asset.updated_at, "source": asset.api_url}))
    return Download(path, path.read_text(encoding="utf-8"), from_cache=False)


def read_csv(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


# --------------------------------------------------------------------------- #
# Transform
# --------------------------------------------------------------------------- #
OFFENSE_GROUPS = {"QB", "RB", "WR", "TE"}  # position_group; fullbacks are in 'RB'
PLAYOFF_LABELS = {"WC": "WildCard", "DIV": "Division", "CON": "ConfChamp", "SB": "SuperBowl"}

# our column in player_game_offense -> nflverse column in stats_player_week
STAT_COLUMNS = {
    "pass_cmp": "completions",
    "pass_att": "attempts",
    "pass_yds": "passing_yards",
    "pass_td": "passing_tds",
    "pass_int": "passing_interceptions",
    "pass_sacked": "sacks_suffered",
    "pass_sacked_yds": "sack_yards_lost",
    "pass_2pt": "passing_2pt_conversions",
    "rush_att": "carries",
    "rush_yds": "rushing_yards",
    "rush_td": "rushing_tds",
    "rush_2pt": "rushing_2pt_conversions",
    "targets": "targets",
    "rec": "receptions",
    "rec_yds": "receiving_yards",
    "rec_td": "receiving_tds",
    "rec_2pt": "receiving_2pt_conversions",
    "st_td": "special_teams_tds",
    "src_pts_standard": "fantasy_points",
    "src_pts_ppr": "fantasy_points_ppr",
}
# A player can fumble on a sack, a run or a catch; we store the totals.
FUMBLE_COLUMNS = ("sack_fumbles", "rushing_fumbles", "receiving_fumbles")
FUMBLE_LOST_COLUMNS = ("sack_fumbles_lost", "rushing_fumbles_lost", "receiving_fumbles_lost")

# Columns written to player_game_offense.
OFFENSE_COLUMNS = ["game_id", "player_id", "team_abbr", *STAT_COLUMNS, "fumbles", "fumbles_lost"]


def to_number(value: str | None) -> int | float | None:
    """'244' -> 244, '25.66' -> 25.66, '' or 'NA' -> None."""
    if value is None or value.strip() in ("", "NA"):
        return None
    f = float(value)
    return int(f) if f.is_integer() else f


def transform_games(rows: Iterable[dict[str, str]], season: int) -> list[dict[str, Any]]:
    """games.csv rows (every season since 1999) -> our ``games`` rows for one season."""
    out = []
    for r in rows:
        if to_number(r["season"]) != season:
            continue
        home_score, away_score = to_number(r["home_score"]), to_number(r["away_score"])
        out.append({
            "game_id": r["game_id"],
            "season": season,
            "week": to_number(r["week"]),
            "week_label": PLAYOFF_LABELS.get(r["game_type"], r["week"]),
            "game_type": "REG" if r["game_type"] == "REG" else "POST",
            "game_date": date.fromisoformat(r["gameday"]) if r["gameday"] else None,
            "kickoff_time": r["gametime"] or None,
            "home_team": r["home_team"],
            "away_team": r["away_team"],
            "home_score": home_score,
            "away_score": away_score,
            "neutral_site": r["location"] == "Neutral",
            "is_completed": home_score is not None and away_score is not None,
        })
    return out


def transform_player_stats(rows: Iterable[dict[str, str]], season: int,
                           week: int | None = None) -> list[dict[str, Any]]:
    """stats_player_week rows -> one row per offensive player per game.

    Keeps QB/RB/WR/TE only. Extra keys (player_name, position, week) are used to
    build the players / player_seasons tables; ``OFFENSE_COLUMNS`` picks what
    goes into player_game_offense.
    """
    out = []
    for r in rows:
        if to_number(r["season"]) != season or r["position_group"] not in OFFENSE_GROUPS:
            continue
        if week is not None and to_number(r["week"]) != week:
            continue
        row: dict[str, Any] = {
            "game_id": r["game_id"],
            "player_id": r["player_id"],
            "player_name": r["player_display_name"],
            "position": r["position_group"],
            "week": to_number(r["week"]),
            "team_abbr": r["team"],
        }
        row.update({ours: to_number(r[theirs]) for ours, theirs in STAT_COLUMNS.items()})
        # nflverse stores sack yards as a negative number (-26); we store yards lost (26).
        if row["pass_sacked_yds"] is not None:
            row["pass_sacked_yds"] = abs(row["pass_sacked_yds"])
        row["fumbles"] = sum(to_number(r[c]) or 0 for c in FUMBLE_COLUMNS)
        row["fumbles_lost"] = sum(to_number(r[c]) or 0 for c in FUMBLE_LOST_COLUMNS)
        out.append(row)
    return out


def unique_players(stat_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """One ``players`` row per player id."""
    return list({r["player_id"]: {"player_id": r["player_id"], "player_name": r["player_name"]}
                 for r in stat_rows}.values())


def birth_dates(player_rows: Iterable[dict[str, str]]) -> dict[str, date]:
    """players.csv rows -> {player_id: birth date} (players without one are skipped)."""
    return {r["gsis_id"]: date.fromisoformat(r["birth_date"])
            for r in player_rows if r.get("gsis_id") and r.get("birth_date")}


def age_on(birth: date, on: date) -> int:
    """Whole years old on a given day."""
    return on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))


def transform_player_seasons(stat_rows: Iterable[dict[str, Any]], season: int,
                             births: dict[str, date]) -> list[dict[str, Any]]:
    """One ``player_seasons`` row per player.

    Team and position come from the player's most recent game that season (so a
    traded player shows their current team). Age is as of Sept 1, the usual
    "football age" convention.
    """
    latest: dict[str, dict[str, Any]] = {}
    for r in stat_rows:
        pid = r["player_id"]
        if pid not in latest or r["week"] > latest[pid]["week"]:
            latest[pid] = r
    sept_1 = date(season, 9, 1)
    return [
        {
            "player_id": pid,
            "season": season,
            "team_abbr": r["team_abbr"],
            "position": r["position"],
            "age": age_on(births[pid], sept_1) if pid in births else None,
        }
        for pid, r in latest.items()
    ]
