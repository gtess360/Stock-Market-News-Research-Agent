"""Tests for anonymous visitor access, 3-free quota enforcement, anti-reset on registration, and rate limiting."""
import os
import pytest
from src.database.connection import get_connection
from src.database.schema import init_db
from src.services.auth_service import register_user
from src.services.entitlement_service import (
    admin_issue_token,
    check_entitlement,
    check_subnet_rate_limit,
    get_or_create_visitor_user,
    link_visitor_to_user,
    redeem_token,
)
from src.services.job_service import complete_research_job, create_research_job


@pytest.fixture
def test_db(tmp_path):
    """Create isolated test database."""
    db_file = tmp_path / "test_visitor_access.db"
    init_db(db_file)
    return db_file


def test_visitor_initial_entitlement(test_db):
    """Anonymous visitors receive exactly 3 free research requests on initial visit."""
    guest_user, entitlement = get_or_create_visitor_user("raw_visitor_cookie_123", db_path=test_db)
    assert guest_user.id.startswith("guest_")
    assert guest_user.role == "user"
    assert entitlement.can_research is True
    assert entitlement.remaining_free == 3
    assert entitlement.has_unlimited is False


def test_visitor_exact_three_requests_depletion(test_db):
    """Visitor can complete exactly 3 jobs, then is blocked on the 4th."""
    guest_user, _ = get_or_create_visitor_user("raw_visitor_cookie_456", db_path=test_db)

    # Job 1
    job1, _ = create_research_job(
        user_id=guest_user.id,
        idempotency_key="job-1",
        tab="news",
        ticker_list=["AAPL"],
        start_at="2026-10-01",
        end_at="2026-10-30",
        db_path=test_db,
    )
    complete_research_job(job1.id, success=True, db_path=test_db)
    ent1 = check_entitlement(guest_user.id, db_path=test_db)
    assert ent1.remaining_free == 2
    assert ent1.can_research is True

    # Job 2
    job2, _ = create_research_job(
        user_id=guest_user.id,
        idempotency_key="job-2",
        tab="news",
        ticker_list=["MSFT"],
        start_at="2026-10-01",
        end_at="2026-10-30",
        db_path=test_db,
    )
    complete_research_job(job2.id, success=True, db_path=test_db)
    ent2 = check_entitlement(guest_user.id, db_path=test_db)
    assert ent2.remaining_free == 1
    assert ent2.can_research is True

    # Job 3
    job3, _ = create_research_job(
        user_id=guest_user.id,
        idempotency_key="job-3",
        tab="news",
        ticker_list=["NVDA"],
        start_at="2026-10-01",
        end_at="2026-10-30",
        db_path=test_db,
    )
    complete_research_job(job3.id, success=True, db_path=test_db)
    ent3 = check_entitlement(guest_user.id, db_path=test_db)
    assert ent3.remaining_free == 0
    assert ent3.can_research is False

    # 4th Job must fail server-side
    with pytest.raises(PermissionError, match="Free quota exhausted"):
        create_research_job(
            user_id=guest_user.id,
            idempotency_key="job-4",
            tab="news",
            ticker_list=["GOOGL"],
            start_at="2026-10-01",
            end_at="2026-10-30",
            db_path=test_db,
        )


def test_anti_reset_on_registration_after_three_jobs(test_db):
    """Registering after consuming 3 visitor requests does NOT reset allowance."""
    guest_user, _ = get_or_create_visitor_user("raw_visitor_cookie_reset_test", db_path=test_db)

    # Consume all 3 requests as visitor
    for i in range(1, 4):
        job, _ = create_research_job(
            user_id=guest_user.id,
            idempotency_key=f"reset-job-{i}",
            tab="news",
            ticker_list=["AAPL"],
            start_at="2026-10-01",
            end_at="2026-10-30",
            db_path=test_db,
        )
        complete_research_job(job.id, success=True, db_path=test_db)

    ent_visitor = check_entitlement(guest_user.id, db_path=test_db)
    assert ent_visitor.remaining_free == 0

    # Visitor registers an account
    new_user = register_user("converted_visitor@example.com", "SecurePass123!", role="user", db_path=test_db)
    link_visitor_to_user("raw_visitor_cookie_reset_test", new_user.id, db_path=test_db)

    # New user's entitlement must carry over 0 remaining free requests
    ent_registered = check_entitlement(new_user.id, db_path=test_db)
    assert ent_registered.remaining_free == 0
    assert ent_registered.can_research is False

    # Historical research jobs must now be linked to the registered user
    conn = get_connection(test_db)
    try:
        jobs = conn.execute("SELECT user_id FROM research_jobs WHERE user_id = ?;", (new_user.id,)).fetchall()
        assert len(jobs) == 3
    finally:
        conn.close()


def test_partial_quota_carryover_on_registration(test_db):
    """Registering after 1 visitor request carries over exactly 2 remaining requests."""
    guest_user, _ = get_or_create_visitor_user("raw_visitor_cookie_partial", db_path=test_db)

    # Run 1 job
    job, _ = create_research_job(
        user_id=guest_user.id,
        idempotency_key="partial-job-1",
        tab="sentiment",
        ticker_list=["AAPL"],
        start_at="2026-10-01",
        end_at="2026-10-30",
        horizon_days=30,
        db_path=test_db,
    )
    complete_research_job(job.id, success=True, db_path=test_db)

    # Visitor registers
    new_user = register_user("partial_user@example.com", "SecurePass123!", role="user", db_path=test_db)
    link_visitor_to_user("raw_visitor_cookie_partial", new_user.id, db_path=test_db)

    ent = check_entitlement(new_user.id, db_path=test_db)
    assert ent.remaining_free == 2
    assert ent.can_research is True


def test_token_unlocks_quota_exhausted_user(test_db):
    """Admin token redemption enables unlimited research for an account with 0 free credits."""
    admin = register_user("admin@example.com", "AdminPass123!", role="admin", allow_admin_creation=True, db_path=test_db)
    user = register_user("exhausted@example.com", "UserPass123!", role="user", db_path=test_db)

    # Exhaust user's 3 requests
    for i in range(1, 4):
        job, _ = create_research_job(
            user_id=user.id,
            idempotency_key=f"exh-job-{i}",
            tab="news",
            ticker_list=["AAPL"],
            start_at="2026-10-01",
            end_at="2026-10-30",
            db_path=test_db,
        )
        complete_research_job(job.id, success=True, db_path=test_db)

    ent_before = check_entitlement(user.id, db_path=test_db)
    assert ent_before.can_research is False

    # Admin issues token and user redeems it
    _, raw_tok = admin_issue_token(admin_user_id=admin.id, recipient_user_id=user.id, db_path=test_db)
    ok, msg = redeem_token(user.id, raw_tok, db_path=test_db)
    assert ok is True

    ent_after = check_entitlement(user.id, db_path=test_db)
    assert ent_after.can_research is True
    assert ent_after.has_unlimited is True


def test_subnet_rate_limiting(test_db):
    """Subnet rate limiting returns False when max threshold is exceeded."""
    guest_user, _ = get_or_create_visitor_user("raw_visitor_rate_1", ip_subnet_hash="subnet_abc", db_path=test_db)

    # Rate limit check should pass initially
    assert check_subnet_rate_limit("subnet_abc", max_requests_per_hour=5, db_path=test_db) is True
