-- 001_initial_tables.sql
-- Core tables for Step 1. Applied once by `python -m ffdata init-db`
-- and recorded in schema_migrations so it never runs twice.

-- ---------------------------------------------------------------------------
-- Reference / dimension-like tables
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS teams (
    team_code   TEXT PRIMARY KEY,          -- PFR franchise code used in URLs, e.g. 'crd'
    team_abbr   TEXT NOT NULL UNIQUE,      -- abbreviation used in stat tables, e.g. 'ARI'
    team_name   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    player_id    TEXT PRIMARY KEY,         -- PFR player id, e.g. 'HurtJa00'
    player_name  TEXT NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Position/team/age can change year to year, so they live at player-season grain.
CREATE TABLE IF NOT EXISTS player_seasons (
    player_id    TEXT    NOT NULL REFERENCES players(player_id),
    season       INTEGER NOT NULL,
    team_abbr    TEXT,                     -- may be '2TM'/'3TM' for traded players
    position     TEXT,                     -- fantasy position: QB/RB/WR/TE
    age          INTEGER,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id, season)
);

-- ---------------------------------------------------------------------------
-- Games (one row per NFL game)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS games (
    game_id       TEXT PRIMARY KEY,        -- PFR id, e.g. '202509040phi'
    season        INTEGER NOT NULL,
    week          INTEGER NOT NULL,        -- playoffs continue after last regular week
    week_label    TEXT    NOT NULL,        -- '1'..'18', 'WildCard', 'Division', ...
    game_type     TEXT    NOT NULL CHECK (game_type IN ('REG', 'POST')),
    game_date     DATE,
    kickoff_time  TEXT,
    home_team     TEXT NOT NULL REFERENCES teams(team_abbr),
    away_team     TEXT NOT NULL REFERENCES teams(team_abbr),
    home_score    INTEGER,
    away_score    INTEGER,
    neutral_site  BOOLEAN NOT NULL DEFAULT FALSE,
    is_completed  BOOLEAN NOT NULL DEFAULT FALSE,
    boxscore_url  TEXT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_games_season_week ON games (season, week);

-- ---------------------------------------------------------------------------
-- Fact: player offensive stats per game (grain = one player in one game)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_game_offense (
    game_id          TEXT NOT NULL REFERENCES games(game_id),
    player_id        TEXT NOT NULL REFERENCES players(player_id),
    team_abbr        TEXT NOT NULL REFERENCES teams(team_abbr),
    pass_cmp         INTEGER,
    pass_att         INTEGER,
    pass_yds         INTEGER,
    pass_td          INTEGER,
    pass_int         INTEGER,
    pass_sacked      INTEGER,
    pass_sacked_yds  INTEGER,
    pass_long        INTEGER,
    pass_rating      NUMERIC(5, 1),
    rush_att         INTEGER,
    rush_yds         INTEGER,
    rush_td          INTEGER,
    rush_long        INTEGER,
    targets          INTEGER,
    rec              INTEGER,
    rec_yds          INTEGER,
    rec_td           INTEGER,
    rec_long         INTEGER,
    fumbles          INTEGER,
    fumbles_lost     INTEGER,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (game_id, player_id)
);
CREATE INDEX IF NOT EXISTS ix_pgo_player ON player_game_offense (player_id);

-- ---------------------------------------------------------------------------
-- Pipeline metadata: one row per CLI run (audit trail / observability)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id         SERIAL PRIMARY KEY,
    command        TEXT NOT NULL,
    args           TEXT,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at    TIMESTAMPTZ,
    status         TEXT NOT NULL DEFAULT 'running',  -- running / success / partial / failed
    pages_fetched  INTEGER NOT NULL DEFAULT 0,
    pages_cached   INTEGER NOT NULL DEFAULT 0,
    rows_loaded    INTEGER NOT NULL DEFAULT 0,
    error          TEXT
);
