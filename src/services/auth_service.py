"""Authentication, rate limiting, password recovery, and session management service."""
import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple
from src.database.connection import get_connection
from src.models.user import User
from src.services.audit_service import log_audit_event

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COMMON_PASSWORDS = {"password", "password123", "12345678", "admin123", "qwerty123", "letmein123"}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15


def validate_password_strength(password: str) -> None:
    """Validate password against complexity and common-password policies."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must contain at least one letter.")
    if not re.search(r"[\d\W_]", password):
        raise ValueError("Password must contain at least one digit or special character.")
    if password.lower() in COMMON_PASSWORDS:
        raise ValueError("Password is too common or easily guessable.")


def hash_password(password: str) -> Tuple[str, str]:
    """Hash password using scrypt with a cryptographically secure random salt."""
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        maxmem=32 * 1024 * 1024,
    )
    salt_hex = salt.hex()
    hash_hex = derived.hex()
    formatted = f"scrypt$16384$8$1${salt_hex}${hash_hex}"
    return formatted, salt_hex


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored scrypt hash using constant-time comparison."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False
        n = int(parts[1])
        r = int(parts[2])
        p = int(parts[3])
        salt = bytes.fromhex(parts[4])
        expected_hash = bytes.fromhex(parts[5])

        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            maxmem=32 * 1024 * 1024,
        )
        return hmac.compare_digest(derived, expected_hash)
    except Exception:
        return False


def check_login_rate_limit(
    subject: str,
    db_path: Optional[Path | str] = None,
) -> Tuple[bool, int]:
    """Check if subject has exceeded maximum failed login attempts within window.
    
    Returns:
        Tuple[bool, int]: (allowed, remaining_cooldown_seconds)
    """
    cleaned = subject.strip().lower()
    now_dt = datetime.now(timezone.utc)
    cutoff = (now_dt - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)).isoformat()

    conn = get_connection(db_path)
    try:
        # Count failed attempts since cutoff
        rows = conn.execute(
            """
            SELECT attempted_at
            FROM login_attempts
            WHERE subject = ? AND success = 0 AND attempted_at > ?
            ORDER BY attempted_at ASC;
            """,
            (cleaned, cutoff),
        ).fetchall()

        if len(rows) >= MAX_LOGIN_ATTEMPTS:
            earliest_dt = datetime.fromisoformat(rows[0]["attempted_at"])
            cooldown_end = earliest_dt + timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
            remaining_sec = max(1, int((cooldown_end - now_dt).total_seconds()))
            return False, remaining_sec
        return True, 0
    finally:
        conn.close()


def record_login_attempt(
    subject: str,
    success: bool,
    ip_address: Optional[str] = None,
    db_path: Optional[Path | str] = None,
) -> None:
    """Record an authentication attempt for rate limiting and threat detection."""
    cleaned = subject.strip().lower()
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO login_attempts (id, subject, ip_address, attempted_at, success)
                VALUES (?, ?, ?, ?, ?);
                """,
                (str(uuid.uuid4()), cleaned, ip_address, now, 1 if success else 0),
            )
    finally:
        conn.close()


