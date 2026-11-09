"""Automated tests for Phase 3.7: Research History, Persistence, and Multi-Format Export."""
import json
import sqlite3
import pytest
from src.database.connection import get_connection
from src.database.schema import init_db
from src.services.history_service import query_user_research_history, get_user_job_detail
from src.services.export_service import (
    export_to_markdown,
    export_to_json,
    export_to_csv,
    export_to_pdf,
)


@pytest.fixture
def test_db(tmp_path):
    """Create and migrate an isolated temporary SQLite database populated with multi-user jobs."""
    db_file = tmp_path / "test_history.db"
    init_db(db_file)

    conn = get_connection(db_file)
    try:
        # Create User A and User B
        conn.execute(
            """
            INSERT INTO users (id, auth_provider_subject, role, created_at, status)
            VALUES 
                ('user_a', 'usera@example.com', 'user', '2026-11-01 00:00:00', 'active'),
                ('user_b', 'userb@example.com', 'user', '2026-11-01 00:00:00', 'active');
            """
        )

        # Create Research Jobs for User A
        conn.execute(
            """
            INSERT INTO research_jobs (
                id, user_id, idempotency_key, tab, ticker_list_json,
                start_at, end_at, horizon_days, status, credit_debited, created_at, completed_at
            ) VALUES 
                ('job_a1', 'user_a', 'idem_a1', 'news', '["AAPL", "MSFT"]', '2026-10-01', '2026-10-31', NULL, 'completed', 1, '2026-11-01 10:00:00', '2026-11-01 10:02:00'),
                ('job_a2', 'user_a', 'idem_a2', 'sentiment', '["AAPL", "NVDA"]', '2026-10-15', '2026-11-05', 30, 'completed', 1, '2026-11-02 11:00:00', '2026-11-02 11:03:00'),
                ('job_a3', 'user_a', 'idem_a3', 'news', '["TSLA"]', '2026-10-20', '2026-11-06', NULL, 'failed', 0, '2026-11-03 09:00:00', '2026-11-03 09:01:00');
            """
        )

        # Create Research Job for User B
        conn.execute(
            """
            INSERT INTO research_jobs (
                id, user_id, idempotency_key, tab, ticker_list_json,
                start_at, end_at, horizon_days, status, credit_debited, created_at, completed_at
            ) VALUES 
                ('job_b1', 'user_b', 'idem_b1', 'sentiment', '["AMZN"]', '2026-10-01', '2026-10-31', 7, 'completed', 1, '2026-11-04 12:00:00', '2026-11-04 12:02:00');
            """
        )

        # Insert Reports
        report_a1_json = {
            "executive_summary": "Apple and Microsoft showed resilient cloud demand and stable iPhone shipments in Q3.",
            "stock_news_summaries": [
                {
                    "ticker": "AAPL",
                    "key_developments": ["iPhone 16 sales exceeded Wall Street consensus by 4%."],
                    "citations": [{"claim": "Q3 beat", "article_id": "art_1", "source_url": "https://reuters.com/aapl"}]
                }
            ],
            "all_citations": [
                {
                    "article_id": "art_1",
                    "ticker": "AAPL",
                    "publisher": "Reuters",
                    "publication_date": "2026-10-28T14:00:00Z",
                    "claim": "iPhone 16 sales exceeded Wall Street consensus by 4%",
                    "source_url": "https://reuters.com/aapl"
                }
            ]
        }

        report_a2_json = {
            "executive_summary": "Nvidia datacenter GPU orders remain elevated while Apple supply chain indicators are stable.",
            "stock_sentiment_outlooks": [
                {
                    "ticker": "NVDA",
                    "current_news_sentiment": "bullish",
                    "forward_scenario_outlook": "bullish",
                    "horizon_days": 30,
                    "evidence_strength": "high",
                    "catalysts": ["Hyperscaler AI CAPEX raised by 18%"],
                    "risks": ["Potential regulatory export curbs"],
                    "opposing_evidence": ["Lead times shortening for H200"]
                }
            ],
            "all_citations": [
                {
                    "article_id": "art_2",
                    "ticker": "NVDA",
                    "publisher": "Bloomberg",
                    "publication_date": "2026-11-01T09:30:00Z",
                    "claim": "Hyperscaler AI capex raised by 18%",
                    "source_url": "https://bloomberg.com/nvda"
                }
            ]
        }

        conn.execute(
            """
            INSERT INTO research_reports (id, job_id, markdown, report_json, model_version, prompt_version, generated_at)
            VALUES 
                ('rep_a1', 'job_a1', '# Apple & Microsoft Research\nresilient cloud demand...', ?, 'gpt-4o-mini', '1.0.0', '2026-11-01 10:02:00'),
                ('rep_a2', 'job_a2', '# NVDA Sentiment Report\nAI demand elevated...', ?, 'gpt-4o-mini', '1.0.0', '2026-11-02 11:03:00');
            """,
            (json.dumps(report_a1_json), json.dumps(report_a2_json))
        )

        # Insert Source Records for job_a1
        conn.execute(
            """
            INSERT INTO source_records (
                id, job_id, ticker, source_url, publisher, published_at, retrieved_at, evidence_type, normalized_metadata_json
            ) VALUES 
                ('src_1', 'job_a1', 'AAPL', 'https://reuters.com/aapl', 'Reuters', '2026-10-28 14:00:00', '2026-11-01 10:01:00', 'news', '{"headline": "Apple Q3 Beats Estimates", "is_duplicate": false}');
            """
        )

        conn.commit()
    finally:
        conn.close()

    return db_file


