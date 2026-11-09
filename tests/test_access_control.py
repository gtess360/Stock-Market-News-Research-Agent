"""Comprehensive tests for free tier quota, unlimited tokens, and access control."""
import json
import pytest
from src.database.connection import get_connection
from src.database.schema import init_db
from src.services.audit_service import log_audit_event
from src.services.auth_service import bootstrap_admin_user, register_user
from src.services.entitlement_service import (
    admin_issue_token,
    admin_list_token_requests,
    admin_review_token_request,
    admin_revoke_token,
    check_entitlement,
    hash_token,
    redeem_token,
    request_token,
)
from src.services.job_service import complete_research_job, create_research_job


@pytest.fixture
def access_db(tmp_path):
    """Fixture providing an isolated database for access control tests."""
    db_file = tmp_path / "access_test.db"
    init_db(db_file)
    return db_file


@pytest.fixture
def admin_user(access_db):
    return bootstrap_admin_user("admin@corp.internal", "AdminPassword123!", db_path=access_db)


@pytest.fixture
def regular_user(access_db):
    return register_user("user@example.com", "UserPassword123!", role="user", db_path=access_db)


def test_initial_free_quota(access_db, regular_user):
    """Verify new user receives 3 free research requests."""
    status = check_entitlement(regular_user.id, db_path=access_db)
    assert status.can_research is True
    assert status.remaining_free == 3
    assert status.has_unlimited is False


def test_free_quota_consumption(access_db, regular_user):
    """Verify quota decreases 3 -> 2 -> 1 -> 0 upon successful completion."""
    for i in range(3):
        status = check_entitlement(regular_user.id, db_path=access_db)
        assert status.can_research is True
        assert status.remaining_free == 3 - i

        # Create multi-stock job
        job, is_new = create_research_job(
            user_id=regular_user.id,
            idempotency_key=f"job_key_{i}",
            tab="news",
            ticker_list=["AAPL", "MSFT", "NVDA"],  # Multi-stock counts as 1 job
            start_at="2026-10-01",
            end_at="2026-11-01",
            db_path=access_db,
        )
        assert is_new is True

        # Complete job successfully
        completed = complete_research_job(job.id, success=True, db_path=access_db)
        assert completed.status == "completed"
        assert completed.credit_debited == 1

    # 4th request must be blocked
    status_final = check_entitlement(regular_user.id, db_path=access_db)
    assert status_final.can_research is False
    assert status_final.remaining_free == 0

    with pytest.raises(PermissionError, match="Free quota exhausted"):
        create_research_job(
            user_id=regular_user.id,
            idempotency_key="job_key_blocked",
            tab="news",
            ticker_list=["GOOGL"],
            start_at="2026-10-01",
            end_at="2026-11-01",
            db_path=access_db,
        )


def test_concurrent_job_submission_cap(access_db, regular_user):
    """Verify users cannot bypass quota by submitting multiple uncompleted jobs simultaneously."""
    # Set user to 2 used (1 remaining)
    conn = get_connection(access_db)
    with conn:
        conn.execute("UPDATE usage_accounts SET free_success_count = 2 WHERE user_id = ?;", (regular_user.id,))
    conn.close()

    # User creates job 1 (now 1 active, 2 used -> total 3)
    job1, _ = create_research_job(regular_user.id, "active_key_1", "news", ["AAPL"], "2026-10-01", "2026-11-01", db_path=access_db)
    assert job1.status == "requested"

    # User attempts to create a 2nd job before 1st completes: MUST BE BLOCKED
    with pytest.raises(PermissionError, match="Concurrent quota limit reached"):
        create_research_job(regular_user.id, "active_key_2", "news", ["MSFT"], "2026-10-01", "2026-11-01", db_path=access_db)

    # After job1 fails (or cancels), slot is released
    complete_research_job(job1.id, success=False, error_code="USER_CANCELLED", db_path=access_db)

    # Now user can submit again
    job2, _ = create_research_job(regular_user.id, "active_key_2", "news", ["MSFT"], "2026-10-01", "2026-11-01", db_path=access_db)
    assert job2.status == "requested"


def test_token_ownership_isolation(access_db, admin_user, regular_user):
    """Verify an access token issued for User A cannot be redeemed by User B."""
    other_user = register_user("other@example.com", "OtherPassword123!", db_path=access_db)

    # Issue token pre-bound to regular_user
    token_model, raw_token = admin_issue_token(admin_user.id, recipient_user_id=regular_user.id, db_path=access_db)

    # other_user attempts to redeem regular_user's token
    success, err = redeem_token(other_user.id, raw_token, db_path=access_db)
    assert success is False
    assert "bound to another user" in err

    # regular_user redeems successfully
    ok, msg = redeem_token(regular_user.id, raw_token, db_path=access_db)
    assert ok is True


