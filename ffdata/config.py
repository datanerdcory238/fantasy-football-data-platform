"""Central configuration, read from environment variables (and a local .env file).

Keeping settings in one place means the rest of the code never hard-codes
passwords, paths, or tuning values. This pattern carries straight over to
AWS/Airflow later, where the same values come from secrets managers or
Airflow Variables instead of a .env file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # no-op if .env doesn't exist

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    pg_host: str = field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    pg_port: int = field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432")))
    pg_db: str = field(default_factory=lambda: os.getenv("POSTGRES_DB", "fantasy"))
    pg_user: str = field(default_factory=lambda: os.getenv("POSTGRES_USER", "fantasy"))
    pg_password: str = field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "fantasy"))

    delay_seconds: float = field(
        default_factory=lambda: float(os.getenv("SCRAPER_DELAY_SECONDS", "4"))
    )
    user_agent: str = field(
        default_factory=lambda: os.getenv(
            "SCRAPER_USER_AGENT", "ffdata-learning-project/0.1 (personal educational use)"
        )
    )
    raw_data_dir: Path = field(
        default_factory=lambda: PROJECT_ROOT / os.getenv("RAW_DATA_DIR", "data/raw")
    )

    @property
    def dsn(self) -> str:
        """libpq connection string used by psycopg."""
        return (
            f"host={self.pg_host} port={self.pg_port} dbname={self.pg_db} "
            f"user={self.pg_user} password={self.pg_password}"
        )


settings = Settings()
