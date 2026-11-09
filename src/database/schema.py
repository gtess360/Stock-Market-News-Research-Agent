"""Database schema definition and initialization utilities."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from src.database.connection import get_connection

SCHEMA_VERSION = 3

SCHEMA_DDL = """
-- Schema migration metadata
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT NOT NULL
);

-- 1. Users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    auth_provider_subject TEXT UNIQUE NOT NULL, -- Email or OAuth subject
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deactivated'))
);

-- 2. User credentials (password authentication)
CREATE TABLE IF NOT EXISTS user_credentials (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    algorithm TEXT NOT NULL DEFAULT 'scrypt',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 3. User sessions (server-side session management)
CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);

-- 4. Login rate limiting and brute force defense
CREATE TABLE IF NOT EXISTS login_attempts (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    ip_address TEXT,
    attempted_at TEXT NOT NULL,
    success INTEGER NOT NULL CHECK (success IN (0, 1))
);

-- 5. Password reset tokens (account recovery)
CREATE TABLE IF NOT EXISTS password_resets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reset_token_hash TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT
);

-- 6. Usage accounts (free tier tracking: 3 successful research jobs lifetime)
CREATE TABLE IF NOT EXISTS usage_accounts (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    free_success_count INTEGER NOT NULL DEFAULT 0 CHECK (free_success_count >= 0 AND free_success_count <= 3),
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);

-- 7. Access tokens (unlimited access tier)
CREATE TABLE IF NOT EXISTS access_tokens (
    id TEXT PRIMARY KEY,
    token_hash TEXT UNIQUE NOT NULL,
    token_prefix TEXT NOT NULL,
    issued_to_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'redeemed', 'expired', 'revoked')),
    created_at TEXT NOT NULL,
    expires_at TEXT,
    revoked_at TEXT,
    issued_by_admin_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    redeemed_at TEXT
);

-- 8. Token requests
CREATE TABLE IF NOT EXISTS token_requests (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reason TEXT,
    requested_at TEXT NOT NULL,
    reviewed_at TEXT,
    reviewer_id TEXT REFERENCES users(id) ON DELETE SET NULL
);

-- 9. Research jobs (with idempotency and credit debit flag)
CREATE TABLE IF NOT EXISTS research_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    idempotency_key TEXT NOT NULL,
    tab TEXT NOT NULL CHECK (tab IN ('news', 'sentiment')),
    ticker_list_json TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    horizon_days INTEGER CHECK (horizon_days IS NULL OR horizon_days IN (1, 7, 30, 90)),
    status TEXT NOT NULL DEFAULT 'requested' CHECK (
        status IN ('requested', 'validating', 'authorized', 'collecting', 
                   'normalizing', 'verifying', 'analyzing', 'reporting', 
                   'completed', 'failed', 'cancelled', 'rate_limited', 'no_data')
    ),
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error_code TEXT,
    credit_debited INTEGER NOT NULL DEFAULT 0 CHECK (credit_debited IN (0, 1)),
    UNIQUE(user_id, idempotency_key)
);

-- 10. Source records
CREATE TABLE IF NOT EXISTS source_records (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES research_jobs(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    source_url TEXT NOT NULL,
    publisher TEXT NOT NULL,
    published_at TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    normalized_metadata_json TEXT
);

-- 11. Research reports
CREATE TABLE IF NOT EXISTS research_reports (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES research_jobs(id) ON DELETE CASCADE,
    report_json TEXT NOT NULL,
    markdown TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    model_version TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    limitations_json TEXT
);

-- 12. Audit events
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    actor_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    subject_id TEXT,
    created_at TEXT NOT NULL,
    metadata_json TEXT
);

-- 13. Visitor quotas (anonymous 3-free-job quota tracking and abuse defense)
CREATE TABLE IF NOT EXISTS visitor_quotas (
    visitor_token_hash TEXT PRIMARY KEY,
    ip_subnet_hash TEXT NOT NULL,
    free_success_count INTEGER NOT NULL DEFAULT 0 CHECK (free_success_count >= 0 AND free_success_count <= 3),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    linked_user_id TEXT REFERENCES users(id) ON DELETE SET NULL
);

-- Performance and Integrity Indexes
CREATE INDEX IF NOT EXISTS idx_users_subject ON users(auth_provider_subject);
CREATE INDEX IF NOT EXISTS idx_sessions_hash ON user_sessions(session_token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_login_attempts_subject ON login_attempts(subject, attempted_at);
CREATE INDEX IF NOT EXISTS idx_password_resets_hash ON password_resets(reset_token_hash);
CREATE INDEX IF NOT EXISTS idx_tokens_hash ON access_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_tokens_user ON access_tokens(issued_to_user_id);
CREATE INDEX IF NOT EXISTS idx_token_requests_user ON token_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON research_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_idempotency ON research_jobs(user_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_jobs_user_status ON research_jobs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_source_records_job ON source_records(job_id);
CREATE INDEX IF NOT EXISTS idx_reports_job ON research_reports(job_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_visitor_ip ON visitor_quotas(ip_subnet_hash);
CREATE INDEX IF NOT EXISTS idx_visitor_linked_user ON visitor_quotas(linked_user_id);
"""


def init_db(db_path: Optional[Path | str] = None) -> None:
    """Initialize SQLite database, execute repeatable DDL, and record migration state."""
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    try:
        with conn:
            conn.executescript(SCHEMA_DDL)
            # Record baseline and visitor schema migrations
            conn.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (version, applied_at, description)
                VALUES (2, ?, 'Phase 3.2 Security Hardened Schema');
                """,
                (now,),
            )
            conn.execute(
                """
                INSERT INTO schema_migrations (version, applied_at, description)
                VALUES (?, ?, 'Phase 4.5 Visitor Access & Quota Schema')
                ON CONFLICT(version) DO UPDATE SET applied_at = excluded.applied_at;
                """,
                (SCHEMA_VERSION, now),
            )
    finally:
        conn.close()
