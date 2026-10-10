"""Parsers for Pro-Football-Reference (PFR) pages.

Parsers are *pure functions*: HTML string in, list of dicts out. They never
touch the network or the database, which makes them easy to unit-test against
saved HTML fixtures (see ``tests/``).

PFR quirks handled here:
* Every cell carries a ``data-stat`` attribute — we key on that rather than on
  column position, so added/reordered columns don't break us.
* Header rows repeat every ~30 rows inside ``<tbody>`` (class ``thead``).
* Many tables are shipped inside HTML comments and un-commented by JavaScript
  in the browser, so BeautifulSoup won't "see" them unless we look in comments.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime

from bs4 import BeautifulSoup, Comment, Tag

from ..teams import abbr_for

log = logging.getLogger(__name__)

BASE_URL = "https://www.pro-football-reference.com"

PLAYOFF_ROUNDS = {"WildCard": 1, "Division": 2, "ConfChamp": 3, "SuperBowl": 4}

# Box-score "player_offense" columns we keep: data-stat -> (output column, type)
OFFENSE_STATS: dict[str, tuple[str, type]] = {
    "pass_cmp": ("pass_cmp", int),
    "pass_att": ("pass_att", int),
    "pass_yds": ("pass_yds", int),
    "pass_td": ("pass_td", int),
    "pass_int": ("pass_int", int),
    "pass_sacked": ("pass_sacked", int),
    "pass_sacked_yds": ("pass_sacked_yds", int),
    "pass_long": ("pass_long", int),
    "pass_rating": ("pass_rating", float),
    "rush_att": ("rush_att", int),
    "rush_yds": ("rush_yds", int),
    "rush_td": ("rush_td", int),
    "rush_long": ("rush_long", int),
    "targets": ("targets", int),
    "rec": ("rec", int),
    "rec_yds": ("rec_yds", int),
    "rec_td": ("rec_td", int),
    "rec_long": ("rec_long", int),
    "fumbles": ("fumbles", int),
    "fumbles_lost": ("fumbles_lost", int),
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def find_table(html: str, table_id: str) -> Tag | None:
    """Find ``<table id=table_id>`` even if it is hidden inside an HTML comment."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id=table_id)
    if table is not None:
        return table
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        if f'id="{table_id}"' in comment:
            table = BeautifulSoup(str(comment), "lxml").find("table", id=table_id)
            if table is not None:
                return table
    return None


def data_rows(table: Tag) -> list[Tag]:
    """Body rows, skipping repeated header / spacer rows."""
    body = table.find("tbody") or table
    rows = []
    for tr in body.find_all("tr"):
        classes = tr.get("class") or []
        if "thead" in classes or "over_header" in classes or "spacer" in classes:
            continue
        rows.append(tr)
    return rows


def cell(tr: Tag, stat: str) -> Tag | None:
    return tr.find(["td", "th"], attrs={"data-stat": stat})


def text(tr: Tag, stat: str) -> str:
    c = cell(tr, stat)
    return c.get_text(strip=True) if c else ""


def to_number(value: str, kind: type = int):
    """'' -> None, '1,234' -> 1234, '98.7' -> 98.7."""
    value = value.replace(",", "").strip()
    if value == "":
        return None
    try:
        return kind(value)
    except ValueError:
        try:
            return kind(float(value))
        except ValueError:
            return None


def href_of(tr: Tag, stat: str) -> str | None:
    c = cell(tr, stat)
    a = c.find("a") if c else None
    return a.get("href") if a else None


def franchise_from_href(href: str | None) -> str | None:
    """'/teams/kan/2025.htm' -> 'kan'."""
    m = re.search(r"/teams/([a-z]{3})/", href or "")
    return m.group(1) if m else None


