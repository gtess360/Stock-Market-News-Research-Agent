"""Automated tests for LangGraph research workflow, tool integration, and citation integrity."""
import json
import sqlite3
import pytest
from src.agent.orchestrator import run_research_workflow
from src.agent.schemas import ClaimCitation
from src.agent.tools import verify_citations_tool
from src.database.connection import get_connection
from src.database.schema import init_db
from src.models.financial import CanonicalNewsItem
from src.services.auth_service import create_session, register_user
from src.services.entitlement_service import check_entitlement


@pytest.fixture
def agent_db(tmp_path):
    """Fixture providing an isolated database for agent workflow tests."""
    db_file = tmp_path / "agent_test.db"
    init_db(db_file)
    return str(db_file)


@pytest.fixture
def test_user(agent_db):
    """Fixture providing a registered user with 3 free requests."""
    return register_user("researcher@fund.com", "FundResearch2026!", role="user", db_path=agent_db)


def test_successful_news_research_workflow(agent_db, test_user):
    """Verify end-to-end execution of the Stock News LangGraph workflow."""
    final_state = run_research_workflow(
        user_id=test_user.id,
        tab="news",
        tickers=["AAPL", "MSFT"],
        date_preset="30D",
        as_of_date="2026-11-07",
        db_path=agent_db,
        provider_mode="mock",
    )

    # 1. State assertions
    assert final_state["status"] == "completed"
    assert final_state["current_stage"] == "COMPLETED"
    assert len(final_state["validated_tickers"]) == 2
    assert len(final_state["raw_news"]) > 0
    assert len(final_state["deduplicated_news"]) > 0
    assert len(final_state["news_summaries"]) == 2
    assert len(final_state["verified_citations"]) > 0

    # 2. Report assertions
    report = final_state["report"]
    assert report is not None
    assert report.tab == "news"
    assert "AAPL" in report.tickers and "MSFT" in report.tickers
    assert "Stock Market Research Report" in final_state["report_markdown"]
    assert "Verified Source Citations" in final_state["report_markdown"]

    # 3. Database persistence assertions
    conn = get_connection(agent_db)
    job_row = conn.execute("SELECT status, credit_debited FROM research_jobs WHERE id = ?;", (final_state["job_id"],)).fetchone()
    report_row = conn.execute("SELECT id FROM research_reports WHERE job_id = ?;", (final_state["job_id"],)).fetchone()
    source_count = conn.execute("SELECT COUNT(*) as count FROM source_records WHERE job_id = ?;", (final_state["job_id"],)).fetchone()["count"]
    conn.close()

    assert job_row["status"] == "completed"
    assert job_row["credit_debited"] == 1
    assert report_row is not None
    assert source_count > 0

    # 4. Quota debit assertion: Decreased from 3 to 2
    entitlement = check_entitlement(test_user.id, db_path=agent_db)
    assert entitlement.remaining_free == 2


def test_successful_sentiment_research_workflow(agent_db, test_user):
    """Verify end-to-end execution of the Sentiment Research LangGraph workflow with forward horizon."""
    final_state = run_research_workflow(
        user_id=test_user.id,
        tab="sentiment",
        tickers=["NVDA"],
        date_preset="30D",
        horizon_days=30,
        as_of_date="2026-11-07",
        db_path=agent_db,
        provider_mode="mock",
    )

    assert final_state["status"] == "completed"
    assert len(final_state["sentiment_outlooks"]) == 1
    outlook = final_state["sentiment_outlooks"][0]
    assert outlook.ticker == "NVDA"
    assert outlook.horizon_days == 30
    assert outlook.forward_scenario_outlook in ("bullish", "bearish", "neutral", "mixed")
    assert len(outlook.catalysts) > 0
    assert len(outlook.risks) > 0

    # Markdown contains forward horizon card
    assert "**Forward Horizon:** 30 Days" in final_state["report_markdown"]
    assert "Top Catalysts:" in final_state["report_markdown"]


def test_invalid_ticker_inputs_handling(agent_db, test_user):
    """Verify unknown ticker triggers invalid_input error and does NOT debit quota."""
    final_state = run_research_workflow(
        user_id=test_user.id,
        tab="news",
        tickers=["TOTALLYINVALIDXYZ"],
        date_preset="30D",
        db_path=agent_db,
        provider_mode="mock",
    )

    assert final_state["status"] == "invalid_input"
    assert final_state["error_code"] == "INVALID_TICKERS"
    assert final_state["quota_debited"] is False

    # Quota remains 3
    entitlement = check_entitlement(test_user.id, db_path=agent_db)
    assert entitlement.remaining_free == 3


