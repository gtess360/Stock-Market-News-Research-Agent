"""Unit tests for canonical financial data models and validation contracts."""
import pytest
from src.models.financial import CanonicalNewsItem, CanonicalPriceBar, TickerInfo


def test_canonical_price_bar_valid():
    """Verify valid OHLCV price bar creation and ticker normalization."""
    bar = CanonicalPriceBar(
        ticker="  aapl  ",
        trading_date="2026-11-05",
        open=220.0,
        high=225.5,
        low=219.0,
        close=224.0,
        adjusted_close=223.5,
        volume=45000000.0,
        data_provider="TestProvider",
        retrieved_at_utc="2026-11-05T21:00:00+00:00",
    )
    assert bar.ticker == "AAPL"
    assert bar.symbol == "AAPL"
    assert bar.high == 225.5
    assert bar.adjusted_close == 223.5


def test_canonical_price_bar_invalid_high_low():
    """Verify high price cannot be less than low price."""
    with pytest.raises(ValueError, match="High price .* cannot be less than low price"):
        CanonicalPriceBar(
            ticker="MSFT",
            trading_date="2026-11-05",
            open=400.0,
            high=390.0,  # Invalid: high < low
            low=395.0,
            close=392.0,
            volume=1000000.0,
            data_provider="TestProvider",
            retrieved_at_utc="2026-11-05T21:00:00+00:00",
        )


def test_canonical_news_item_valid():
    """Verify canonical news item normalization and aliases."""
    item = CanonicalNewsItem(
        article_id="art_123",
        ticker_association=["msft", " msft ", "nvda "],
        headline="Tech Giants Announce Strategic Collaboration",
        publisher="Reuters",
        source_url="https://reuters.example.com/art_123",
        published_at_utc="2026-11-05T14:30:00Z",
        retrieved_at_utc="2026-11-05T15:00:00Z",
        summary_or_description="Executive summary of the partnership.",
        provider_identification="TestNewsProvider",
    )
    assert item.ticker_association == ["MSFT", "NVDA"]
    assert item.ticker_symbols == ["MSFT", "NVDA"]
    assert item.summary_if_licensed == "Executive summary of the partnership."
    assert item.is_duplicate is False


def test_canonical_news_item_invalid_timestamp():
    """Verify invalid ISO timestamp triggers validation error."""
    with pytest.raises(ValueError, match="Invalid ISO 8601 timestamp"):
        CanonicalNewsItem(
            article_id="art_bad_ts",
            ticker_association=["AAPL"],
            headline="Invalid Date Test",
            publisher="Bloomberg",
            source_url="https://example.com",
            published_at_utc="not-a-valid-date",
            retrieved_at_utc="2026-11-05T15:00:00Z",
            provider_identification="Test",
        )


def test_ticker_info_contract():
    """Verify ticker info structure."""
    t = TickerInfo(symbol="NVDA", name="NVIDIA Corporation", asset_type="equity", exchange="NASDAQ")
    assert t.symbol == "NVDA"
    assert t.is_valid is True

