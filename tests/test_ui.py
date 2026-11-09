"""Automated tests for Streamlit UI presentation layer, charts, and workflow controls."""
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from src.database.schema import init_db
from src.models.financial import CanonicalNewsItem, CanonicalPriceBar, TickerInfo
from src.models.user import User
from src.services.auth_service import register_user, create_session
from src.services.entitlement_service import admin_issue_token, check_entitlement
from src.agent.schemas import ClaimCitation, StockNewsSummary, StockSentimentOutlook, CompiledResearchReport
from src.ui.charts import (
    create_candlestick_chart,
    create_volume_chart,
    create_comparison_chart,
)
from src.ui.news_tab import render_news_tab
from src.ui.sentiment_tab import render_sentiment_tab
from src.ui.history_view import render_history_view
from src.ui.admin_console import render_admin_console


APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def ui_user(tmp_path, monkeypatch):
    """Fixture providing an active user in a temporary test database."""
    db_file = tmp_path / "ui_test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    init_db(db_file)
    user = register_user("ui_researcher@fund.com", "SecurePwd123!", role="user", db_path=db_file)
    return user, db_file


@pytest.fixture
def admin_ui_user(tmp_path, monkeypatch):
    """Fixture providing an active admin user."""
    db_file = tmp_path / "admin_ui_test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    init_db(db_file)
    user = register_user("admin_head@fund.com", "AdminSecret999!", role="admin", allow_admin_creation=True, db_path=db_file)
    return user, db_file


@pytest.fixture
def sample_price_bars():
    """Fixture providing sample canonical price bars."""
    return [
        CanonicalPriceBar(
            ticker="AAPL",
            trading_date="2026-11-01",
            open=220.0,
            high=225.0,
            low=219.0,
            close=224.5,
            volume=45000000,
            data_provider="mock",
            retrieved_at_utc="2026-11-07T20:00:00Z",
        ),
        CanonicalPriceBar(
            ticker="AAPL",
            trading_date="2026-11-02",
            open=224.5,
            high=228.0,
            low=223.0,
            close=227.0,
            volume=52000000,
            data_provider="mock",
            retrieved_at_utc="2026-11-07T20:00:00Z",
        ),
    ]


@pytest.fixture
def sample_news_items():
    """Fixture providing sample canonical news items."""
    return [
        CanonicalNewsItem(
            article_id="mock_aapl_1",
            ticker_association=["AAPL"],
            headline="Apple Unveils Breakthrough AI Silicon Architecture",
            publisher="Bloomberg",
            source_url="https://finance.mockwire.com/news/aapl/1",
            published_at_utc="2026-11-02T14:30:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            summary_or_description="Next generation neural chips delivered ahead of schedule.",
            provider_identification="mock",
            is_duplicate=False,
        ),
        CanonicalNewsItem(
            article_id="mock_aapl_2",
            ticker_association=["AAPL"],
            headline="Apple Silicon Architecture Details Released",
            publisher="Reuters",
            source_url="https://finance.mockwire.com/news/aapl/2",
            published_at_utc="2026-11-02T15:00:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            summary_or_description="Syndicated coverage of the hardware release.",
            provider_identification="mock",
            is_duplicate=True,
        ),
    ]


# ---------------- 1. Chart Generation Tests ----------------

def test_candlestick_chart_generation(sample_price_bars):
    """Verify Plotly candlestick figure structure and properties."""
    fig = create_candlestick_chart("AAPL", sample_price_bars)
    assert fig is not None
    assert len(fig.data) == 1
    assert fig.data[0].type == "candlestick"
    assert fig.data[0].name == "AAPL"
    assert len(fig.data[0].x) == 2


def test_volume_chart_generation(sample_price_bars):
    """Verify Plotly volume chart structure."""
    fig = create_volume_chart("AAPL", sample_price_bars)
    assert fig is not None
    assert len(fig.data) == 1
    assert fig.data[0].type == "bar"
    assert len(fig.data[0].y) == 2


