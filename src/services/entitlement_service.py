"""Entitlement, quota tracking, and access token lifecycle management."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple
from src.database.connection import get_connection
from src.models.token import AccessToken, EntitlementStatus, TokenRequest
from src.models.user import User
from src.services.audit_service import log_audit_event


def hash_token(raw_token: Any) -> str:
    """Compute SHA-256 hash of access token for secure persistence."""
    token = str(raw_token).strip() if raw_token is not None else ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def format_token_prefix(raw_token: str) -> str:
    """Extract masked display prefix for token tracking."""
    token = raw_token.strip()
    if len(token) <= 12:
        return f"{token[:4]}..."
    return f"{token[:8]}...{token[-4:]}"


def check_entitlement(user_id: str, db_path: Optional[Path | str] = None) -> EntitlementStatus:
    """Evaluate server-side entitlement status for a user."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        # 1. Fetch user record
        user_row = conn.execute(
            "SELECT id, auth_provider_subject, role, status FROM users WHERE id = ?;",
            (user_id,),
        ).fetchone()

        if not user_row or user_row["status"] != "active":
            return EntitlementStatus(
                can_research=False,
                reason="Account is inactive or does not exist.",
                remaining_free=0,
                has_unlimited=False,
                user_id=user_id,
                role="unknown",
            )

        role = user_row["role"]

        # 2. Check for active, unexpired, non-revoked unlimited access token
        token_row = conn.execute(
            """
            SELECT id, token_prefix, expires_at
            FROM access_tokens
            WHERE issued_to_user_id = ?
              AND status IN ('active', 'redeemed')
              AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > ?);
            """,
            (user_id, now),
        ).fetchone()

        if token_row:
            return EntitlementStatus(
                can_research=True,
                reason="Unlimited access token active.",
                remaining_free=0,
                has_unlimited=True,
                user_id=user_id,
                role=role,
            )

        # 3. Check free quota usage
        usage_row = conn.execute(
            "SELECT free_success_count FROM usage_accounts WHERE user_id = ?;",
            (user_id,),
        ).fetchone()

        free_used = usage_row["free_success_count"] if usage_row else 0
        remaining_free = max(0, 3 - free_used)

        if remaining_free > 0:
            plural = "s" if remaining_free != 1 else ""
            return EntitlementStatus(
                can_research=True,
                reason=f"Free access tier: {remaining_free} research request{plural} remaining.",
                remaining_free=remaining_free,
                has_unlimited=False,
                user_id=user_id,
                role=role,
            )
        else:
            return EntitlementStatus(
                can_research=False,
                reason="Free quota exhausted (3/3 used). Token required for further research.",
                remaining_free=0,
                has_unlimited=False,
                user_id=user_id,
                role=role,
            )
    finally:
        conn.close()


def redeem_token(
    user_id: str,
    raw_token: str,
    db_path: Optional[Path | str] = None,
) -> Tuple[bool, str]:
    """Validate and redeem an access token, binding it to the user."""
    cleaned = raw_token.strip()
    if not cleaned:
        return False, "Token cannot be empty."

    token_digest = hash_token(cleaned)
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()

    conn = get_connection(db_path)
    try:
        token_row = conn.execute(
            """
            SELECT id, issued_to_user_id, status, expires_at, revoked_at
            FROM access_tokens
            WHERE token_hash = ?;
            """,
            (token_digest,),
        ).fetchone()

        if not token_row:
            log_audit_event("TOKEN_REDEMPTION_FAILED", actor_user_id=user_id, metadata={"reason": "not_found"}, db_path=db_path)
            return False, "Invalid access token."

        if token_row["revoked_at"] is not None or token_row["status"] == "revoked":
            log_audit_event("TOKEN_REDEMPTION_FAILED", actor_user_id=user_id, subject_id=token_row["id"], metadata={"reason": "revoked"}, db_path=db_path)
            return False, "Access token has been revoked."

        if token_row["expires_at"] and token_row["expires_at"] <= now:
            with conn:
                conn.execute("UPDATE access_tokens SET status = 'expired' WHERE id = ?;", (token_row["id"],))
            log_audit_event("TOKEN_REDEMPTION_FAILED", actor_user_id=user_id, subject_id=token_row["id"], metadata={"reason": "expired"}, db_path=db_path)
            return False, "Access token has expired."

        if token_row["issued_to_user_id"] and token_row["issued_to_user_id"] != user_id:
            log_audit_event("TOKEN_REDEMPTION_FAILED", actor_user_id=user_id, subject_id=token_row["id"], metadata={"reason": "bound_to_other"}, db_path=db_path)
            return False, "Access token is bound to another user account."

        # Bind token to user and mark redeemed
        with conn:
            conn.execute(
                """
                UPDATE access_tokens
                SET issued_to_user_id = ?, status = 'redeemed', redeemed_at = ?
                WHERE id = ?;
                """,
                (user_id, now, token_row["id"]),
            )

        log_audit_event("TOKEN_REDEEMED", actor_user_id=user_id, subject_id=token_row["id"], db_path=db_path)
        return True, "Access token redeemed successfully. Unlimited research enabled."
    finally:
        conn.close()


