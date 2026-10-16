-- vw_player_game_fantasy
-- One row per player per game with fantasy points under three common scoring
-- formats. Rebuilt every run with `python -m ffdata build-models`.
--
-- Scoring (offense only, v2):
--   passing: 0.04/yd (1 pt per 25), 4/TD, -2/INT
--   rushing & receiving: 0.1/yd, 6/TD
--   2-point conversions (pass, rush or catch): 2
--   special-teams (return) TDs: 6
--   fumbles lost: -2
--   receptions: 0 (standard), 0.5 (half-PPR), 1 (PPR)
-- Not yet included: fumble-recovery TDs.

DROP VIEW IF EXISTS vw_player_season_fantasy;
DROP VIEW IF EXISTS vw_player_game_fantasy;

CREATE VIEW vw_player_game_fantasy AS
WITH base AS (
    SELECT
        g.season,
        g.week,
        g.week_label,
        g.game_type,
        g.game_id,
        g.game_date,
        o.player_id,
        p.player_name,
        ps.position,
        o.team_abbr,
        CASE WHEN o.team_abbr = g.home_team THEN g.away_team ELSE g.home_team END AS opponent,
        CASE WHEN o.team_abbr = g.home_team THEN 'home' ELSE 'away' END            AS home_away,
        COALESCE(o.pass_att, 0)     AS pass_att,
        COALESCE(o.pass_cmp, 0)     AS pass_cmp,
        COALESCE(o.pass_yds, 0)     AS pass_yds,
        COALESCE(o.pass_td, 0)      AS pass_td,
        COALESCE(o.pass_int, 0)     AS pass_int,
        COALESCE(o.rush_att, 0)     AS rush_att,
        COALESCE(o.rush_yds, 0)     AS rush_yds,
        COALESCE(o.rush_td, 0)      AS rush_td,
        COALESCE(o.targets, 0)      AS targets,
        COALESCE(o.rec, 0)          AS rec,
        COALESCE(o.rec_yds, 0)      AS rec_yds,
        COALESCE(o.rec_td, 0)       AS rec_td,
        COALESCE(o.pass_2pt, 0) + COALESCE(o.rush_2pt, 0) + COALESCE(o.rec_2pt, 0) AS two_pt,
        COALESCE(o.st_td, 0)        AS st_td,
        COALESCE(o.fumbles_lost, 0) AS fumbles_lost
    FROM player_game_offense o
    JOIN games   g ON g.game_id = o.game_id
    JOIN players p ON p.player_id = o.player_id
    LEFT JOIN player_seasons ps ON ps.player_id = o.player_id AND ps.season = g.season
),
scored AS (
    SELECT
        base.*,
        ( pass_yds * 0.04 + pass_td * 4 - pass_int * 2
        + rush_yds * 0.1  + rush_td * 6
        + rec_yds  * 0.1  + rec_td  * 6
        + two_pt * 2      + st_td   * 6
        - fumbles_lost * 2 ) AS pts_standard
    FROM base
)
SELECT
    scored.*,
    ROUND(CAST(pts_standard + rec * 0.5 AS NUMERIC), 2) AS pts_half_ppr,
    ROUND(CAST(pts_standard + rec       AS NUMERIC), 2) AS pts_ppr
FROM scored;
