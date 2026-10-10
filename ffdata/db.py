"""Database helpers: connecting, migrations, SQL models, and idempotent upserts.

Key idea — **idempotency**: every load uses ``INSERT ... ON CONFLICT DO UPDATE``
(an "upsert") keyed on the table's natural primary key. Re-running the same
scrape updates rows instead of duplicating them, so the pipeline is always
safe to re-run. Airflow (Step 3) relies on exactly this property for retries
and backfills.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .config import PROJECT_ROOT, settings

log = logging.getLogger(__name__)

SCHEMA_DIR = PROJECT_ROOT / "sql" / "schema"
MODELS_DIR = PROJECT_ROOT / "sql" / "models"


def connect():
    """Open a PostgreSQL connection (psycopg 3)."""
    import psycopg  # imported lazily so unit tests don't need it installed

    return psycopg.connect(settings.dsn)


# --------------------------------------------------------------------------- #
# Small compatibility layer so tests can run against in-memory SQLite.
# --------------------------------------------------------------------------- #
def _is_sqlite(conn) -> bool:
    return isinstance(conn, sqlite3.Connection)


def param(conn, name: str) -> str:
    return f":{name}" if _is_sqlite(conn) else f"%({name})s"


def run_script(conn, sql: str) -> None:
    """Execute a multi-statement SQL script."""
    if _is_sqlite(conn):
        # SQLite's auto-increment spelling differs from Postgres' SERIAL.
        conn.executescript(sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY"))
    else:
        with conn.cursor() as cur:
            cur.execute(sql)


# --------------------------------------------------------------------------- #
# Migrations & models
# --------------------------------------------------------------------------- #
def apply_migrations(conn, schema_dir: Path = SCHEMA_DIR) -> list[str]:
    """Apply sql/schema/*.sql files in order, each exactly once."""
    run_script(
        conn,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    TEXT PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    )
    applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    newly_applied = []
    for path in sorted(schema_dir.glob("*.sql")):
        if path.name in applied:
            continue
        log.info("applying migration %s", path.name)
        run_script(conn, path.read_text())
        conn.execute(
            f"INSERT INTO schema_migrations (version) VALUES ({param(conn, 'v')})",
            {"v": path.name},
        )
        newly_applied.append(path.name)
    conn.commit()
    return newly_applied


def build_models(conn, models_dir: Path = MODELS_DIR) -> list[str]:
    """(Re)create the SQL views in sql/models/*.sql, in filename order."""
    built = []
    for path in sorted(models_dir.glob("*.sql")):
        log.info("building model %s", path.name)
        run_script(conn, path.read_text())
        built.append(path.name)
    conn.commit()
    return built


# --------------------------------------------------------------------------- #
# Upsert
# --------------------------------------------------------------------------- #
def upsert(
    conn,
    table: str,
    rows: Iterable[dict[str, Any]],
    key_cols: list[str],
    columns: list[str] | None = None,
    touch_updated_at: bool = True,
) -> int:
    """Insert rows, updating non-key columns when the key already exists.

    ``table``/``columns`` come from our own code (never user input), so it is
    safe to format them into the SQL string; *values* are always parameterised.
    """
    rows = list(rows)
    if not rows:
        return 0
    columns = columns or list(rows[0].keys())
    update_cols = [c for c in columns if c not in key_cols]

    set_parts = [f"{c} = EXCLUDED.{c}" for c in update_cols]
    if touch_updated_at:
        set_parts.append("updated_at = CURRENT_TIMESTAMP")
    conflict_action = f"DO UPDATE SET {', '.join(set_parts)}" if set_parts else "DO NOTHING"

    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) "
        f"VALUES ({', '.join(param(conn, c) for c in columns)}) "
        f"ON CONFLICT ({', '.join(key_cols)}) {conflict_action}"
    )
    payload = [{c: r.get(c) for c in columns} for r in rows]
    if _is_sqlite(conn):
        conn.executemany(sql, payload)
    else:
        with conn.cursor() as cur:
            cur.executemany(sql, payload)
    return len(payload)


# --------------------------------------------------------------------------- #
# Run log (scrape_runs table)
# --------------------------------------------------------------------------- #
def start_run(conn, command: str, args: str) -> int:
    row = conn.execute(
        f"INSERT INTO scrape_runs (command, args) VALUES "
        f"({param(conn, 'command')}, {param(conn, 'args')}) RETURNING run_id",
        {"command": command, "args": args},
    ).fetchone()
    conn.commit()
    return row[0]


def finish_run(conn, run_id: int, status: str, stats: dict[str, int], error: str | None = None):
    conn.execute(
        "UPDATE scrape_runs SET finished_at = CURRENT_TIMESTAMP, "
        f"status = {param(conn, 'status')}, "
        f"pages_fetched = {param(conn, 'pages_fetched')}, "
        f"pages_cached = {param(conn, 'pages_cached')}, "
        f"rows_loaded = {param(conn, 'rows_loaded')}, "
        f"error = {param(conn, 'error')} "
        f"WHERE run_id = {param(conn, 'run_id')}",
        {
            "status": status,
            "pages_fetched": stats.get("pages_fetched", 0),
            "pages_cached": stats.get("pages_cached", 0),
            "rows_loaded": stats.get("rows_loaded", 0),
            "error": error,
            "run_id": run_id,
        },
    )
    conn.commit()