def register_user(
    email: str,
    password: str,
    role: str = "user",
    allow_admin_creation: bool = False,
    db_path: Optional[Path | str] = None,
) -> User:
    """Register a new user. Role defaults strictly to 'user' to prevent privilege escalation."""
    cleaned_email = email.strip().lower()
    if not EMAIL_REGEX.match(cleaned_email):
        raise ValueError("Invalid email format.")
    
    validate_password_strength(password)

    # Prevent unapproved administrator role assignment
    if role == "admin" and not allow_admin_creation:
        raise PermissionError("Direct registration of administrator accounts is restricted. Use admin bootstrap.")
    if role not in ("user", "admin"):
        raise ValueError(f"Invalid role: {role}")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    pwd_hash, salt_hex = hash_password(password)

    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO users (id, auth_provider_subject, role, created_at, status)
                VALUES (?, ?, ?, ?, 'active');
                """,
                (user_id, cleaned_email, role, now),
            )
            conn.execute(
                """
                INSERT INTO user_credentials (user_id, password_hash, salt, algorithm, created_at, updated_at)
                VALUES (?, ?, ?, 'scrypt', ?, ?);
                """,
                (user_id, pwd_hash, salt_hex, now, now),
            )
            conn.execute(
                """
                INSERT INTO usage_accounts (user_id, free_success_count, updated_at, version)
                VALUES (?, 0, ?, 1);
                """,
                (user_id, now),
            )
        log_audit_event("USER_REGISTERED", actor_user_id=user_id, subject_id=user_id, metadata={"role": role}, db_path=db_path)
        return User(
            id=user_id,
            auth_provider_subject=cleaned_email,
            role=role,
            created_at=now,
            status="active",
        )
    finally:
        conn.close()


def bootstrap_admin_user(
    email: str,
    password: str,
    db_path: Optional[Path | str] = None,
) -> User:
    """Authorized bootstrap mechanism to create the root administrator account."""
    return register_user(email, password, role="admin", allow_admin_creation=True, db_path=db_path)


def promote_user_to_admin(
    admin_user_id: str,
    target_user_id: str,
    db_path: Optional[Path | str] = None,
) -> bool:
    """Promote an existing user to admin. Requires active admin authorization."""
    conn = get_connection(db_path)
    try:
        admin_row = conn.execute("SELECT role FROM users WHERE id = ?;", (admin_user_id,)).fetchone()
        if not admin_row or admin_row["role"] != "admin":
            raise PermissionError("Only active administrators can promote users.")

        with conn:
            cursor = conn.execute("UPDATE users SET role = 'admin' WHERE id = ?;", (target_user_id,))
            promoted = cursor.rowcount > 0

        if promoted:
            log_audit_event("USER_PROMOTED_TO_ADMIN", actor_user_id=admin_user_id, subject_id=target_user_id, db_path=db_path)
        return promoted
    finally:
        conn.close()


def authenticate_user(
    email: str,
    password: str,
    ip_address: Optional[str] = None,
    db_path: Optional[Path | str] = None,
) -> Optional[User]:
    """Verify user credentials with brute-force rate limit enforcement."""
    cleaned_email = email.strip().lower()

    # Rate limiting check
    allowed, cooldown = check_login_rate_limit(cleaned_email, db_path=db_path)
    if not allowed:
        log_audit_event("LOGIN_BLOCKED_RATE_LIMIT", subject_id=cleaned_email, metadata={"cooldown_seconds": cooldown}, db_path=db_path)
        raise PermissionError(f"Too many failed login attempts. Please wait {cooldown} seconds before trying again.")

    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT u.id, u.auth_provider_subject, u.role, u.created_at, u.status, c.password_hash
            FROM users u
            JOIN user_credentials c ON u.id = c.user_id
            WHERE u.auth_provider_subject = ?;
            """,
            (cleaned_email,),
        ).fetchone()

        if not row or row["status"] != "active":
            record_login_attempt(cleaned_email, success=False, ip_address=ip_address, db_path=db_path)
            log_audit_event("USER_LOGIN_FAILED", subject_id=cleaned_email, metadata={"reason": "user_not_found_or_inactive"}, db_path=db_path)
            return None

        if not verify_password(password, row["password_hash"]):
            record_login_attempt(cleaned_email, success=False, ip_address=ip_address, db_path=db_path)
            log_audit_event("USER_LOGIN_FAILED", actor_user_id=row["id"], subject_id=cleaned_email, metadata={"reason": "bad_password"}, db_path=db_path)
            return None

        # Successful login: record attempt
        record_login_attempt(cleaned_email, success=True, ip_address=ip_address, db_path=db_path)
        user = User(
            id=row["id"],
            auth_provider_subject=row["auth_provider_subject"],
            role=row["role"],
            created_at=row["created_at"],
            status=row["status"],
        )
        log_audit_event("USER_LOGIN_SUCCESS", actor_user_id=user.id, subject_id=user.id, db_path=db_path)
        return user
    finally:
        conn.close()


def create_session(
    user_id: str,
    duration_hours: int = 24,
    db_path: Optional[Path | str] = None,
) -> Tuple[str, str]:
    """Generate high-entropy session token, store hash, and return (session_id, raw_token)."""
    session_id = str(uuid.uuid4())
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    expires_at = (now_dt + timedelta(hours=duration_hours)).isoformat()

    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO user_sessions (id, user_id, session_token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (session_id, user_id, token_hash, now, expires_at),
            )
        log_audit_event("SESSION_CREATED", actor_user_id=user_id, subject_id=session_id, db_path=db_path)
        return session_id, raw_token
    finally:
        conn.close()


