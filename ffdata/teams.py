"""Team reference data.

Pro-Football-Reference uses two different team codes:

* a lowercase *franchise code* in URLs (``/teams/crd/2025.htm``) and game ids
  (``202509070crd``), which stays the same when a team relocates; and
* an uppercase *abbreviation* in stat tables (``ARI``).

They don't always match (crd ↔ ARI, rav ↔ BAL, oti ↔ TEN …), so we keep an
explicit mapping. This is the seed for the ``teams`` dimension table.
"""
from __future__ import annotations

# franchise_code: (abbreviation, current team name)
TEAMS: dict[str, tuple[str, str]] = {
    "crd": ("ARI", "Arizona Cardinals"),
    "atl": ("ATL", "Atlanta Falcons"),
    "rav": ("BAL", "Baltimore Ravens"),
    "buf": ("BUF", "Buffalo Bills"),
    "car": ("CAR", "Carolina Panthers"),
    "chi": ("CHI", "Chicago Bears"),
    "cin": ("CIN", "Cincinnati Bengals"),
    "cle": ("CLE", "Cleveland Browns"),
    "dal": ("DAL", "Dallas Cowboys"),
    "den": ("DEN", "Denver Broncos"),
    "det": ("DET", "Detroit Lions"),
    "gnb": ("GNB", "Green Bay Packers"),
    "htx": ("HOU", "Houston Texans"),
    "clt": ("IND", "Indianapolis Colts"),
    "jax": ("JAX", "Jacksonville Jaguars"),
    "kan": ("KAN", "Kansas City Chiefs"),
    "rai": ("LVR", "Las Vegas Raiders"),
    "sdg": ("LAC", "Los Angeles Chargers"),
    "ram": ("LAR", "Los Angeles Rams"),
    "mia": ("MIA", "Miami Dolphins"),
    "min": ("MIN", "Minnesota Vikings"),
    "nwe": ("NWE", "New England Patriots"),
    "nor": ("NOR", "New Orleans Saints"),
    "nyg": ("NYG", "New York Giants"),
    "nyj": ("NYJ", "New York Jets"),
    "phi": ("PHI", "Philadelphia Eagles"),
    "pit": ("PIT", "Pittsburgh Steelers"),
    "sfo": ("SFO", "San Francisco 49ers"),
    "sea": ("SEA", "Seattle Seahawks"),
    "tam": ("TAM", "Tampa Bay Buccaneers"),
    "oti": ("TEN", "Tennessee Titans"),
    "was": ("WAS", "Washington Commanders"),
}


def abbr_for(franchise_code: str) -> str:
    """Franchise code -> stat-table abbreviation (falls back to upper-case code)."""
    code = franchise_code.lower()
    return TEAMS[code][0] if code in TEAMS else code.upper()


def team_rows() -> list[dict]:
    return [
        {"team_code": code, "team_abbr": abbr, "team_name": name}
        for code, (abbr, name) in TEAMS.items()
    ]