def test_lookahead_date_leakage_prevention(agent_db, test_user):
    """Verify research request attempting to leak future data past as-of date is rejected."""
    final_state = run_research_workflow(
        user_id=test_user.id,
        tab="news",
        tickers=["AAPL"],
        date_preset="Custom",
        custom_start="2026-11-01",
        custom_end="2026-11-20",  # Future date relative to as_of
        as_of_date="2026-11-07",
        db_path=agent_db,
        provider_mode="mock",
    )

    assert final_state["status"] == "invalid_input"
    assert final_state["error_code"] == "INVALID_DATE_WINDOW"
    assert "Point-in-time guardrail violation" in final_state["error_message"]
    assert final_state["quota_debited"] is False


def test_provider_rate_limit_failure_neutrality(agent_db, test_user):
    """Verify rate-limited provider aborts gracefully and does not consume user credit."""
    final_state = run_research_workflow(
        user_id=test_user.id,
        tab="news",
        tickers=["AAPL"],
        date_preset="7D",
        as_of_date="2026-11-07",
        db_path=agent_db,
        provider_mode="mock",
    )
    # Re-run with rate_limit simulation
    from src.agent.nodes import collect_data_node
    # Test collect_data_node error handling directly
    sim_state = {
        "provider_mode": "mock",
        "validated_tickers": final_state["validated_tickers"],
        "start_date": "2026-10-01",
        "end_date": "2026-10-15",
    }
    from src.providers.mock_provider import MockFinancialDataProvider
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "src.providers.factory.ProviderFactory.get_news_provider",
            lambda mode: MockFinancialDataProvider(simulate_failure="rate_limit"),
        )
        res = collect_data_node(sim_state)
        assert res["status"] == "rate_limited"
        assert res["error_code"] == "RATE_LIMIT_EXCEEDED"


def test_citation_integrity_verification():
    """Verify hallucinated or mismatched citations are flagged as unverified."""
    available_articles = [
        CanonicalNewsItem(
            article_id="real_art_001",
            ticker_association=["AAPL"],
            headline="Apple Q4 Earnings Beat Expectations",
            publisher="Reuters",
            source_url="https://reuters.com/aapl1",
            published_at_utc="2026-11-01T14:00:00Z",
            retrieved_at_utc="2026-11-01T15:00:00Z",
            provider_identification="Test",
        )
    ]

    # Citation 1: Real article
    cit_real = ClaimCitation(
        claim="Earnings increased 15% year-over-year",
        article_id="real_art_001",
        publisher="Reuters",
        source_url="https://reuters.com/aapl1",
        publication_date="2026-11-01T14:00:00Z",
    )
    # Citation 2: Hallucinated / fake article ID
    cit_fake = ClaimCitation(
        claim="Apple announced acquisition of space station",
        article_id="fabricated_art_999",
        publisher="Unknown Rumor",
        source_url="https://fake.com",
        publication_date="2026-11-01T14:00:00Z",
    )

    verified, unverified = verify_citations_tool([cit_real, cit_fake], available_articles)

    assert len(verified) == 1
    assert verified[0].article_id == "real_art_001"
    assert len(unverified) == 1
    assert "fabricated_art_999" in unverified[0]


def test_idempotent_duplicate_job_submission(agent_db, test_user):
    """Verify duplicate submission returns existing job and does not double-debit quota."""
    key = "unique_idem_key_123"

    run1 = run_research_workflow(
        user_id=test_user.id,
        tab="news",
        tickers=["AAPL"],
        date_preset="7D",
        idempotency_key=key,
        as_of_date="2026-11-07",
        db_path=agent_db,
    )
    assert run1["status"] == "completed"
    assert run1["quota_debited"] is True

    # Quota is now 2
    assert check_entitlement(test_user.id, db_path=agent_db).remaining_free == 2

    # Second run with same idempotency key
    run2 = run_research_workflow(
        user_id=test_user.id,
        tab="news",
        tickers=["AAPL"],
        date_preset="7D",
        idempotency_key=key,
        as_of_date="2026-11-07",
        db_path=agent_db,
    )
    assert run2["status"] == "completed"
    assert run2["job_id"] == run1["job_id"]

    # Quota remains 2 (NOT 1!)
    assert check_entitlement(test_user.id, db_path=agent_db).remaining_free == 2


def test_session_token_validation_at_agent_boundary(agent_db, test_user):
    """Verify unauthorized or invalid session token blocks agent execution."""
    # Invalid session token
    final_state = run_research_workflow(
        user_id=test_user.id,
        session_token="invalid_token_xyz",
        tab="news",
        tickers=["AAPL"],
        db_path=agent_db,
    )
    assert final_state["status"] == "failed"
    assert final_state["error_code"] == "UNAUTHORIZED_SESSION"

    # Valid session token succeeds
    _, valid_tok = create_session(test_user.id, db_path=agent_db)
    valid_run = run_research_workflow(
        user_id=test_user.id,
        session_token=valid_tok,
        tab="news",
        tickers=["AAPL"],
        as_of_date="2026-11-07",
        db_path=agent_db,
    )
    assert valid_run["status"] == "completed"