def request_token(
    user_id: str,
    reason: Optional[str] = None,
    db_path: Optional[Path | str] = None,
) -> TokenRequest:
    """Submit a request for an unlimited access token."""
    req_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO token_requests (id, user_id, status, reason, requested_at)
                VALUES (?, ?, 'pending', ?, ?);
                """,
                (req_id, user_id, reason, now),
            )
        log_audit_event("TOKEN_REQUESTED", actor_user_id=user_id, subject_id=req_id, metadata={"reason": reason}, db_path=db_path)
        return TokenRequest(
            id=req_id,
            user_id=user_id,
            status="pending",
            reason=reason,
            requested_at=now,
        )
    finally:
        conn.close()


def admin_issue_token(
    admin_user_id: str,
    recipient_user_id: Optional[str] = None,
    expires_in_days: Optional[int] = None,
    db_path: Optional[Path | str] = None,
) -> Tuple[AccessToken, str]:
    """Issue a high-entropy access token. Returns (AccessToken, raw_token_plaintext)."""
    conn = get_connection(db_path)
    try:
        # Check admin role
        admin_row = conn.execute("SELECT role FROM users WHERE id = ?;", (admin_user_id,)).fetchone()
        if not admin_row or admin_row["role"] != "admin":
            raise PermissionError("Only administrators may issue access tokens.")

        token_id = str(uuid.uuid4())
        raw_secret = secrets.token_urlsafe(32)
        raw_token = f"sk_res_{raw_secret}"
        token_digest = hash_token(raw_token)
        prefix = format_token_prefix(raw_token)
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        expires_at = (now_dt + timedelta(days=expires_in_days)).isoformat() if expires_in_days else None

        with conn:
            conn.execute(
                """
                INSERT INTO access_tokens (
                    id, token_hash, token_prefix, issued_to_user_id, status, 
                    created_at, expires_at, issued_by_admin_id
                )
                VALUES (?, ?, ?, ?, 'active', ?, ?, ?);
                """,
                (token_id, token_digest, prefix, recipient_user_id, now, expires_at, admin_user_id),
            )

        log_audit_event(
            "TOKEN_ISSUED",
            actor_user_id=admin_user_id,
            subject_id=token_id,
            metadata={"prefix": prefix, "recipient": recipient_user_id, "expires_at": expires_at},
            db_path=db_path,
        )

        model = AccessToken(
            id=token_id,
            token_hash=token_digest,
            token_prefix=prefix,
            issued_to_user_id=recipient_user_id,
            status="active",
            created_at=now,
            expires_at=expires_at,
            issued_by_admin_id=admin_user_id,
        )
        return model, raw_token
    finally:
        conn.close()


def admin_revoke_token(
    admin_user_id: str,
    token_id: str,
    db_path: Optional[Path | str] = None,
) -> bool:
    """Revoke an active access token."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        admin_row = conn.execute("SELECT role FROM users WHERE id = ?;", (admin_user_id,)).fetchone()
        if not admin_row or admin_row["role"] != "admin":
            raise PermissionError("Only administrators may revoke access tokens.")

        with conn:
            cursor = conn.execute(
                """
                UPDATE access_tokens
                SET status = 'revoked', revoked_at = ?
                WHERE id = ? AND revoked_at IS NULL;
                """,
                (now, token_id),
            )
            success = cursor.rowcount > 0

        if success:
            log_audit_event("TOKEN_REVOKED", actor_user_id=admin_user_id, subject_id=token_id, db_path=db_path)
        return success
    finally:
        conn.close()


