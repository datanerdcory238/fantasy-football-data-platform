"""Tests for the nflverse source: transforms (pure functions) and the download cache.

Fixtures in tests/fixtures/nflverse/ are real rows cut from nflverse files
(2026 weeks 4-5, a few 2025 playoff games), trimmed to the columns we use.
"""
from datetime import date
from pathlib import Path

import pytest

from ffdata.sources import nflverse as nv

FIXTURES = Path(__file__).parent / "fixtures" / "nflverse"


def read_fixture(name):
    return nv.read_csv((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def stats_2026():
    return nv.transform_player_stats(read_fixture("stats_player_week_sample.csv"), 2026)


def by_player_week(rows, name, week):
    return next(r for r in rows if r["player_name"] == name and r["week"] == week)


# --------------------------------------------------------------------------- #
# Games
# --------------------------------------------------------------------------- #
def test_games_only_requested_season():
    games = nv.transform_games(read_fixture("games_sample.csv"), 2026)
    assert len(games) == 8
    assert {g["season"] for g in games} == {2026}


def test_game_values_and_types():
    games = {g["game_id"]: g for g in nv.transform_games(read_fixture("games_sample.csv"), 2026)}
    g = games["2026_05_IND_PIT"]
    assert g["home_team"] == "PIT" and g["away_team"] == "IND"
    assert (g["home_score"], g["away_score"]) == (34, 22)
    assert g["game_date"] == date(2026, 10, 11)
    assert (g["week"], g["week_label"], g["game_type"]) == (5, "5", "REG")
    assert g["is_completed"] is True and g["neutral_site"] is False


def test_unplayed_game_has_no_scores():
    games = {g["game_id"]: g for g in nv.transform_games(read_fixture("games_sample.csv"), 2026)}
    g = games["2026_06_HOU_JAX"]
    assert g["home_score"] is None and g["is_completed"] is False
    assert g["neutral_site"] is True  # played abroad


def test_playoff_games_are_post_with_round_label():
    games = {g["game_id"]: g for g in nv.transform_games(read_fixture("games_sample.csv"), 2025)}
    assert games["2025_19_LA_CAR"]["game_type"] == "POST"
    assert games["2025_19_LA_CAR"]["week_label"] == "WildCard"
    sb = games["2025_22_SEA_NE"]
    assert (sb["week"], sb["week_label"], sb["game_type"]) == (22, "SuperBowl", "POST")


# --------------------------------------------------------------------------- #
# Player stats
# --------------------------------------------------------------------------- #
def test_only_offensive_players_kept(stats_2026):
    names = {r["player_name"] for r in stats_2026}
    assert "Nick Folk" not in names        # kicker
    assert "Cameron Jordan" not in names   # linebacker
    assert len(stats_2026) == 5


def test_fullback_counts_as_rb(stats_2026):
    assert by_player_week(stats_2026, "Michael Burton", 5)["position"] == "RB"


def test_stat_values_and_sack_yards_positive(stats_2026):
    r = by_player_week(stats_2026, "Aaron Rodgers", 5)
    assert (r["pass_cmp"], r["pass_att"], r["pass_yds"], r["pass_td"]) == (22, 31, 235, 3)
    assert (r["pass_sacked"], r["pass_sacked_yds"]) == (1, 10)  # file says -10
    assert (r["team_abbr"], r["game_id"]) == ("PIT", "2026_05_IND_PIT")


def test_fumbles_are_summed(stats_2026):
    r = by_player_week(stats_2026, "Aaron Jones", 5)
    assert (r["fumbles"], r["fumbles_lost"]) == (1, 1)


def test_two_point_conversions_and_source_points(stats_2026):
    r = by_player_week(stats_2026, "Mike Evans", 5)
    assert r["rec_2pt"] == 1
    assert (r["src_pts_standard"], r["src_pts_ppr"]) == (19.3, 26.3)


def test_week_filter():
    rows = nv.transform_player_stats(read_fixture("stats_player_week_sample.csv"), 2026, week=4)
    assert [r["player_name"] for r in rows] == ["Aaron Rodgers"]


def test_rows_have_every_offense_column(stats_2026):
    for r in stats_2026:
        assert set(nv.OFFENSE_COLUMNS) <= r.keys()


# --------------------------------------------------------------------------- #
# Players and player seasons
# --------------------------------------------------------------------------- #
def test_unique_players(stats_2026):
    players = nv.unique_players(stats_2026)
    assert len(players) == 4  # Rodgers appears twice (weeks 4 and 5) but once here


def test_age_on():
    assert nv.age_on(date(1983, 12, 2), date(2026, 9, 1)) == 42  # birthday not reached yet
    assert nv.age_on(date(1993, 8, 21), date(2026, 9, 1)) == 33  # birthday already passed


def test_player_seasons(stats_2026):
    births = nv.birth_dates(read_fixture("players_sample.csv"))
    seasons = {r["player_id"]: r for r in nv.transform_player_seasons(stats_2026, 2026, births)}
    rodgers = seasons["00-0023459"]
    assert rodgers == {"player_id": "00-0023459", "season": 2026, "team_abbr": "PIT",
                       "position": "QB", "age": 42}


def test_player_season_missing_birth_date_gives_no_age(stats_2026):
    seasons = nv.transform_player_seasons(stats_2026, 2026, births={})
    assert all(r["age"] is None for r in seasons)


# --------------------------------------------------------------------------- #
# Extract: find_asset and the "only download when changed" cache
# --------------------------------------------------------------------------- #
class FakeFetcher:
    """Pretends to be PoliteFetcher: a fake GitHub API plus a counter of downloads."""

    def __init__(self, raw_dir, updated_at="2026-10-16T13:59:46Z"):
        self.raw_dir = raw_dir
        self.updated_at = updated_at
        self.downloads = 0

    def get_json(self, url):
        assert url.endswith("/releases/tags/schedules")
        return {"assets": [
            {"name": "other.csv", "url": "https://api.example/assets/1", "updated_at": "x"},
            {"name": "games.csv", "url": "https://api.example/assets/2",
             "updated_at": self.updated_at},
        ]}

    def download(self, url, dest, headers=None):
        assert headers == {"Accept": "application/octet-stream"}
        self.downloads += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("game_id\nG1\n", encoding="utf-8")
        return dest


def test_find_asset():
    asset = nv.find_asset(FakeFetcher(Path(".")), *nv.GAMES_FILE)
    assert asset.api_url == "https://api.example/assets/2"


def test_find_asset_missing_file():
    with pytest.raises(FileNotFoundError):
        nv.find_asset(FakeFetcher(Path(".")), "schedules", "nope.csv")


def test_fetch_asset_downloads_only_when_changed(tmp_path):
    fetcher = FakeFetcher(tmp_path)
    asset = nv.find_asset(fetcher, *nv.GAMES_FILE)

    first = nv.fetch_asset(fetcher, asset)
    assert first.from_cache is False
    assert first.path == tmp_path / "nflverse" / "schedules" / "games.csv"
    assert nv.read_csv(first.text) == [{"game_id": "G1"}]

    assert nv.fetch_asset(fetcher, asset).from_cache is True   # same version: no download
    assert fetcher.downloads == 1

    fetcher.updated_at = "2026-10-17T13:59:46Z"                 # nflverse published a new one
    assert nv.fetch_asset(fetcher, nv.find_asset(fetcher, *nv.GAMES_FILE)).from_cache is False
    assert fetcher.downloads == 2
