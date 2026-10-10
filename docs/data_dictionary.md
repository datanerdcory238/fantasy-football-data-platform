# Data Dictionary

All tables live in the `public` schema of the `fantasy` PostgreSQL database.
Source: Pro-Football-Reference (PFR).

## Tables

### `teams` — reference (32 rows)
| Column | Type | Description |
|---|---|---|
| team_code | text **PK** | PFR franchise code used in URLs and game ids (`crd`, `rav`, `kan`) |
| team_abbr | text, unique | Abbreviation used in stat tables (`ARI`, `BAL`, `KAN`) |
| team_name | text | Current team name |

### `games` — one row per game
| Column | Type | Description |
|---|---|---|
| game_id | text **PK** | PFR id: `YYYYMMDD` + `0` + home franchise code, e.g. `202509040phi` |
| season | int | NFL season (the year it starts) |
| week | int | Week number. Playoffs continue after the last regular week (WildCard = 19 in an 18-week season) |
| week_label | text | `1`–`18`, `WildCard`, `Division`, `ConfChamp`, `SuperBowl` |
| game_type | text | `REG` or `POST` |
| game_date | date | Local game date |
| kickoff_time | text | e.g. `8:20PM` (ET, as shown by PFR) |
| home_team / away_team | text → teams.team_abbr | Home and away teams |
| home_score / away_score | int | NULL until the game is played |
| neutral_site | bool | TRUE for neutral-site games (e.g. Super Bowl, international) |
| is_completed | bool | TRUE when a box score exists |
| boxscore_url | text | Source box-score page |
| updated_at | timestamptz | Last upsert time |

### `players` — one row per player
| Column | Type | Description |
|---|---|---|
| player_id | text **PK** | PFR player id, e.g. `HurtJa00` |
| player_name | text | Display name |
| updated_at | timestamptz | Last upsert time |

### `player_seasons` — one row per player per season
| Column | Type | Description |
|---|---|---|
| player_id | text **PK** → players | |
| season | int **PK** | |
| team_abbr | text | Team, or `2TM`/`3TM` if the player was traded |
| position | text | Fantasy position (QB/RB/WR/TE), from PFR's season fantasy page |
| age | int | Age as listed by PFR |

### `player_game_offense` — fact table, one row per player per game
| Column | Type | Description |
|---|---|---|
| game_id | text **PK** → games | |
| player_id | text **PK** → players | |
| team_abbr | text → teams.team_abbr | Player's team in this game |
| pass_cmp, pass_att, pass_yds, pass_td, pass_int | int | Passing |
| pass_sacked, pass_sacked_yds | int | Times sacked, yards lost |
| pass_long | int | Longest completion |
| pass_rating | numeric(5,1) | Passer rating |
| rush_att, rush_yds, rush_td, rush_long | int | Rushing |
| targets, rec, rec_yds, rec_td, rec_long | int | Receiving |
| fumbles, fumbles_lost | int | Fumbles |

Blank cells on PFR are stored as NULL. Views treat NULL as 0.

### `scrape_runs` — pipeline audit log
| Column | Description |
|---|---|
| run_id | Auto-increment id |
| command / args | e.g. `boxscores` / `season=2025 week=1` |
| started_at / finished_at | Run timing |
| status | `running`, `success`, `partial` (some games failed), `failed` |
| pages_fetched / pages_cached | Network requests vs. cache hits |
| rows_loaded | Rows upserted |
| error | Error text or list of failed game ids |

### `schema_migrations`
The migration files that have been applied, with timestamps.

## Views (`sql/models/`)

### `vw_player_game_fantasy`
One row per player per game. It joins `games`, `players`, and `player_seasons` and adds `opponent`, `home_away`,
and fantasy points:

| Stat | Points |
|---|---|
| Passing yards | 0.04 per yard (1 per 25) |
| Passing TD | 4 |
| Interception | −2 |
| Rushing / receiving yards | 0.1 per yard |
| Rushing / receiving TD | 6 |
| Fumble lost | −2 |
| Reception | 0 (`pts_standard`), 0.5 (`pts_half_ppr`), 1 (`pts_ppr`) |

Not yet counted: 2-point conversions, return TDs, and offensive fumble-recovery TDs.

### `vw_player_season_fantasy`
Regular-season totals per player: games played, yardage and TDs, points in each format, and `ppr_per_game`.