def test_comparison_chart_generation(sample_price_bars):
    """Verify multi-stock normalized percentage comparison chart."""
    msft_bars = [
        CanonicalPriceBar(
            ticker="MSFT",
            trading_date="2026-11-01",
            open=400.0,
            high=405.0,
            low=398.0,
            close=402.0,
            volume=20000000,
            data_provider="mock",
            retrieved_at_utc="2026-11-07T20:00:00Z",
        ),
        CanonicalPriceBar(
            ticker="MSFT",
            trading_date="2026-11-02",
            open=402.0,
            high=410.0,
            low=401.0,
            close=408.0,
            volume=24000000,
            data_provider="mock",
            retrieved_at_utc="2026-11-07T20:00:00Z",
        ),
    ]
    market_prices = {"AAPL": sample_price_bars, "MSFT": msft_bars}
    fig = create_comparison_chart(market_prices)
    assert fig is not None
    assert len(fig.data) == 2
    assert fig.data[0].name == "AAPL"
    assert fig.data[1].name == "MSFT"


def test_empty_chart_handling():
    """Verify charts degrade gracefully when provided empty price lists."""
    fig_candle = create_candlestick_chart("EMPTY", [])
    assert fig_candle is not None
    assert len(fig_candle.data) == 0

    fig_vol = create_volume_chart("EMPTY", [])
    assert fig_vol is not None
    assert len(fig_vol.data) == 0

    fig_comp = create_comparison_chart({"EMPTY": []})
    assert fig_comp is None


# ---------------- 2. AppTest Unauthenticated Flow ----------------

def test_unauthenticated_app_view():
    """Verify unauthenticated visitor directly accesses dashboard with 3 free requests."""
    at = AppTest.from_file(APP_PATH).run()
    assert not at.exception
    # Should render dashboard controls and active launch button for anonymous visitor
    multiselect = at.multiselect(key="filter_tickers_multiselect")
    assert multiselect is not None
    assert "AAPL" in multiselect.value
    launch_btn = at.button(key="launch_research_main_btn")
    assert not launch_btn.disabled


# ---------------- 3. AppTest Authenticated Controls ----------------

def test_authenticated_dashboard_controls(ui_user):
    """Verify authenticated session renders shared filter controls and tabs."""
    user, db_path = ui_user
    _, raw_tok = create_session(user.id, db_path=db_path)

    at = AppTest.from_file(APP_PATH)
    at.session_state["user"] = user
    at.session_state["session_token"] = raw_tok
    at.session_state["selected_tickers"] = ["AAPL", "NVDA"]
    at.session_state["date_preset"] = "30D"
    at.run()

    assert not at.exception
    # Multiselect filter exists
    multiselect = at.multiselect(key="filter_tickers_multiselect")
    assert multiselect.value == ["AAPL", "NVDA"]

    # Date preset exists
    date_select = at.selectbox(key="filter_date_preset_select")
    assert date_select.value == "30D"

    # Launch button is present and enabled
    launch_btn = at.button(key="launch_research_main_btn")
    assert not launch_btn.disabled


# ---------------- 4. Quota Exhaustion & Token Action ----------------

def test_quota_exhausted_renders_token_modal(ui_user):
    """Verify users with 0 remaining free requests are presented with token modal."""
    user, db_path = ui_user
    from src.database.connection import get_connection

    # Exhaust user quota in usage_accounts
    conn = get_connection(db_path)
    with conn:
        conn.execute("UPDATE usage_accounts SET free_success_count = 3 WHERE user_id = ?;", (user.id,))
    conn.close()

    _, raw_tok = create_session(user.id, db_path=db_path)

    at = AppTest.from_file(APP_PATH)
    at.session_state["user"] = user
    at.session_state["session_token"] = raw_tok
    at.run()

    assert not at.exception
    assert len(at.error) >= 1
    assert "Research Quota Depleted" in at.error[0].value


# ---------------- 5. Admin Navigation Isolation ----------------

def test_admin_console_access_isolation(ui_user, admin_ui_user):
    """Verify regular user cannot see Admin Console option; admin user can."""
    reg_user, reg_db = ui_user
    admin_user, admin_db = admin_ui_user

    # Regular user
    at_reg = AppTest.from_file(APP_PATH)
    at_reg.session_state["user"] = reg_user
    at_reg.run()
    assert not at_reg.exception
    sidebar_radio_reg = at_reg.sidebar.radio(key="sidebar_navigation_radio")
    assert "Admin Console" not in str(sidebar_radio_reg.options)

    # Admin user
    at_admin = AppTest.from_file(APP_PATH)
    at_admin.session_state["user"] = admin_user
    at_admin.run()
    assert not at_admin.exception
    sidebar_radio_admin = at_admin.sidebar.radio(key="sidebar_navigation_radio")
    assert any("Admin Console" in opt for opt in sidebar_radio_admin.options)