def admin_list_token_requests(
    admin_user_id: str,
    status_filter: Optional[str] = None,
    db_path: Optional[Path | str] = None,
) -> List[TokenRequest]:
    """Retrieve token requests for administrative review."""
    conn = get_connection(db_path)
    try:
        admin_row = conn.execute("SELECT role FROM users WHERE id = ?;", (admin_user_id,)).fetchone()
        if not admin_row or admin_row["role"] != "admin":
            raise PermissionError("Only administrators may review token requests.")

        if status_filter:
            rows = conn.execute(
                "SELECT id, user_id, status, reason, requested_at, reviewed_at, reviewer_id FROM token_requests WHERE status = ? ORDER BY requested_at DESC;",
                (status_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, user_id, status, reason, requested_at, reviewed_at, reviewer_id FROM token_requests ORDER BY requested_at DESC;"
            ).fetchall()

        return [
            TokenRequest(
                id=r["id"],
                user_id=r["user_id"],
                status=r["status"],
                reason=r["reason"],
                requested_at=r["requested_at"],
                reviewed_at=r["reviewed_at"],
                reviewer_id=r["reviewer_id"],
            )
            for r in rows
        ]
    finally:
        conn.close()


def admin_review_token_request(
    admin_user_id: str,
    request_id: str,
    approve: bool,
    expires_in_days: Optional[int] = None,
    db_path: Optional[Path | str] = None,
) -> Tuple[bool, Optional[str]]:
    """Approve or reject a pending token request. If approved, generates and returns token."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        admin_row = conn.execute("SELECT role FROM users WHERE id = ?;", (admin_user_id,)).fetchone()
        if not admin_row or admin_row["role"] != "admin":
            raise PermissionError("Only administrators may review token requests.")

        req_row = conn.execute("SELECT id, user_id, status FROM token_requests WHERE id = ?;", (request_id,)).fetchone()
        if not req_row or req_row["status"] != "pending":
            return False, None

        user_id = req_row["user_id"]
        status = "approved" if approve else "rejected"

        with conn:
            conn.execute(
                """
                UPDATE token_requests
                SET status = ?, reviewed_at = ?, reviewer_id = ?
                WHERE id = ?;
                """,
                (status, now, admin_user_id, request_id),
            )

        log_audit_event(
            "TOKEN_REQUEST_REVIEWED",
            actor_user_id=admin_user_id,
            subject_id=request_id,
            metadata={"decision": status, "user_id": user_id},
            db_path=db_path,
        )

        raw_token = None
        if approve:
            _, raw_token = admin_issue_token(
                admin_user_id=admin_user_id,
                recipient_user_id=user_id,
                expires_in_days=expires_in_days,
                db_path=db_path,
            )

        return True, raw_token
    finally:
        conn.close()


def get_or_create_visitor_user(
    visitor_token: str,
    ip_subnet_hash: str = "default_subnet",
    db_path: Optional[Path | str] = None,
) -> Tuple[User, EntitlementStatus]:
    """Ensure a visitor guest user and visitor_quotas record exist.
    
    Returns:
        Tuple[User, EntitlementStatus]: The active guest user and current entitlement.
    """
    cleaned = visitor_token.strip() if visitor_token else secrets.token_hex(16)
    v_hash = hash_token(cleaned)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        # Check existing visitor quota row
        row = conn.execute(
            """
            SELECT visitor_token_hash, free_success_count, linked_user_id
            FROM visitor_quotas
            WHERE visitor_token_hash = ?;
            """,
            (v_hash,),
        ).fetchone()

        target_user_id: Optional[str] = None
        if row and row["linked_user_id"]:
            target_user_id = row["linked_user_id"]

        if not target_user_id:
            guest_id = f"guest_{v_hash[:16]}"
            target_user_id = guest_id

        # Verify or create the user record
        user_row = conn.execute(
            "SELECT id, auth_provider_subject, role, status, created_at FROM users WHERE id = ?;",
            (target_user_id,),
        ).fetchone()

        with conn:
            if not user_row:
                conn.execute(
                    """
                    INSERT INTO users (id, auth_provider_subject, role, created_at, status)
                    VALUES (?, ?, 'user', ?, 'active');
                    """,
                    (target_user_id, f"{target_user_id}@visitor.local", now),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO usage_accounts (user_id, free_success_count, updated_at, version)
                    VALUES (?, 0, ?, 1);
                    """,
                    (target_user_id, now),
                )
                user_row = conn.execute(
                    "SELECT id, auth_provider_subject, role, status, created_at FROM users WHERE id = ?;",
                    (target_user_id,),
                ).fetchone()

            if not row:
                conn.execute(
                    """
                    INSERT INTO visitor_quotas (visitor_token_hash, ip_subnet_hash, free_success_count, created_at, updated_at, linked_user_id)
                    VALUES (?, ?, 0, ?, ?, ?);
                    """,
                    (v_hash, ip_subnet_hash, now, now, target_user_id),
                )

        user = User(
            id=user_row["id"],
            auth_provider_subject=user_row["auth_provider_subject"],
            role=user_row["role"],
            status=user_row["status"],
            created_at=user_row["created_at"],
        )
    finally:
        conn.close()

    entitlement = check_entitlement(user.id, db_path=db_path)
    return user, entitlement


