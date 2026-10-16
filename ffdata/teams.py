"""Team reference data: the seed for the ``teams`` dimension table.

Abbreviations follow nflverse (our data source), which differs from other
sites for a few teams: GB (not GNB), KC (KAN), LA (LAR) for the Rams, LV (LVR),
NE (NWE), NO (NOR), SF (SFO), TB (TAM). Every team in the data must exist here,
or the database rejects the game (foreign key).
"""
from __future__ import annotations

# abbreviation: current team name
TEAMS: dict[str, str] = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}


def team_rows() -> list[dict]:
    # team_code was PFR's franchise code; with nflverse it is simply the abbreviation.
    return [
        {"team_code": abbr, "team_abbr": abbr, "team_name": name}
        for abbr, name in TEAMS.items()
    ]
