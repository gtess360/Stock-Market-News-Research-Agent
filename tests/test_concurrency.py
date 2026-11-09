"""Concurrency and race condition tests for quota debiting."""
import concurrent.futures
import pytest
from src.database.connection import get_connection
from src.database.schema import init_db
from src.services.auth_service import register_user
from src.services.job_service import complete_research_job, create_research_job


@pytest.fixture
def conc_db(tmp_path):
    db_file = tmp_path / "conc_test.db"
    init_db(db_file)
    return db_file


def test_concurrent_quota_debiting_race_condition(conc_db):
    """Verify that when 1 free request remains, concurrent completions cannot double-spend."""
    user = register_user("concurrent_user@example.com", "Password123!", db_path=conc_db)

    # 1. User legitimately creates two active jobs when 2 credits remain (1 used + 2 active = 3 total)
    conn = get_connection(conc_db)
    with conn:
        conn.execute("UPDATE usage_accounts SET free_success_count = 1 WHERE user_id = ?;", (user.id,))
    conn.close()

    job1, _ = create_research_job(user.id, "conc_key_1", "news", ["AAPL"], "2026-10-01", "2026-11-01", db_path=conc_db)
    job2, _ = create_research_job(user.id, "conc_key_2", "news", ["MSFT"], "2026-10-01", "2026-11-01", db_path=conc_db)

    # 2. Simulate external transaction consuming one credit before completion, leaving exactly 1 credit available
    conn = get_connection(conc_db)
    with conn:
        conn.execute("UPDATE usage_accounts SET free_success_count = 2 WHERE user_id = ?;", (user.id,))
    conn.close()

    results = []
    errors = []

    def finish_job(j_id):
        try:
            res = complete_research_job(j_id, success=True, db_path=conc_db)
            return ("SUCCESS", res)
        except Exception as e:
            return ("ERROR", str(e))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(finish_job, job1.id)
        f2 = executor.submit(finish_job, job2.id)
        for f in concurrent.futures.as_completed([f1, f2]):
            status, val = f.result()
            if status == "SUCCESS":
                results.append(val)
            else:
                errors.append(val)

    # 3. Verify database state: free_success_count must be exactly 3 (never 4)
    conn = get_connection(conc_db)
    row = conn.execute("SELECT free_success_count FROM usage_accounts WHERE user_id = ?;", (user.id,)).fetchone()
    conn.close()

    assert row["free_success_count"] == 3
    # Exactly one job must have succeeded in debiting the final slot
    total_debited = sum(r.credit_debited for r in results)
    assert total_debited == 1
    # Exactly one error must have been reported due to quota exhaustion
    assert len(errors) == 1
    assert "quota exceeded" in errors[0].lower()
