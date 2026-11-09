"""Unit tests for external API adapters with mocked HTTP responses and factory resolution."""
from unittest.mock import MagicMock, patch
import pytest
import requests
from src.providers.base import AuthenticationError, RateLimitExceeded
from src.providers.factory import ProviderFactory
from src.providers.live_adapters import AlphaVantageAdapter, FinnhubAdapter, request_with_retry


def test_finnhub_missing_api_key(monkeypatch):
    """Verify adapter raises AuthenticationError when API key is missing."""
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    adapter = FinnhubAdapter(api_key=None)
    with pytest.raises(AuthenticationError, match="FINNHUB_API_KEY environment variable is not configured"):
        adapter.fetch_news(["AAPL"], "2026-10-01", "2026-10-15")


@patch("src.providers.live_adapters.requests.get")
def test_finnhub_news_mapping_and_parsing(mock_get):
    """Verify Finnhub news JSON is parsed and normalized into CanonicalNewsItem."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "id": 1001,
            "headline": "Apple Expands Silicon Capabilities",
            "source": "Bloomberg",
            "url": "https://bloomberg.com/news/1001",
            "datetime": 1793500000,
            "summary": "Apple announces next generation M-series processors.",
        }
    ]
    mock_get.return_value = mock_resp

    adapter = FinnhubAdapter(api_key="mock_finnhub_key")
    news = adapter.fetch_news(["AAPL"], "2026-10-01", "2026-10-15")

    assert len(news) == 1
    item = news[0]
    assert item.headline == "Apple Expands Silicon Capabilities"
    assert item.publisher == "Bloomberg"
    assert item.ticker_association == ["AAPL"]
    assert item.provider_identification == "Finnhub"


@patch("src.providers.live_adapters.requests.get")
def test_finnhub_rate_limit_retry_after(mock_get):
    """Verify HTTP 429 response is translated to RateLimitExceeded."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {"Retry-After": "15"}
    mock_get.return_value = mock_resp

    with pytest.raises(RateLimitExceeded) as exc:
        request_with_retry("https://api.example.com", provider="Finnhub", max_retries=1)
    assert exc.value.retry_after_sec == 15


@patch("src.providers.live_adapters.requests.get")
def test_alpha_vantage_daily_prices_parsing(mock_get):
    """Verify Alpha Vantage daily time series JSON is parsed into CanonicalPriceBar."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "Time Series (Daily)": {
            "2026-11-05": {
                "1. open": "220.00",
                "2. high": "225.00",
                "3. low": "219.00",
                "4. close": "224.50",
                "5. volume": "50000000",
            }
        }
    }
    mock_get.return_value = mock_resp

    adapter = AlphaVantageAdapter(api_key="mock_av_key")
    bars = adapter.fetch_historical_prices("AAPL", "2026-11-01", "2026-11-06")

    assert len(bars) == 1
    bar = bars[0]
    assert bar.ticker == "AAPL"
    assert bar.trading_date == "2026-11-05"
    assert bar.close == 224.50
    assert bar.data_provider == "AlphaVantage"


@patch("src.providers.live_adapters.requests.get")
def test_alpha_vantage_rate_limit_note(mock_get):
    """Verify Alpha Vantage 'Note' response is identified as RateLimitExceeded."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute."
    }
    mock_get.return_value = mock_resp

    adapter = AlphaVantageAdapter(api_key="mock_av_key")
    with pytest.raises(RateLimitExceeded):
        adapter.fetch_news(["AAPL"], "2026-10-01", "2026-10-15")


def test_provider_factory():
    """Verify ProviderFactory returns requested mock and live adapter instances."""
    mock_news = ProviderFactory.get_news_provider("mock")
    assert mock_news.__class__.__name__ == "MockFinancialDataProvider"

    fh_market = ProviderFactory.get_market_data_provider("finnhub")
    assert fh_market.__class__.__name__ == "FinnhubAdapter"

    av_news = ProviderFactory.get_news_provider("alphavantage")
    assert av_news.__class__.__name__ == "AlphaVantageAdapter"

    # Test "live" composite resolution
    live_news = ProviderFactory.get_news_provider("live")
    assert live_news.__class__.__name__ == "FinnhubAdapter"

    live_market = ProviderFactory.get_market_data_provider("live")
    assert live_market.__class__.__name__ == "AlphaVantageAdapter"

    live_ticker = ProviderFactory.get_ticker_provider("live")
    assert live_ticker.__class__.__name__ == "FinnhubAdapter"


def test_alpha_vantage_missing_api_key(monkeypatch):
    """Verify adapter raises AuthenticationError when API key is missing."""
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    adapter = AlphaVantageAdapter(api_key=None)
    with pytest.raises(AuthenticationError, match="ALPHA_VANTAGE_API_KEY environment variable is not configured"):
        adapter.fetch_historical_prices("AAPL", "2026-11-01", "2026-11-05")


@patch("src.providers.live_adapters.requests.get")
def test_alpha_vantage_premium_information_limitation(mock_get):
    """Verify Alpha Vantage premium endpoint notice is identified as CoverageLimitation."""
    from src.providers.base import CoverageLimitation
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "Information": "Thank you for using Alpha Vantage! This is a premium endpoint."
    }
    mock_get.return_value = mock_resp

    adapter = AlphaVantageAdapter(api_key="mock_av_key")
    with pytest.raises(CoverageLimitation, match="premium endpoint"):
        adapter.fetch_news(["AAPL"], "2026-10-01", "2026-10-15")


@patch("src.providers.live_adapters.requests.get")
def test_finnhub_candle_quote_fallback(mock_get):
    """Verify Finnhub candle 403 access restriction triggers graceful fallback to /quote."""
    def mock_get_dispatch(url, *args, **kwargs):
        resp = MagicMock()
        if "stock/candle" in url:
            resp.status_code = 403
            resp.text = '{"error":"You don\'t have access to this resource."}'
            return resp
        elif "quote" in url:
            resp.status_code = 200
            resp.json.return_value = {
                "c": 224.50,
                "h": 226.00,
                "l": 223.00,
                "o": 223.50,
                "pc": 222.00,
                "t": 1793500000,
            }
            return resp
        resp.status_code = 404
        return resp

    mock_get.side_effect = mock_get_dispatch

    adapter = FinnhubAdapter(api_key="mock_finnhub_key")
    bars = adapter.fetch_historical_prices("AAPL", "2026-11-01", "2026-11-05")

    assert len(bars) == 1
    assert bars[0].ticker == "AAPL"
    assert bars[0].close == 224.50
    assert bars[0].data_provider == "Finnhub"


@patch("src.providers.live_adapters.requests.get")
def test_finnhub_validate_ticker(mock_get):
    """Verify Finnhub ticker search maps to valid TickerInfo."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": [
            {"description": "APPLE INC", "symbol": "AAPL", "type": "Common Stock"}
        ]
    }
    mock_get.return_value = mock_resp

    adapter = FinnhubAdapter(api_key="mock_finnhub_key")
    tinfo = adapter.validate_ticker("AAPL")

    assert tinfo.is_valid is True
    assert tinfo.name == "APPLE INC"
    assert tinfo.asset_type == "equity"


