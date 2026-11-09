"""Database connection and lifecycle management."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "app.db"


def get_db_path() -> Path:
    """Resolve database path from environment variable or default local path."""
    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        return Path(env_path).resolve()
    env_url = os.getenv("DATABASE_URL")
    if env_url and env_url.startswith("sqlite:///"):
        # Strip sqlite:/// prefix
        raw_path = env_url.replace("sqlite:///", "", 1)
        return Path(raw_path).resolve()
    return DEFAULT_DB_PATH.resolve()


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Create a configured SQLite connection with foreign keys and WAL enabled."""
    target_path = Path(db_path).resolve() if db_path else get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(
        database=str(target_path),
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        check_same_thread=False,
        timeout=30.0,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


@contextmanager
def get_db_cursor(db_path: Path | str | None = None) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager for executing database operations inside a managed transaction."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