def validate_session(
    raw_session_token: str,
    db_path: Optional[Path | str] = None,
) -> Optional[User]:
    """Validate raw session token hash against active unexpired sessions."""
    if not raw_session_token:
        return None
    token_hash = hashlib.sha256(raw_session_token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT u.id, u.auth_provider_subject, u.role, u.created_at, u.status
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token_hash = ?
              AND s.revoked_at IS NULL
              AND s.expires_at > ?
              AND u.status = 'active';
            """,
            (token_hash, now),
        ).fetchone()

        if not row:
            return None
        return User(
            id=row["id"],
            auth_provider_subject=row["auth_provider_subject"],
            role=row["role"],
            created_at=row["created_at"],
            status=row["status"],
        )
    finally:
        conn.close()


def revoke_session(
    raw_session_token: str,
    db_path: Optional[Path | str] = None,
) -> bool:
    """Revoke session token on logout."""
    if not raw_session_token:
        return False
    token_hash = hashlib.sha256(raw_session_token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE user_sessions
                SET revoked_at = ?
                WHERE session_token_hash = ? AND revoked_at IS NULL;
                """,
                (now, token_hash),
            )
            updated = cursor.rowcount > 0
        if updated:
            log_audit_event("SESSION_REVOKED", db_path=db_path)
        return updated
    finally:
        conn.close()


def revoke_all_user_sessions(
    user_id: str,
    db_path: Optional[Path | str] = None,
) -> int:
    """Revoke all active sessions for a user (e.g. following password reset)."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE user_sessions
                SET revoked_at = ?
                WHERE user_id = ? AND revoked_at IS NULL;
                """,
                (now, user_id),
            )
            count = cursor.rowcount
        log_audit_event("ALL_SESSIONS_REVOKED", actor_user_id=user_id, metadata={"count": count}, db_path=db_path)
        return count
    finally:
        conn.close()


def request_password_reset(
    email: str,
    duration_minutes: int = 30,
    db_path: Optional[Path | str] = None,
) -> Tuple[bool, Optional[str]]:
    """Initiate secure password reset. Returns (success, raw_reset_token)."""
    cleaned_email = email.strip().lower()
    conn = get_connection(db_path)
    try:
        user_row = conn.execute("SELECT id FROM users WHERE auth_provider_subject = ? AND status = 'active';", (cleaned_email,)).fetchone()
        if not user_row:
            # Silent return to prevent account enumeration
            return True, None

        user_id = user_row["id"]
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        expires_at = (now_dt + timedelta(minutes=duration_minutes)).isoformat()

        with conn:
            conn.execute(
                """
                INSERT INTO password_resets (id, user_id, reset_token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (str(uuid.uuid4()), user_id, token_hash, now, expires_at),
            )
        log_audit_event("PASSWORD_RESET_REQUESTED", actor_user_id=user_id, subject_id=user_id, db_path=db_path)
        return True, raw_token
    finally:
        conn.close()


def reset_password_with_token(
    raw_reset_token: str,
    new_password: str,
    db_path: Optional[Path | str] = None,
) -> Tuple[bool, str]:
    """Complete password reset with valid token, update scrypt hash, and revoke all active sessions."""
    if not raw_reset_token:
        return False, "Token cannot be empty."

    validate_password_strength(new_password)
    token_hash = hashlib.sha256(raw_reset_token.strip().encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection(db_path)
    try:
        reset_row = conn.execute(
            """
            SELECT id, user_id, expires_at, used_at
            FROM password_resets
            WHERE reset_token_hash = ?;
            """,
            (token_hash,),
        ).fetchone()

        if not reset_row:
            return False, "Invalid or expired password reset token."
        if reset_row["used_at"] is not None:
            return False, "Reset token has already been used."
        if reset_row["expires_at"] <= now:
            return False, "Reset token has expired."

        user_id = reset_row["user_id"]
        new_pwd_hash, new_salt = hash_password(new_password)

        with conn:
            # 1. Update password
            conn.execute(
                """
                UPDATE user_credentials
                SET password_hash = ?, salt = ?, updated_at = ?
                WHERE user_id = ?;
                """,
                (new_pwd_hash, new_salt, now, user_id),
            )
            # 2. Mark reset token as used
            conn.execute(
                """
                UPDATE password_resets
                SET used_at = ?
                WHERE id = ?;
                """,
                (now, reset_row["id"]),
            )
            # 3. Terminate all active sessions for security
            conn.execute(
                """
                UPDATE user_sessions
                SET revoked_at = ?
                WHERE user_id = ? AND revoked_at IS NULL;
                """,
                (now, user_id),
            )

        log_audit_event("PASSWORD_RESET_COMPLETED", actor_user_id=user_id, subject_id=user_id, db_path=db_path)
        return True, "Password reset successfully. All existing sessions revoked."
    finally:
        conn.close()
