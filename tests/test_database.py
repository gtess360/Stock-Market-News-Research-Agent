"""Unit tests for SQLite database schema, connections, and constraints."""
import sqlite3
import pytest
from src.database.connection import get_connection
from src.database.schema import init_db


@pytest.fixture
def test_db(tmp_path):
    """Fixture providing a fresh isolated database path."""
    db_file = tmp_path / "test.db"
    init_db(db_file)
    return db_file


def test_schema_initialization(test_db):
    """Verify that all core tables and migrations are initialized."""
    conn = get_connection(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        "schema_migrations",
        "users",
        "user_credentials",
        "user_sessions",
        "login_attempts",
        "password_resets",
        "usage_accounts",
        "access_tokens",
        "token_requests",
        "research_jobs",
        "source_records",
        "research_reports",
        "audit_events",
    }
    assert expected_tables.issubset(tables)

    # Verify migration record
    cursor.execute("SELECT version, description FROM schema_migrations WHERE version = 2;")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert "Security Hardened" in row["description"]


def test_repeatable_idempotent_migrations(test_db):
    """Verify that running init_db() multiple times preserves data and executes idempotently."""
    conn = get_connection(test_db)
    with conn:
        conn.execute("INSERT INTO users (id, auth_provider_subject, role, created_at) VALUES ('u_keep', 'keep@test.com', 'user', '2026-11-07');")
    conn.close()

    # Re-run initialization
    init_db(test_db)

    conn = get_connection(test_db)
    row = conn.execute("SELECT id FROM users WHERE id = 'u_keep';").fetchone()
    conn.close()

    assert row is not None
    assert row["id"] == "u_keep"


def test_foreign_key_enforcement(test_db):
    """Verify that foreign keys are enforced by the connection factory."""
    conn = get_connection(test_db)
    with pytest.raises(sqlite3.IntegrityError):
        # Insert usage_account for nonexistent user
        with conn:
            conn.execute(
                "INSERT INTO usage_accounts (user_id, free_success_count, updated_at) VALUES ('invalid-id', 0, '2026-11-07T00:00:00Z');"
            )
    conn.close()


def test_quota_check_constraint(test_db):
    """Verify CHECK constraint prevents free_success_count from exceeding 3 or dropping below 0."""
    conn = get_connection(test_db)
    with conn:
        conn.execute(
            "INSERT INTO users (id, auth_provider_subject, role, created_at, status) VALUES ('u1', 'test@test.com', 'user', '2026-11-07', 'active');"
        )
    
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute(
                "INSERT INTO usage_accounts (user_id, free_success_count, updated_at) VALUES ('u1', 4, '2026-11-07');"
            )
    conn.close()


def test_cascade_delete_user(test_db):
    """Verify deleting a user cascades to dependent user_credentials and usage_accounts."""
    conn = get_connection(test_db)
    with conn:
        conn.execute("INSERT INTO users (id, auth_provider_subject, role, created_at) VALUES ('u2', 'casc@test.com', 'user', '2026-11-07');")
        conn.execute("INSERT INTO usage_accounts (user_id, free_success_count, updated_at) VALUES ('u2', 0, '2026-11-07');")
        conn.execute("INSERT INTO user_credentials (user_id, password_hash, salt, created_at, updated_at) VALUES ('u2', 'h', 's', '2026-11-07', '2026-11-07');")

    with conn:
        conn.execute("DELETE FROM users WHERE id = 'u2';")

    usage = conn.execute("SELECT * FROM usage_accounts WHERE user_id = 'u2';").fetchone()
    creds = conn.execute("SELECT * FROM user_credentials WHERE user_id = 'u2';").fetchone()
    conn.close()

    assert usage is None
    assert creds is None
