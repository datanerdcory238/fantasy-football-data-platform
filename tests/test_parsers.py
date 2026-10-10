"""Unit tests for the PFR parsers — no network, no database."""
from datetime import date
from pathlib import Path

from ffdata.parsers import pfr

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------- schedule ----------------
def test_schedule_skips_header_and_separator_rows():
    games = pfr.parse_schedule(load("games_sample.html"), 2025)
    assert len(games) == 4


def test_schedule_home_away_from_location_marker():
    games = {g["game_id"]: g for g in pfr.parse_schedule(load("games_sample.html"), 2025)}

    phi = games["202509040phi"]  # no "@" -> winner was home
    assert (phi["home_team"], phi["away_team"]) == ("PHI", "DAL")
    assert (phi["home_score"], phi["away_score"]) == (24, 20)
    assert phi["game_date"] == date(2025, 9, 4)

    ari = games["202509070crd"]  # "@" -> winner (KC) was away; crd maps to ARI
    assert (ari["home_team"], ari["away_team"]) == ("ARI", "KAN")
    assert (ari["home_score"], ari["away_score"]) == (17, 27)


def test_schedule_unplayed_game_has_no_scores():
    games = {g["game_id"]: g for g in pfr.parse_schedule(load("games_sample.html"), 2025)}
    g = games["202601040oti"]  # id synthesised from date + home franchise code
    assert g["is_completed"] is False
    assert g["home_score"] is None and g["boxscore_url"] is None
    assert (g["home_team"], g["away_team"]) == ("TEN", "BAL")


def test_schedule_playoff_week_numbering():
    games = {g["game_id"]: g for g in pfr.parse_schedule(load("games_sample.html"), 2025)}
    sb = games["202602080nwe"]
    assert sb["game_type"] == "POST"
    assert sb["week_label"] == "SuperBowl"
    assert sb["week"] == 18 + 4
    assert sb["neutral_site"] is True


# ---------------- box score ----------------
def test_box_score_reads_commented_table():
    rows = pfr.parse_player_offense(load("boxscore_sample.html"), "202509040phi")
    assert [r["player_id"] for r in rows] == ["HurtJa00", "BrowAJ00", "PresDa01"]


def test_box_score_values_and_types():
    rows = {r["player_id"]: r for r in
            pfr.parse_player_offense(load("boxscore_sample.html"), "202509040phi")}
    hurts = rows["HurtJa00"]
    assert hurts["game_id"] == "202509040phi"
    assert hurts["player_name"] == "Jalen Hurts"
    assert hurts["team_abbr"] == "PHI"
    assert hurts["pass_yds"] == 250 and hurts["rush_td"] == 1
    assert hurts["pass_rating"] == 98.6
    assert hurts["rec_long"] is None            # blank cell -> NULL
    assert rows["PresDa01"]["pass_yds"] == 1005  # "1,005" -> 1005
    assert rows["PresDa01"]["rush_yds"] == -3


# ---------------- fantasy positions ----------------
def test_fantasy_positions():
    rows = {r["player_id"]: r for r in
            pfr.parse_fantasy_positions(load("fantasy_sample.html"), 2025)}
    assert len(rows) == 3
    assert rows["BrowAJ00"]["position"] == "WR"
    assert rows["HurtJa00"]["player_name"] == "Jalen Hurts"  # '*' Pro Bowl marker stripped
    assert rows["PresDa01"]["age"] == 32


# ---------------- helpers ----------------
def test_to_number():
    assert pfr.to_number("") is None
    assert pfr.to_number("1,234") == 1234
    assert pfr.to_number("98.7", float) == 98.7
    assert pfr.to_number("abc") is None


def test_parse_game_date_old_format_rolls_year():
    assert pfr.parse_game_date("September 8", 2019) == date(2019, 9, 8)
    assert pfr.parse_game_date("January 5", 2019) == date(2020, 1, 5)
