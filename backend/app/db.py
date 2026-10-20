"""SQLite access helpers."""

import os
import sqlite3
from pathlib import Path

import pandas as pd

from app.scenario import DATA_DIR


def db_path() -> Path:
    return Path(os.environ.get("DEMO_DB_PATH", DATA_DIR / "demo.db"))


def connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise FileNotFoundError(f"Database not found at {path}. Run `python scripts/seed.py` first.")
    return sqlite3.connect(path)


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [r[0] for r in rows]


def row_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


def column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]


def read_sql(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn, params=params)


def table_as_text(conn: sqlite3.Connection, table: str, where: str = "", params: tuple = ()) -> str:
    """Serialise a table (or a filtered slice) as CSV, the way it would be pasted into an AI's context."""
    df = read_sql(conn, f'SELECT * FROM "{table}" {where}', params)
    return f"### table: {table} ({len(df)} rows)\n{df.to_csv(index=False)}"