def link_visitor_to_user(
    visitor_token: str,
    user_id: str,
    db_path: Optional[Path | str] = None,
) -> None:
    """Link an anonymous visitor session to an authenticated/registered user.
    
    Transfers consumed quota count and re-keys historical research jobs so the user
    maintains their history while preventing allowance resets on signup.
    """
    cleaned = visitor_token.strip() if visitor_token else ""
    if not cleaned:
        return

    v_hash = hash_token(cleaned)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        with conn:
            row = conn.execute(
                "SELECT free_success_count, linked_user_id FROM visitor_quotas WHERE visitor_token_hash = ?;",
                (v_hash,),
            ).fetchone()

            if not row:
                conn.execute(
                    """
                    INSERT INTO visitor_quotas (visitor_token_hash, ip_subnet_hash, free_success_count, created_at, updated_at, linked_user_id)
                    VALUES (?, 'linked', 0, ?, ?, ?);
                    """,
                    (v_hash, now, now, user_id),
                )
                return

            visitor_used = row["free_success_count"]
            old_guest_id = row["linked_user_id"]

            # Transfer quota: Account's consumed count cannot be lower than what was consumed as visitor
            usage_row = conn.execute(
                "SELECT free_success_count FROM usage_accounts WHERE user_id = ?;",
                (user_id,),
            ).fetchone()
            current_count = usage_row["free_success_count"] if usage_row else 0
            new_count = min(3, max(current_count, visitor_used))

            conn.execute(
                """
                UPDATE usage_accounts
                SET free_success_count = ?, updated_at = ?
                WHERE user_id = ?;
                """,
                (new_count, now, user_id),
            )

            # Update visitor quota link
            conn.execute(
                """
                UPDATE visitor_quotas
                SET linked_user_id = ?, free_success_count = ?, updated_at = ?
                WHERE visitor_token_hash = ?;
                """,
                (user_id, new_count, now, v_hash),
            )

            # Re-associate historical research jobs from the guest account to the authenticated user
            if old_guest_id and old_guest_id.startswith("guest_") and old_guest_id != user_id:
                conn.execute(
                    "UPDATE research_jobs SET user_id = ? WHERE user_id = ?;",
                    (user_id, old_guest_id),
                )
                conn.execute(
                    "UPDATE audit_events SET actor_user_id = ? WHERE actor_user_id = ?;",
                    (user_id, old_guest_id),
                )
    finally:
        conn.close()


def check_subnet_rate_limit(
    ip_subnet_hash: str,
    max_requests_per_hour: int = 15,
    db_path: Optional[Path | str] = None,
) -> bool:
    """Evaluate sliding-window rate limit for a subnet to prevent automated abuse."""
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT COUNT(j.id) as recent_count
            FROM research_jobs j
            JOIN visitor_quotas vq ON j.user_id = vq.linked_user_id
            WHERE vq.ip_subnet_hash = ? AND j.created_at >= ?;
            """,
            (ip_subnet_hash, one_hour_ago),
        ).fetchone()
        recent_count = row["recent_count"] if row else 0
        return recent_count < max_requests_per_hour
    finally:
        conn.close()

