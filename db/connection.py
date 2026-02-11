"""SQLite connection factory and database initialization."""

import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "spec_agent.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create a SQLite connection with row factory and foreign keys enabled."""
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path | None = None) -> None:
    """Create all tables if they don't exist."""
    path = db_path or DB_PATH
    # Ensure data directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(path)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.close()
