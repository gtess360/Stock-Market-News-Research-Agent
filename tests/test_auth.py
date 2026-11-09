"""Unit and integration tests for authentication, rate limiting, and password recovery."""
import sqlite3
import pytest
from src.database.schema import init_db
from src.services.auth_service import (
    authenticate_user,
    bootstrap_admin_user,
    check_login_rate_limit,
    create_session,
    hash_password,
    promote_user_to_admin,
    register_user,
    request_password_reset,
    reset_password_with_token,
    revoke_session,
    validate_password_strength,
    validate_session,
    verify_password,
)


@pytest.fixture
def auth_db(tmp_path):
    """Fixture providing an isolated database for auth tests."""
    db_file = tmp_path / "auth_test.db"
    init_db(db_file)
    return db_file


def test_password_hashing_and_verification():
    """Verify scrypt password hashing produces different salts and verifies correctly."""
    pwd = "CorrectHorseBatteryStaple123!"
    hash1, salt1 = hash_password(pwd)
    hash2, salt2 = hash_password(pwd)

    assert hash1 != hash2  # Unique salts ensure unique digests
    assert salt1 != salt2
    assert verify_password(pwd, hash1) is True
    assert verify_password(pwd, hash2) is True
    assert verify_password("WrongPassword123!", hash1) is False
    assert verify_password("", hash1) is False


def test_password_complexity_rules():
    """Verify strict password strength validation."""
    with pytest.raises(ValueError, match="at least 8 characters"):
        validate_password_strength("Short1!")

    with pytest.raises(ValueError, match="at least one letter"):
        validate_password_strength("1234567890!")

    with pytest.raises(ValueError, match="at least one digit or special character"):
        validate_password_strength("AllLettersOnlyPassword")

    with pytest.raises(ValueError, match="too common"):
        validate_password_strength("password123")


def test_privilege_escalation_prevention(auth_db):
    """Verify regular registration cannot assign the admin role."""
    with pytest.raises(PermissionError, match="Direct registration of administrator"):
        register_user("attacker@example.com", "Password123!", role="admin", db_path=auth_db)

    # Legitimate bootstrap creates admin
    admin = bootstrap_admin_user("superadmin@example.com", "SuperSecretAdmin123!", db_path=auth_db)
    assert admin.role == "admin"

    # Regular user promotion requires active admin
    reg_user = register_user("junior@example.com", "JuniorPass123!", db_path=auth_db)
    assert reg_user.role == "user"

    # Unauthorized promotion fails
    with pytest.raises(PermissionError, match="Only active administrators"):
        promote_user_to_admin(reg_user.id, reg_user.id, db_path=auth_db)

    # Authorized promotion succeeds
    promoted = promote_user_to_admin(admin.id, reg_user.id, db_path=auth_db)
    assert promoted is True


def test_login_rate_limiting_defense(auth_db):
    """Verify that 5 consecutive failed logins trigger lockout."""
    email = "target@example.com"
    pwd = "CorrectPassword123!"
    register_user(email, pwd, db_path=auth_db)

    # 4 failed attempts: allowed
    for _ in range(4):
        assert authenticate_user(email, "WrongPassword!", db_path=auth_db) is None

    allowed, _ = check_login_rate_limit(email, db_path=auth_db)
    assert allowed is True

    # 5th failed attempt: triggers lockout
    assert authenticate_user(email, "WrongPassword!", db_path=auth_db) is None
    allowed, cooldown = check_login_rate_limit(email, db_path=auth_db)
    assert allowed is False
    assert cooldown > 0

    # 6th attempt: raises PermissionError even with correct password
    with pytest.raises(PermissionError, match="Too many failed login attempts"):
        authenticate_user(email, pwd, db_path=auth_db)


def test_password_recovery_and_session_invalidation(auth_db):
    """Verify password reset workflow and mandatory revocation of existing sessions."""
    email = "recovery@example.com"
    user = register_user(email, "OldPassword123!", db_path=auth_db)

    # User has an active session
    _, session_token = create_session(user.id, db_path=auth_db)
    assert validate_session(session_token, db_path=auth_db) is not None

    # Request reset token
    ok, reset_token = request_password_reset(email, duration_minutes=15, db_path=auth_db)
    assert ok is True
    assert reset_token is not None

    # Perform password reset
    success, msg = reset_password_with_token(reset_token, "NewBrandPassword456!", db_path=auth_db)
    assert success is True

    # Re-using the same token fails
    re_use, err = reset_password_with_token(reset_token, "AnotherPassword789!", db_path=auth_db)
    assert re_use is False
    assert "already been used" in err

    # Old password fails login, new password succeeds
    assert authenticate_user(email, "OldPassword123!", db_path=auth_db) is None
    new_user = authenticate_user(email, "NewBrandPassword456!", db_path=auth_db)
    assert new_user is not None

    # Previous session was invalidated upon password reset
    assert validate_session(session_token, db_path=auth_db) is None


def test_session_lifecycle(auth_db):
    """Verify server-side session token generation, validation, and revocation."""
    user = register_user("session_user@example.com", "SessionPass123!", db_path=auth_db)

    # Create session
    session_id, raw_token = create_session(user.id, duration_hours=12, db_path=auth_db)
    assert session_id is not None
    assert len(raw_token) > 20

    # Validate session
    validated_user = validate_session(raw_token, db_path=auth_db)
    assert validated_user is not None
    assert validated_user.id == user.id

    # Revoke session (logout)
    revoked = revoke_session(raw_token, db_path=auth_db)
    assert revoked is True

    # Re-validating revoked session returns None
    assert validate_session(raw_token, db_path=auth_db) is None