def parse_game_date(raw: str, season: int) -> date | None:
    """PFR shows ISO dates ('2025-09-04'); older pages show 'September 4'."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass
    try:
        d = datetime.strptime(raw, "%B %d")
    except ValueError:
        return None
    # Jan/Feb games belong to the following calendar year.
    year = season + 1 if d.month <= 2 else season
    return date(year, d.month, d.day)


# --------------------------------------------------------------------------- #
# Season schedule & results:  /years/{season}/games.htm
# --------------------------------------------------------------------------- #
def schedule_url(season: int) -> str:
    return f"{BASE_URL}/years/{season}/games.htm"


def parse_schedule(html: str, season: int) -> list[dict]:
    table = find_table(html, "games")
    if table is None:
        raise ValueError("could not find table#games on schedule page")

    games: list[dict] = []
    for tr in data_rows(table):
        week_label = text(tr, "week_num")
        winner_code = franchise_from_href(href_of(tr, "winner"))
        loser_code = franchise_from_href(href_of(tr, "loser"))
        if not week_label or not winner_code or not loser_code:
            continue  # e.g. the "Playoffs" separator row

        game_date = parse_game_date(text(tr, "game_date"), season)
        location = text(tr, "game_location")  # "@" = winner was away, "N" = neutral
        # For unplayed games PFR lists visitor in "winner" and home in "loser" with "@".
        if location == "@":
            away_code, home_code = winner_code, loser_code
            away_pts, home_pts = text(tr, "pts_win"), text(tr, "pts_lose")
        else:
            home_code, away_code = winner_code, loser_code
            home_pts, away_pts = text(tr, "pts_win"), text(tr, "pts_lose")

        box_href = href_of(tr, "boxscore_word")
        completed = bool(box_href and box_href.startswith("/boxscores/") and home_pts)
        if box_href and box_href.startswith("/boxscores/"):
            game_id = box_href.rsplit("/", 1)[-1].removesuffix(".htm")
        elif game_date:
            game_id = f"{game_date:%Y%m%d}0{home_code}"  # PFR's id convention
        else:
            continue

        is_playoff = week_label in PLAYOFF_ROUNDS
        games.append(
            {
                "game_id": game_id,
                "season": season,
                "week": None if is_playoff else to_number(week_label),
                "week_label": week_label,
                "game_type": "POST" if is_playoff else "REG",
                "game_date": game_date,
                "kickoff_time": text(tr, "gametime") or None,
                "home_team": abbr_for(home_code),
                "away_team": abbr_for(away_code),
                "home_score": to_number(home_pts) if completed else None,
                "away_score": to_number(away_pts) if completed else None,
                "neutral_site": location == "N",
                "is_completed": completed,
                "boxscore_url": f"{BASE_URL}{box_href}" if completed else None,
            }
        )

    # Give playoff games a numeric week that follows the regular season
    # (e.g. WildCard = 19 in an 18-week season) so we can sort/filter by week.
    last_reg = max((g["week"] for g in games if g["week"] is not None), default=0)
    for g in games:
        if g["week"] is None:
            g["week"] = last_reg + PLAYOFF_ROUNDS[g["week_label"]]
    return games


# --------------------------------------------------------------------------- #
# Box score player offense:  /boxscores/{game_id}.htm  (table#player_offense)
# --------------------------------------------------------------------------- #
def boxscore_url(game_id: str) -> str:
    return f"{BASE_URL}/boxscores/{game_id}.htm"


def parse_player_offense(html: str, game_id: str) -> list[dict]:
    table = find_table(html, "player_offense")
    if table is None:
        raise ValueError(f"could not find table#player_offense for {game_id}")

    rows: list[dict] = []
    for tr in data_rows(table):
        player_cell = cell(tr, "player")
        if player_cell is None:
            continue
        player_id = player_cell.get("data-append-csv")
        if not player_id:  # fall back to the link: /players/H/HurtJa00.htm
            m = re.search(r"/players/\w/(\w+)\.htm", href_of(tr, "player") or "")
            player_id = m.group(1) if m else None
        if not player_id:
            continue

        row = {
            "game_id": game_id,
            "player_id": player_id,
            "player_name": player_cell.get_text(strip=True),
            "team_abbr": text(tr, "team"),
        }
        for stat, (col, kind) in OFFENSE_STATS.items():
            row[col] = to_number(text(tr, stat), kind)
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# Season fantasy page (for positions):  /years/{season}/fantasy.htm
# --------------------------------------------------------------------------- #
def fantasy_url(season: int) -> str:
    return f"{BASE_URL}/years/{season}/fantasy.htm"


def parse_fantasy_positions(html: str, season: int) -> list[dict]:
    """One row per player-season with their fantasy position (QB/RB/WR/TE)."""
    table = find_table(html, "fantasy")
    if table is None:
        raise ValueError("could not find table#fantasy on fantasy page")

    out: dict[str, dict] = {}
    for tr in data_rows(table):
        player_cell = cell(tr, "player")
        if player_cell is None:
            continue
        player_id = player_cell.get("data-append-csv")
        if not player_id:
            continue
        out[player_id] = {
            "player_id": player_id,
            "season": season,
            "player_name": player_cell.get_text(strip=True).rstrip("*+"),
            "team_abbr": text(tr, "team") or None,  # "2TM" if traded
            "position": text(tr, "fantasy_pos") or None,
            "age": to_number(text(tr, "age")),
        }
    return list(out.values())