def test_failed_and_duplicate_jobs_do_not_debit_credit(access_db, regular_user):
    """Verify that failed or retried jobs do not consume quota."""
    # 1. Failed job
    job, _ = create_research_job(
        user_id=regular_user.id,
        idempotency_key="failed_attempt_1",
        tab="sentiment",
        ticker_list=["TSLA"],
        start_at="2026-10-01",
        end_at="2026-11-01",
        horizon_days=30,
        db_path=access_db,
    )
    failed_job = complete_research_job(job.id, success=False, error_code="API_TIMEOUT", db_path=access_db)
    assert failed_job.status == "failed"
    assert failed_job.credit_debited == 0

    # Quota remains 3
    status = check_entitlement(regular_user.id, db_path=access_db)
    assert status.remaining_free == 3

    # 2. Duplicate submission (same idempotency key)
    job_dup, is_new = create_research_job(
        user_id=regular_user.id,
        idempotency_key="failed_attempt_1",
        tab="sentiment",
        ticker_list=["TSLA"],
        start_at="2026-10-01",
        end_at="2026-11-01",
        horizon_days=30,
        db_path=access_db,
    )
    assert is_new is False  # Re-used existing job
    assert job_dup.id == job.id


def test_token_request_and_admin_approval_flow(access_db, admin_user, regular_user):
    """Verify complete lifecycle: request -> admin review -> token issue -> redemption -> unlimited access."""
    # User exhausts free quota
    for i in range(3):
        j, _ = create_research_job(regular_user.id, f"k_{i}", "news", ["AAPL"], "2026-10-01", "2026-11-01", db_path=access_db)
        complete_research_job(j.id, success=True, db_path=access_db)

    # User submits token request
    req = request_token(regular_user.id, reason="Need unlimited access for market research", db_path=access_db)
    assert req.status == "pending"

    # Admin reviews and approves
    admin_reqs = admin_list_token_requests(admin_user.id, status_filter="pending", db_path=access_db)
    assert len(admin_reqs) == 1
    assert admin_reqs[0].id == req.id

    success, raw_token = admin_review_token_request(admin_user.id, req.id, approve=True, db_path=access_db)
    assert success is True
    assert raw_token is not None
    assert raw_token.startswith("sk_res_")

    # User redeems token
    redeemed, msg = redeem_token(regular_user.id, raw_token, db_path=access_db)
    assert redeemed is True

    # User now has unlimited access
    entitlement = check_entitlement(regular_user.id, db_path=access_db)
    assert entitlement.can_research is True
    assert entitlement.has_unlimited is True

    # 4th and 5th jobs can now be executed without debiting free quota
    j4, _ = create_research_job(regular_user.id, "unlimited_job_1", "news", ["AMZN"], "2026-10-01", "2026-11-01", db_path=access_db)
    c4 = complete_research_job(j4.id, success=True, db_path=access_db)
    assert c4.status == "completed"
    assert c4.credit_debited == 0


def test_token_revocation(access_db, admin_user, regular_user):
    """Verify admin token revocation immediately shuts down research access if quota is 0."""
    token_model, raw_token = admin_issue_token(admin_user.id, recipient_user_id=regular_user.id, db_path=access_db)
    redeem_token(regular_user.id, raw_token, db_path=access_db)

    # Exhaust free quota first to isolate token effect
    conn = get_connection(access_db)
    with conn:
        conn.execute("UPDATE usage_accounts SET free_success_count = 3 WHERE user_id = ?;", (regular_user.id,))
    conn.close()

    # User has unlimited access
    assert check_entitlement(regular_user.id, db_path=access_db).can_research is True

    # Admin revokes token
    revoked = admin_revoke_token(admin_user.id, token_model.id, db_path=access_db)
    assert revoked is True

    # Access is now immediately blocked
    status = check_entitlement(regular_user.id, db_path=access_db)
    assert status.can_research is False
    assert status.has_unlimited is False


def test_token_expiration(access_db, admin_user, regular_user):
    """Verify expired token is rejected."""
    # Issue token with expiration in the past
    token_model, raw_token = admin_issue_token(admin_user.id, recipient_user_id=regular_user.id, expires_in_days=-1, db_path=access_db)

    redeemed, err = redeem_token(regular_user.id, raw_token, db_path=access_db)
    assert redeemed is False
    assert "expired" in err.lower()


def test_unauthorized_admin_actions(access_db, regular_user):
    """Verify non-admin users cannot issue or revoke tokens."""
    with pytest.raises(PermissionError, match="Only administrators"):
        admin_issue_token(regular_user.id, db_path=access_db)

    with pytest.raises(PermissionError, match="Only administrators"):
        admin_revoke_token(regular_user.id, "fake-id", db_path=access_db)


def test_audit_log_redaction(access_db, regular_user):
    """Verify audit log redacts sensitive passwords and raw tokens."""
    log_audit_event(
        action="TEST_ACTION",
        actor_user_id=regular_user.id,
        metadata={"raw_token": "sk_res_supersecret", "password": "PlainTextPassword", "ticker": "AAPL"},
        db_path=access_db,
    )

    conn = get_connection(access_db)
    row = conn.execute("SELECT metadata_json FROM audit_events WHERE action = 'TEST_ACTION';").fetchone()
    conn.close()

    data = json.loads(row["metadata_json"])
    assert data["raw_token"] == "[REDACTED]"
    assert data["password"] == "[REDACTED]"
    assert data["ticker"] == "AAPL"
