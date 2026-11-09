"""Research job lifecycle, idempotency management, and atomic quota debiting."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional, Tuple
from src.database.connection import get_connection
from src.models.job import ResearchJob
from src.services.audit_service import log_audit_event
from src.services.entitlement_service import check_entitlement


def create_research_job(
    user_id: str,
    idempotency_key: str,
    tab: Literal["news", "sentiment"],
    ticker_list: List[str],
    start_at: str,
    end_at: str,
    horizon_days: Optional[Literal[1, 7, 30, 90]] = None,
    db_path: Optional[Path | str] = None,
) -> Tuple[ResearchJob, bool]:
    """Create a new research job with strict server-side entitlement check, active concurrency cap, and idempotency.
    
    Returns:
        Tuple[ResearchJob, bool]: (job, is_new_submission)
    """
    clean_tickers = sorted(list({t.strip().upper() for t in ticker_list if t.strip()}))
    if not clean_tickers:
        raise ValueError("At least one valid ticker symbol is required.")
    if tab not in ("news", "sentiment"):
        raise ValueError(f"Invalid research tab: {tab}")
    if tab == "sentiment" and horizon_days not in (1, 7, 30, 90):
        raise ValueError(f"Sentiment research requires valid horizon (1, 7, 30, 90). Got: {horizon_days}")

    conn = get_connection(db_path)
    try:
        # 1. Check idempotency: Return existing job if duplicate submission
        existing = conn.execute(
            """
            SELECT id, user_id, idempotency_key, tab, ticker_list_json, start_at, end_at, 
                   horizon_days, status, created_at, completed_at, error_code, credit_debited
            FROM research_jobs
            WHERE user_id = ? AND idempotency_key = ?;
            """,
            (user_id, idempotency_key),
        ).fetchone()

        if existing:
            return ResearchJob(
                id=existing["id"],
                user_id=existing["user_id"],
                idempotency_key=existing["idempotency_key"],
                tab=existing["tab"],
                ticker_list=json.loads(existing["ticker_list_json"]),
                start_at=existing["start_at"],
                end_at=existing["end_at"],
                horizon_days=existing["horizon_days"],
                status=existing["status"],
                created_at=existing["created_at"],
                completed_at=existing["completed_at"],
                error_code=existing["error_code"],
                credit_debited=existing["credit_debited"],
            ), False

        # 2. Server-side entitlement gate
        entitlement = check_entitlement(user_id, db_path=db_path)
        if not entitlement.can_research:
            raise PermissionError(entitlement.reason)

        # 3. Prevent concurrent submission bypass for free-tier accounts
        if not entitlement.has_unlimited:
            active_row = conn.execute(
                """
                SELECT COUNT(*) as active_count
                FROM research_jobs
                WHERE user_id = ? AND status IN (
                    'requested', 'validating', 'authorized', 'collecting', 
                    'normalizing', 'verifying', 'analyzing', 'reporting'
                );
                """,
                (user_id,),
            ).fetchone()
            active_count = active_row["active_count"] if active_row else 0

            usage_row = conn.execute("SELECT free_success_count FROM usage_accounts WHERE user_id = ?;", (user_id,)).fetchone()
            used_count = usage_row["free_success_count"] if usage_row else 0

            if (used_count + active_count) >= 3:
                raise PermissionError(
                    f"Concurrent quota limit reached: You have {active_count} active job(s) and {used_count}/3 used requests. "
                    "Total active plus completed jobs cannot exceed your free tier limit (3)."
                )

        # 4. Create new job record
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        tickers_json = json.dumps(clean_tickers)

        with conn:
            conn.execute(
                """
                INSERT INTO research_jobs (
                    id, user_id, idempotency_key, tab, ticker_list_json, 
                    start_at, end_at, horizon_days, status, created_at, credit_debited
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'requested', ?, 0);
                """,
                (job_id, user_id, idempotency_key, tab, tickers_json, start_at, end_at, horizon_days, now),
            )

        log_audit_event(
            "RESEARCH_JOB_CREATED",
            actor_user_id=user_id,
            subject_id=job_id,
            metadata={"tab": tab, "tickers": clean_tickers, "idempotency_key": idempotency_key},
            db_path=db_path,
        )

        job = ResearchJob(
            id=job_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
            tab=tab,
            ticker_list=clean_tickers,
            start_at=start_at,
            end_at=end_at,
            horizon_days=horizon_days,
            status="requested",
            created_at=now,
            credit_debited=0,
        )
        return job, True
    finally:
        conn.close()


def complete_research_job(
    job_id: str,
    success: bool,
    error_code: Optional[str] = None,
    db_path: Optional[Path | str] = None,
) -> ResearchJob:
    """Complete a research job. Atomically debit one free request ONLY on success for free-tier users."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        with conn:
            job_row = conn.execute(
                """
                SELECT id, user_id, idempotency_key, tab, ticker_list_json, start_at, end_at, 
                       horizon_days, status, created_at, credit_debited
                FROM research_jobs
                WHERE id = ?;
                """,
                (job_id,),
            ).fetchone()

            if not job_row:
                raise ValueError(f"Job not found: {job_id}")

            user_id = job_row["user_id"]
            already_debited = bool(job_row["credit_debited"])

            if not success:
                # Failed job: mark failed, DO NOT debit free credit
                conn.execute(
                    """
                    UPDATE research_jobs
                    SET status = 'failed', completed_at = ?, error_code = ?
                    WHERE id = ?;
                    """,
                    (now, error_code or "UNKNOWN_ERROR", job_id),
                )
                debited = 0
                final_status = "failed"
            else:
                # Successful job
                final_status = "completed"
                # Check if user has unlimited access token
                entitlement = check_entitlement(user_id, db_path=db_path)
                
                if entitlement.has_unlimited:
                    # User is on unlimited tier; do not debit free quota counter
                    debited = 0
                else:
                    # Free tier: atomically debit exactly 1 credit if not already debited
                    if not already_debited:
                        cursor = conn.execute(
                            """
                            UPDATE usage_accounts
                            SET free_success_count = free_success_count + 1,
                                updated_at = ?,
                                version = version + 1
                            WHERE user_id = ? AND free_success_count < 3;
                            """,
                            (now, user_id),
                        )
                        if cursor.rowcount == 0:
                            # Concurrency edge-case: free quota was consumed by a concurrent job
                            conn.execute(
                                """
                                UPDATE research_jobs
                                SET status = 'failed', completed_at = ?, error_code = 'QUOTA_EXCEEDED'
                                WHERE id = ?;
                                """,
                                (now, job_id),
                            )
                            raise PermissionError("Free request quota exceeded before job completion.")
                        debited = 1

                        # Also sync visitor_quotas if this user is linked to a visitor session
                        conn.execute(
                            """
                            UPDATE visitor_quotas
                            SET free_success_count = MIN(3, free_success_count + 1), updated_at = ?
                            WHERE linked_user_id = ?;
                            """,
                            (now, user_id),
                        )
                    else:
                        debited = 1

                conn.execute(
                    """
                    UPDATE research_jobs
                    SET status = 'completed', completed_at = ?, credit_debited = ?, error_code = NULL
                    WHERE id = ?;
                    """,
                    (now, debited, job_id),
                )

        log_audit_event(
            "RESEARCH_JOB_COMPLETED",
            actor_user_id=user_id,
            subject_id=job_id,
            metadata={"status": final_status, "debited": debited, "error_code": error_code},
            db_path=db_path,
        )

        return ResearchJob(
            id=job_row["id"],
            user_id=user_id,
            idempotency_key=job_row["idempotency_key"],
            tab=job_row["tab"],
            ticker_list=json.loads(job_row["ticker_list_json"]),
            start_at=job_row["start_at"],
            end_at=job_row["end_at"],
            horizon_days=job_row["horizon_days"],
            status=final_status,
            created_at=job_row["created_at"],
            completed_at=now,
            error_code=error_code if not success else None,
            credit_debited=debited,
        )
    finally:
        conn.close()


def list_user_jobs(
    user_id: str,
    limit: int = 20,
    db_path: Optional[Path | str] = None,
) -> List[dict]:
    """Retrieve recent research jobs for a user, with associated report metadata if available."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT j.id, j.tab, j.ticker_list_json, j.start_at, j.end_at, j.horizon_days,
                   j.status, j.created_at, j.completed_at, j.error_code, j.credit_debited,
                   r.markdown as report_markdown
            FROM research_jobs j
            LEFT JOIN research_reports r ON j.id = r.job_id
            WHERE j.user_id = ?
            ORDER BY j.created_at DESC
            LIMIT ?;
            """,
            (user_id, limit),
        ).fetchall()
        jobs = []
        for r in rows:
            jobs.append({
                "id": r["id"],
                "tab": r["tab"],
                "tickers": json.loads(r["ticker_list_json"]),
                "start_at": r["start_at"],
                "end_at": r["end_at"],
                "horizon_days": r["horizon_days"],
                "status": r["status"],
                "created_at": r["created_at"],
                "completed_at": r["completed_at"],
                "error_code": r["error_code"],
                "credit_debited": bool(r["credit_debited"]),
                "report_markdown": r["report_markdown"],
            })
        return jobs
    finally:
        conn.close()