# ==============================================================================
# 1. User Ownership Isolation Tests
# ==============================================================================

def test_user_ownership_isolation_queries(test_db):
    """Ensure User A cannot view User B's jobs and vice versa."""
    # User A queries
    jobs_a, count_a = query_user_research_history(user_id="user_a", db_path=test_db)
    assert count_a == 3
    user_a_ids = {j["id"] for j in jobs_a}
    assert "job_b1" not in user_a_ids
    assert "job_a1" in user_a_ids
    assert "job_a2" in user_a_ids
    assert "job_a3" in user_a_ids

    # User B queries
    jobs_b, count_b = query_user_research_history(user_id="user_b", db_path=test_db)
    assert count_b == 1
    assert jobs_b[0]["id"] == "job_b1"
    assert "user_a" not in {j["user_id"] for j in jobs_b}


def test_user_ownership_isolation_detail(test_db):
    """Ensure User B cannot retrieve User A's job details, returning None."""
    detail_unauth = get_user_job_detail(user_id="user_b", job_id="job_a1", db_path=test_db)
    assert detail_unauth is None

    detail_auth = get_user_job_detail(user_id="user_a", job_id="job_a1", db_path=test_db)
    assert detail_auth is not None
    assert detail_auth["id"] == "job_a1"
    assert detail_auth["user_id"] == "user_a"
    assert len(detail_auth["sources"]) == 1
    assert detail_auth["sources"][0]["publisher"] == "Reuters"


def test_empty_user_id_returns_empty(test_db):
    """Empty or invalid user ID returns empty records."""
    jobs, total = query_user_research_history(user_id="", db_path=test_db)
    assert jobs == []
    assert total == 0


# ==============================================================================
# 2. Filtering & Search Tests
# ==============================================================================

def test_filter_by_ticker(test_db):
    """Filter history by specific ticker symbol."""
    # AAPL is in job_a1 and job_a2
    jobs, total = query_user_research_history(user_id="user_a", ticker="AAPL", db_path=test_db)
    assert total == 2
    for j in jobs:
        assert "AAPL" in j["tickers"]

    # TSLA is only in job_a3
    jobs_tsla, total_tsla = query_user_research_history(user_id="user_a", ticker="TSLA", db_path=test_db)
    assert total_tsla == 1
    assert jobs_tsla[0]["id"] == "job_a3"


def test_filter_by_tab_and_status(test_db):
    """Filter by research mode (news vs sentiment) and execution status."""
    # Filter sentiment jobs
    jobs_sent, total_sent = query_user_research_history(user_id="user_a", tab_type="sentiment", db_path=test_db)
    assert total_sent == 1
    assert jobs_sent[0]["id"] == "job_a2"

    # Filter news jobs
    jobs_news, total_news = query_user_research_history(user_id="user_a", tab_type="news", db_path=test_db)
    assert total_news == 2

    # Filter failed jobs
    jobs_failed, total_failed = query_user_research_history(user_id="user_a", status_filter="failed", db_path=test_db)
    assert total_failed == 1
    assert jobs_failed[0]["id"] == "job_a3"


