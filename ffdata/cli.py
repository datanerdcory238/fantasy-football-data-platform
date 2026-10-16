"""Command-line entry point.

Usage (from the repo root):
    python -m ffdata init-db
    python -m ffdata games  --season 2026
    python -m ffdata stats  --season 2026 --week 5   # --week is optional
    python -m ffdata season --season 2026            # games + stats + build-models
    python -m ffdata build-models
    python -m ffdata status
"""
from __future__ import annotations

import argparse
import logging
import sys

from . import db, pipeline
from .http import PoliteFetcher

log = logging.getLogger("ffdata")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ffdata", description="Fantasy football data collector")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="create tables (migrations) and views")
    sub.add_parser("build-models", help="(re)create SQL views in sql/models")
    sub.add_parser("status", help="show row counts and recent runs")

    for name, help_ in [
        ("games", "load the season's games (schedule and scores) from nflverse"),
        ("stats", "load weekly offensive player stats from nflverse"),
        ("season", "games + stats + build-models"),
    ]:
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("--season", type=int, required=True)
        if name == "stats":
            sp.add_argument("--week", type=int, help="limit to one week")
    return p


def cmd_status(conn) -> None:
    print("Row counts:")
    for table in ["teams", "games", "players", "player_seasons", "player_game_offense"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<22}{n:>8}")
    print("\nRecent runs:")
    rows = conn.execute(
        "SELECT run_id, command, args, status, pages_fetched, pages_cached, rows_loaded, "
        "started_at FROM scrape_runs ORDER BY run_id DESC LIMIT 10"
    ).fetchall()
    for r in rows:
        print(f"  #{r[0]:<4} {r[1]:<10} {r[2] or '':<22} {r[3]:<8} "
              f"fetched={r[4]} cached={r[5]} rows={r[6]}  {r[7]:%Y-%m-%d %H:%M}")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    with db.connect() as conn:
        if args.command == "init-db":
            applied = db.apply_migrations(conn)
            db.build_models(conn)
            print(f"migrations applied: {applied or 'none (already up to date)'}")
            return 0
        if args.command == "build-models":
            print(f"built: {db.build_models(conn)}")
            return 0
        if args.command == "status":
            cmd_status(conn)
            return 0

        # Load commands: wrap in a logged run.
        week = getattr(args, "week", None)
        arg_str = f"season={args.season}" + (f" week={week}" if week else "")
        run_id = db.start_run(conn, args.command, arg_str)
        stats = pipeline.RunStats()
        fetcher = PoliteFetcher()
        try:
            if args.command in ("games", "season"):
                pipeline.load_games(conn, fetcher, args.season, stats)
            if args.command in ("stats", "season"):
                pipeline.load_player_stats(conn, fetcher, args.season, stats, week=week)
            if args.command == "season":
                db.build_models(conn)
        except Exception as exc:
            conn.rollback()
            db.finish_run(conn, run_id, "failed", stats.as_dict(), repr(exc))
            log.exception("run #%d failed", run_id)
            return 1

        db.finish_run(conn, run_id, "success", stats.as_dict())
        print(f"run #{run_id} success: {stats.as_dict()}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
