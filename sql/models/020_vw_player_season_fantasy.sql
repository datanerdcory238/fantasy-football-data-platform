-- vw_player_season_fantasy
-- Season totals and per-game averages per player (regular season only).

CREATE VIEW vw_player_season_fantasy AS
SELECT
    season,
    player_id,
    player_name,
    position,
    STRING_AGG(DISTINCT team_abbr, '/')       AS teams,
    COUNT(*)                                  AS games_played,
    SUM(pass_yds)                             AS pass_yds,
    SUM(pass_td)                              AS pass_td,
    SUM(pass_int)                             AS pass_int,
    SUM(rush_att)                             AS rush_att,
    SUM(rush_yds)                             AS rush_yds,
    SUM(rush_td)                              AS rush_td,
    SUM(targets)                              AS targets,
    SUM(rec)                                  AS rec,
    SUM(rec_yds)                              AS rec_yds,
    SUM(rec_td)                               AS rec_td,
    ROUND(CAST(SUM(pts_standard) AS NUMERIC), 2)      AS pts_standard,
    ROUND(CAST(SUM(pts_half_ppr) AS NUMERIC), 2)      AS pts_half_ppr,
    ROUND(CAST(SUM(pts_ppr) AS NUMERIC), 2)           AS pts_ppr,
    ROUND(CAST(SUM(pts_ppr) AS NUMERIC) / COUNT(*), 2) AS ppr_per_game
FROM vw_player_game_fantasy
WHERE game_type = 'REG'
GROUP BY season, player_id, player_name, position;
