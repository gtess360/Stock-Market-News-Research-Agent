"""Provider factory and registry for instantiating financial data adapters."""
import os
from typing import Optional
from src.providers.base import BaseMarketDataProvider, BaseNewsProvider, BaseTickerProvider
from src.providers.live_adapters import AlphaVantageAdapter, FinnhubAdapter
from src.providers.mock_provider import MockFinancialDataProvider


class ProviderFactory:
    """Factory creating configured data provider instances based on environment or explicit arguments."""

    @staticmethod
    def get_news_provider(
        provider_name: Optional[str] = None,
        simulate_failure: Optional[str] = None,
    ) -> BaseNewsProvider:
        mode = (provider_name or os.getenv("FINANCIAL_DATA_MODE") or os.getenv("NEWS_PROVIDER") or "mock").lower()

        if mode in ("finnhub", "live", "composite", "auto"):
            return FinnhubAdapter()
        elif mode in ("alphavantage", "alpha_vantage"):
            return AlphaVantageAdapter()
        elif mode == "mock":
            return MockFinancialDataProvider(simulate_failure=simulate_failure)
        else:
            raise ValueError(f"Unsupported news provider: '{mode}'. Supported: 'mock', 'finnhub', 'alphavantage', 'live'.")

    @staticmethod
    def get_market_data_provider(
        provider_name: Optional[str] = None,
        simulate_failure: Optional[str] = None,
    ) -> BaseMarketDataProvider:
        mode = (provider_name or os.getenv("FINANCIAL_DATA_MODE") or os.getenv("MARKET_DATA_PROVIDER") or "mock").lower()

        if mode in ("alphavantage", "alpha_vantage", "live", "composite", "auto"):
            return AlphaVantageAdapter()
        elif mode == "finnhub":
            return FinnhubAdapter()
        elif mode == "mock":
            return MockFinancialDataProvider(simulate_failure=simulate_failure)
        else:
            raise ValueError(f"Unsupported market data provider: '{mode}'. Supported: 'mock', 'finnhub', 'alphavantage', 'live'.")

    @staticmethod
    def get_ticker_provider(
        provider_name: Optional[str] = None,
        simulate_failure: Optional[str] = None,
    ) -> BaseTickerProvider:
        mode = (provider_name or os.getenv("FINANCIAL_DATA_MODE") or os.getenv("TICKER_PROVIDER") or "mock").lower()

        if mode in ("finnhub", "live", "composite", "auto"):
            return FinnhubAdapter()
        elif mode == "mock":
            return MockFinancialDataProvider(simulate_failure=simulate_failure)
        else:
            return MockFinancialDataProvider(simulate_failure=simulate_failure)