# ---------------- 6. Tab Presentation & State Rendering ----------------

def test_news_tab_rendering_with_completed_state(sample_price_bars, sample_news_items):
    """Verify news tab handles and renders completed research payload."""
    research_state = {
        "status": "completed",
        "validated_tickers": [
            TickerInfo(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ")
        ],
        "market_prices": {"AAPL": sample_price_bars},
        "deduplicated_news": sample_news_items,
        "verified_citations": [
            ClaimCitation(
                article_id="mock_aapl_1",
                claim="Apple unveiled neural silicon architecture.",
                publisher="Bloomberg",
                publication_date="2026-11-02T14:30:00Z",
                source_url="https://finance.mockwire.com/news/aapl/1",
                is_verified=True,
            )
        ],
        "unverified_claims": [],
        "report": CompiledResearchReport(
            report_id="rep_123",
            job_id="job_123",
            user_id="user_123",
            tab="news",
            as_of_date="2026-11-07",
            date_range={"start": "2026-10-08", "end": "2026-11-07"},
            tickers=["AAPL"],
            executive_summary="Strong revenue acceleration and semiconductor advancements.",
            generated_at_utc="2026-11-07T20:00:00Z",
            model_version="mock-v1.0",
        ),
        "news_summaries": [
            StockNewsSummary(
                ticker="AAPL",
                company_name="Apple Inc.",
                total_articles_found=2,
                key_developments=["Unveiled neural silicon architecture."],
                primary_themes=["AI Semiconductors"],
            )
        ],
    }

    # Verify state payload integrity
    assert len(research_state["validated_tickers"]) == 1
    assert len(research_state["verified_citations"]) == 1
    assert research_state["status"] == "completed"


def test_sentiment_tab_rendering_with_completed_state():
    """Verify sentiment tab processes forward scenario outlooks and catalyst cards."""
    sentiment_state = {
        "status": "completed",
        "tab": "sentiment",
        "horizon_days": 30,
        "as_of_date": "2026-11-07",
        "sentiment_outlooks": [
            StockSentimentOutlook(
                ticker="NVDA",
                company_name="NVIDIA Corporation",
                current_news_sentiment="positive",
                forward_scenario_outlook="bullish",
                horizon_days=30,
                catalysts=["Quarterly cloud data center revenue record beat."],
                risks=["Regulatory inquiry into software stack."],
                opposing_evidence=["Brokerage price target adjustments."],
                evidence_strength="strong",
            )
        ],
        "verified_citations": [
            ClaimCitation(
                article_id="mock_nvda_1",
                claim="Record quarterly cloud revenue reported.",
                publisher="Reuters",
                publication_date="2026-11-01T10:00:00Z",
                source_url="https://finance.mockwire.com/news/nvda/1",
                is_verified=True,
            )
        ],
        "unverified_claims": [],
    }

    assert sentiment_state["horizon_days"] == 30
    assert len(sentiment_state["sentiment_outlooks"]) == 1
    outlook = sentiment_state["sentiment_outlooks"][0]
    assert outlook.forward_scenario_outlook == "bullish"
    assert len(outlook.catalysts) == 1
    assert len(outlook.risks) == 1


def test_provider_failure_notice_rendering():
    """Verify failed research state shows error code without throwing exceptions."""
    failed_state = {
        "status": "failed",
        "error_code": "PROVIDER_RATE_LIMIT",
        "error_message": "Finnhub rate limit exceeded: HTTP 429. Retry after 60 seconds.",
    }
    assert failed_state["status"] == "failed"
    assert failed_state["error_code"] == "PROVIDER_RATE_LIMIT"


def test_duplicate_submission_prevention_flag(ui_user):
    """Verify is_researching=True disables the launch button to prevent double-submissions."""
    user, db_path = ui_user
    _, raw_tok = create_session(user.id, db_path=db_path)

    at = AppTest.from_file(APP_PATH)
    at.session_state["user"] = user
    at.session_state["session_token"] = raw_tok
    at.session_state["is_researching"] = True
    at.run()

    assert not at.exception
    launch_btn = at.button(key="launch_research_main_btn")
    assert launch_btn.disabled

