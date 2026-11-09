"""Unit tests for the financial data caching layer."""
import time
from src.providers.cache import FinancialDataCache


def test_cache_set_and_get():
    """Verify caching and retrieval with parameter hashing."""
    cache = FinancialDataCache()
    params = {"symbol": "AAPL", "start": "2026-10-01", "end": "2026-11-01"}
    data = [{"date": "2026-10-01", "close": 225.0}]

    cache.set("MockProvider", "market_data", params, data, ttl_sec=60)
    retrieved = cache.get("MockProvider", "market_data", params)

    assert retrieved == data
    # Cache miss for different params
    assert cache.get("MockProvider", "market_data", {"symbol": "MSFT"}) is None
    # Cache miss for different category
    assert cache.get("MockProvider", "news", params) is None


def test_cache_ttl_expiration():
    """Verify expired cache entries return None."""
    cache = FinancialDataCache()
    params = {"symbol": "NVDA"}
    cache.set("MockProvider", "news", params, ["item1"], ttl_sec=1)

    assert cache.get("MockProvider", "news", params) == ["item1"]
    time.sleep(1.1)
    assert cache.get("MockProvider", "news", params) is None


def test_cache_clear():
    """Verify clearing cache removes all entries."""
    cache = FinancialDataCache()
    cache.set("P1", "c1", {"k": 1}, "v1")
    cache.set("P2", "c2", {"k": 2}, "v2")
    assert cache.size == 2

    cache.clear()
    assert cache.size == 0