def test_keyword_search(test_db):
    """Search by keyword across executive summaries, report JSON, and markdown."""
    # Search for 'cloud' (present in job_a1)
    jobs, total = query_user_research_history(user_id="user_a", keyword="cloud", db_path=test_db)
    assert total == 1
    assert jobs[0]["id"] == "job_a1"

    # Search for 'datacenter' (present in job_a2 report_json)
    jobs_dc, total_dc = query_user_research_history(user_id="user_a", keyword="datacenter", db_path=test_db)
    assert total_dc == 1
    assert jobs_dc[0]["id"] == "job_a2"

    # Search for non-existent keyword
    jobs_none, total_none = query_user_research_history(user_id="user_a", keyword="nonexistent_xyz", db_path=test_db)
    assert total_none == 0
    assert jobs_none == []


def test_pagination(test_db):
    """Ensure pagination properly divides records and returns correct pages."""
    # Page size 2 for 3 records -> Page 1 has 2 items, Page 2 has 1 item
    page1, total1 = query_user_research_history(user_id="user_a", page=1, page_size=2, db_path=test_db)
    assert total1 == 3
    assert len(page1) == 2

    page2, total2 = query_user_research_history(user_id="user_a", page=2, page_size=2, db_path=test_db)
    assert total2 == 3
    assert len(page2) == 1
    assert page1[0]["id"] != page2[0]["id"]


# ==============================================================================
# 3. Multi-Format Export Tests
# ==============================================================================

def test_export_to_markdown(test_db):
    """Export report to Markdown with metadata, summary, citations, and disclaimer."""
    detail = get_user_job_detail(user_id="user_a", job_id="job_a1", db_path=test_db)
    md = export_to_markdown(detail)

    assert isinstance(md, str)
    assert len(md) > 50
    # Custom markdown was present in DB
    assert "Apple & Microsoft Research" in md or "resilient cloud demand" in md

    # Test fallback markdown generation when markdown is empty
    detail_empty_md = dict(detail)
    detail_empty_md["markdown"] = ""
    fallback_md = export_to_markdown(detail_empty_md)
    assert "Stock Market Research Report" in fallback_md
    assert "Executive Summary" in fallback_md
    assert "Verified Source Citations" in fallback_md
    assert "Methodology & Regulatory Disclaimer" in fallback_md


def test_export_to_json(test_db):
    """Export report to structured JSON containing verified payload schema."""
    detail = get_user_job_detail(user_id="user_a", job_id="job_a1", db_path=test_db)
    json_str = export_to_json(detail)

    payload = json.loads(json_str)
    assert payload["job_id"] == "job_a1"
    assert payload["user_id"] == "user_a"
    assert payload["tickers"] == ["AAPL", "MSFT"]
    assert "report" in payload
    assert "executive_summary" in payload["report"]
    assert "source_records" in payload
    assert len(payload["source_records"]) == 1
    assert "disclaimer" in payload


def test_export_to_csv(test_db):
    """Export report to multi-section CSV with executive summary, developments, and citations."""
    detail = get_user_job_detail(user_id="user_a", job_id="job_a1", db_path=test_db)
    csv_str = export_to_csv(detail)

    assert "STOCK MARKET NEWS RESEARCH AGENT" in csv_str
    assert "EXECUTIVE_SUMMARY" in csv_str
    assert "KEY_DEVELOPMENT" in csv_str
    assert "CITATION" in csv_str
    assert "DISCLAIMER" in csv_str
    assert "AAPL" in csv_str
    assert "Reuters" in csv_str


def test_export_to_csv_sentiment(test_db):
    """Export sentiment research report to CSV with catalysts, risks, and outlooks."""
    detail = get_user_job_detail(user_id="user_a", job_id="job_a2", db_path=test_db)
    csv_str = export_to_csv(detail)

    assert "SENTIMENT_OUTLOOK" in csv_str
    assert "CATALYST" in csv_str
    assert "DOWNSIDE_RISK" in csv_str
    assert "OPPOSING_EVIDENCE" in csv_str
    assert "Hyperscaler AI CAPEX" in csv_str


def test_export_to_pdf(test_db):
    """Export report to binary PDF and verify valid PDF structure and headers."""
    detail = get_user_job_detail(user_id="user_a", job_id="job_a2", db_path=test_db)
    pdf_bytes = export_to_pdf(detail)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    # PDF magic byte signature
    assert pdf_bytes.startswith(b"%PDF-")


def test_export_to_pdf_unicode_resilience(test_db):
    """Ensure PDF generation does not crash on non-Latin-1 characters / smart quotes."""
    detail = get_user_job_detail(user_id="user_a", job_id="job_a1", db_path=test_db)
    # Inject unicode quotes and accents into summary
    detail["report_json"]["executive_summary"] = "Apple’s resilience in Tokyo & München was “outstanding” — 100% growth."
    pdf_bytes = export_to_pdf(detail)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
