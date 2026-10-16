# Data Dictionary

All tables live in the `public` schema of the PostgreSQL database named in `.env` (`POSTGRES_DB`; the default is
`fantasy`). Source: [nflverse](https://github.com/nflverse/nflverse-data) (see `docs/decisions.md`, D-008).

| nflverse file (release tag) | Feeds |
|---|---|
| `games.csv` (`schedules`) | `games` |
| `stats_player_week_<season>.csv` (`stats_player`) | `players`, `player_seasons`, `player_game_offense` |
| `players.csv` (`players`) | `player_seasons.age` (birth dates) |

## Tables

### `teams`: reference (32 rows)
| Column | Type | Description |
|---|---|---|
| team_code | text **PK** | Same as `team_abbr` since the switch to nflverse (it held PFR franchise codes before) |
| team_abbr | text, unique | nflverse abbreviation: `ARI`, `GB`, `KC`, `LA` (Rams), `LAC`, `LV`, `NE`, `NO`, `SF`, `TB`… |
| team_name | text | Current team name |

### `games`: one row per game
| Column | Type | Description |
|---|---|---|
| game_id | text **PK** | nflverse id: `season_week_away_home`, e.g. `2026_05_IND_PIT` |
| season | int | NFL season (the year it starts) |
| week | int | Week number. Playoffs continue after the last regular week (WildCard = 19 … SuperBowl = 22) |
| week_label | text | `1`–`18`, `WildCard`, `Division`, `ConfChamp`, `SuperBowl` |
| game_type | text | `REG` or `POST` (nflverse `WC`/`DIV`/`CON`/`SB` → `POST`) |
| game_date | date | Game date |
| kickoff_time | text | e.g. `20:15` (24-hour clock, US Eastern) |
| home_team / away_team | text → teams.team_abbr | Home and away teams |
| home_score / away_score | int | NULL until the game is played |
| neutral_site | bool | TRUE for neutral-site games (Super Bowl, international games) |
| is_completed | bool | TRUE when both scores are known |
| boxscore_url | text | Unused since the switch to nflverse (always NULL) |
| updated_at | timestamptz | Last upsert time |

### `players`: one row per player
| Column | Type | Description |
|---|---|---|
| player_id | text **PK** | NFL GSIS id, e.g. `00-0023459` |
| player_name | text | Display name, e.g. `Aaron Rodgers` |
| updated_at | timestamptz | Last upsert time |

Only players with at least one game as a QB/RB/WR/TE are loaded.

### `player_seasons`: one row per player per season
| Column | Type | Description |
|---|---|---|
| player_id | text **PK** → players | |
| season | int **PK** | |
| team_abbr | text | Team in the player's most recent game that season |
| position | text | Fantasy position (QB/RB/WR/TE) from nflverse `position_group`; fullbacks are RB |
| age | int | Age on Sept 1 of the season. NULL if nflverse has no birth date |

### `player_game_offense`: fact table, one row per player per game
| Column | Type | Description |
|---|---|---|
| game_id | text **PK** → games | |
| player_id | text **PK** → players | |
| team_abbr | text → teams.team_abbr | Player's team in this game |
| pass_cmp, pass_att, pass_yds, pass_td, pass_int | int | Passing |
| pass_sacked, pass_sacked_yds | int | Times sacked, yards lost (positive number) |
| pass_2pt, rush_2pt, rec_2pt | int | Successful 2-point conversions thrown, run, caught |
| rush_att, rush_yds, rush_td | int | Rushing |
| targets, rec, rec_yds, rec_td | int | Receiving |
| st_td | int | Special-teams (return) touchdowns |
| fumbles, fumbles_lost | int | Fumbles on sacks + runs + catches |
| src_pts_standard, src_pts_ppr | numeric(6,2) | nflverse's own fantasy points. **For checking our view only**, never for analysis |
| pass_long, pass_rating, rush_long, rec_long | | Not available from nflverse; always NULL |

Missing values are stored as NULL. Views treat NULL as 0.

### `scrape_runs`: pipeline audit log
| Column | Description |
|---|---|
| run_id | Auto-increment id |
| command / args | e.g. `stats` / `season=2026 week=5` |
| started_at / finished_at | Run timing (stored in UTC) |
| status | `running`, `success`, `failed` (runs before 2026-10-16 could also be `partial`) |
| pages_fetched / pages_cached | Files downloaded vs. files reused because nflverse hadn't changed them |
| rows_loaded | Rows upserted |
| error | Error text |

### `schema_migrations`
The migration files that have been applied, with timestamps (UTC).

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
| 2-point conversion (pass, run or catch) | 2 |
| Special-teams TD | 6 |
| Fumble lost | −2 |
| Reception | 0 (`pts_standard`), 0.5 (`pts_half_ppr`), 1 (`pts_ppr`) |

Not yet counted: offensive fumble-recovery TDs.

### `vw_player_season_fantasy`
Regular-season totals per player: games played, yardage and TDs, points in each format, and `ppr_per_game`.

## Data-quality check
Our view should match nflverse's points exactly. This should return 0 rows:

```sql
SELECT v.season, v.week, v.player_name, v.pts_ppr, o.src_pts_ppr
FROM vw_player_game_fantasy v
JOIN player_game_offense o USING (game_id, player_id)
WHERE ABS(v.pts_ppr - o.src_pts_ppr) > 0.01
   OR ABS(v.pts_standard - o.src_pts_standard) > 0.01;
```
