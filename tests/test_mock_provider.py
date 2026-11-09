"""Unit tests for the deterministic mock provider and simulated error states."""
from datetime import date
import pytest
from src.providers.base import (
    AuthenticationError,
    CoverageLimitation,
    NetworkTimeoutError,
    RateLimitExceeded,
    TickerNotFoundError,
)
from src.providers.mock_provider import MockFinancialDataProvider


def test_mock_ticker_validation():
    """Verify ticker lookup for supported and unsupported symbols."""
    provider = MockFinancialDataProvider()

    valid_aapl = provider.validate_ticker("aapl")
    assert valid_aapl.symbol == "AAPL"
    assert valid_aapl.is_valid is True
    assert valid_aapl.name == "Apple Inc."

    valid_etf = provider.validate_ticker("SPY")
    assert valid_etf.symbol == "SPY"
    assert valid_etf.asset_type == "etf"
    assert valid_etf.is_valid is True

    invalid_sym = provider.validate_ticker("XYZINVALID123")
    assert invalid_sym.symbol == "XYZINVALID123"
    assert invalid_sym.is_valid is False


def test_mock_ticker_search():
    """Verify search returns matching known tickers."""
    provider = MockFinancialDataProvider()
    matches = provider.search_tickers("micro")
    assert any(m.symbol == "MSFT" for m in matches)


def test_mock_historical_prices():
    """Verify price bars generation, weekend exclusion, and OHLC integrity."""
    provider = MockFinancialDataProvider()
    bars = provider.fetch_historical_prices("AAPL", start_date="2026-10-01", end_date="2026-10-14")

    assert len(bars) > 0
    for bar in bars:
        assert bar.ticker == "AAPL"
        # High must be >= max(open, close), low must be <= min(open, close)
        assert bar.high >= max(bar.open, bar.close)
        assert bar.low <= min(bar.open, bar.close)
        assert bar.volume > 0
        # Check trading day: no Saturdays (weekday 5) or Sundays (weekday 6)
        d = date.fromisoformat(bar.trading_date)
        assert d.weekday() < 5


def test_mock_news_retrieval_single_and_multi_ticker():
    """Verify multi-ticker news retrieval within date window."""
    provider = MockFinancialDataProvider()
    news = provider.fetch_news(["AAPL", "MSFT"], start_date="2026-10-01", end_date="2026-10-31")

    assert len(news) > 0
    # Must contain articles for both AAPL and MSFT
    tickers_found = {t for item in news for t in item.ticker_association}
    assert "AAPL" in tickers_found
    assert "MSFT" in tickers_found

    for item in news:
        assert item.headline
        assert item.source_url
        assert item.published_at_utc.startswith("2026-10")


def test_mock_date_boundary_rejection():
    """Verify start_date > end_date raises ValueError."""
    provider = MockFinancialDataProvider()
    with pytest.raises(ValueError, match="cannot be after end_date"):
        provider.fetch_news(["AAPL"], start_date="2026-11-01", end_date="2026-10-01")

    with pytest.raises(ValueError, match="cannot be after end_date"):
        provider.fetch_historical_prices("AAPL", start_date="2026-11-01", end_date="2026-10-01")


def test_mock_unknown_ticker_price_error():
    """Verify requesting prices for unknown ticker raises TickerNotFoundError."""
    provider = MockFinancialDataProvider()
    with pytest.raises(TickerNotFoundError):
        provider.fetch_historical_prices("NONEXISTENT", start_date="2026-10-01", end_date="2026-10-15")


def test_mock_simulated_failures():
    """Verify simulated failure modes for resilience testing."""
    # 1. Rate limit
    p_rate = MockFinancialDataProvider(simulate_failure="rate_limit")
    with pytest.raises(RateLimitExceeded):
        p_rate.fetch_news(["AAPL"], "2026-10-01", "2026-10-15")

    # 2. Timeout
    p_timeout = MockFinancialDataProvider(simulate_failure="timeout")
    with pytest.raises(NetworkTimeoutError):
        p_timeout.fetch_historical_prices("AAPL", "2026-10-01", "2026-10-15")

    # 3. Auth error
    p_auth = MockFinancialDataProvider(simulate_failure="auth_error")
    with pytest.raises(AuthenticationError):
        p_auth.validate_ticker("AAPL")

    # 4. Coverage limit
    p_cov = MockFinancialDataProvider(simulate_failure="coverage_limit")
    with pytest.raises(CoverageLimitation):
        p_cov.fetch_news(["AAPL"], "2026-10-01", "2026-10-15")

    # 5. Empty news
    p_empty = MockFinancialDataProvider(simulate_failure="empty_news")
    assert p_empty.fetch_news(["AAPL"], "2026-10-01", "2026-10-15") == []

