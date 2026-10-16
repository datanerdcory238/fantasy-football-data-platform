-- 002_nflverse_source.sql
-- Switch the data source from Pro-Football-Reference (blocked automated access
-- with HTTP 403) to nflverse (open data published for programmatic use).
-- See docs/decisions.md.
--
-- Written so it runs on both PostgreSQL and SQLite (used by the tests):
-- one column per ALTER TABLE statement.

-- 1. Team rows loaded with PFR codes ('rav'/'BAL', 'kan'/'KAN', ...) are
--    replaced by nflverse abbreviations ('BAL', 'KC', ...) on the next load.
--    Safe to delete: no games reference them yet.
DELETE FROM teams;

-- 2. Stats that count in standard fantasy scoring but weren't in the PFR table.
ALTER TABLE player_game_offense ADD COLUMN pass_2pt INTEGER;  -- 2-point conversion passes
ALTER TABLE player_game_offense ADD COLUMN rush_2pt INTEGER;  -- 2-point conversion runs
ALTER TABLE player_game_offense ADD COLUMN rec_2pt  INTEGER;  -- 2-point conversion catches
ALTER TABLE player_game_offense ADD COLUMN st_td    INTEGER;  -- special-teams (return) TDs

-- 3. nflverse's own fantasy points, kept ONLY to check our view's math.
--    The official numbers are still calculated in vw_player_game_fantasy.
ALTER TABLE player_game_offense ADD COLUMN src_pts_standard NUMERIC(6, 2);
ALTER TABLE player_game_offense ADD COLUMN src_pts_ppr      NUMERIC(6, 2);
