"""Audit logging service for security and compliance tracking."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from src.database.connection import get_connection


def sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    """Sanitize metadata dictionary, stripping potential passwords or raw tokens."""
    if not metadata:
        return None
    sanitized = {}
    sensitive_keys = {"password", "token", "secret", "raw_token", "key"}
    for k, v in metadata.items():
        if any(sens in k.lower() for sens in sensitive_keys):
            sanitized[k] = "[REDACTED]"
        else:
            sanitized[k] = v
    return json.dumps(sanitized)


def log_audit_event(
    action: str,
    actor_user_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: Optional[Path | str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> str:
    """Record a security or operational event to the audit_events table."""
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    meta_json = sanitize_metadata(metadata)

    if conn is not None:
        conn.execute(
            """
            INSERT INTO audit_events (id, actor_user_id, action, subject_id, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (event_id, actor_user_id, action, subject_id, now, meta_json),
        )
        return event_id

    managed_conn = get_connection(db_path)
    try:
        with managed_conn:
            managed_conn.execute(
                """
                INSERT INTO audit_events (id, actor_user_id, action, subject_id, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (event_id, actor_user_id, action, subject_id, now, meta_json),
            )
        return event_id
    finally:
        managed_conn.close()


def get_recent_audit_logs(limit: int = 25, db_path: Optional[Path | str] = None) -> list:
    """Retrieve recent audit events for compliance review."""
    managed_conn = get_connection(db_path)
    try:
        rows = managed_conn.execute(
            """
            SELECT id, actor_user_id, action, subject_id, created_at, metadata_json
            FROM audit_events
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "actor_user_id": r["actor_user_id"],
                "action": r["action"],
                "subject_id": r["subject_id"],
                "created_at": r["created_at"],
                "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else {},
            }
            for r in rows
        ]
    finally:
        managed_conn.close()

