"""Deterministic mock financial market data and news provider for testing and development."""
import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional
from src.models.financial import CanonicalNewsItem, CanonicalPriceBar, ProviderCoverageReport, TickerInfo
from src.providers.base import (
    AuthenticationError,
    BaseMarketDataProvider,
    BaseNewsProvider,
    BaseTickerProvider,
    CoverageLimitation,
    NetworkTimeoutError,
    ProviderException,
    RateLimitExceeded,
    TickerNotFoundError,
)
from src.providers.date_filter import is_trading_day

KNOWN_TICKERS: Dict[str, Dict[str, str]] = {
    "AAPL": {"name": "Apple Inc.", "exchange": "NASDAQ", "type": "equity", "base_price": "225.50"},
    "MSFT": {"name": "Microsoft Corporation", "exchange": "NASDAQ", "type": "equity", "base_price": "415.20"},
    "NVDA": {"name": "NVIDIA Corporation", "exchange": "NASDAQ", "type": "equity", "base_price": "135.00"},
    "GOOGL": {"name": "Alphabet Inc.", "exchange": "NASDAQ", "type": "equity", "base_price": "178.40"},
    "AMZN": {"name": "Amazon.com Inc.", "exchange": "NASDAQ", "type": "equity", "base_price": "186.10"},
    "TSLA": {"name": "Tesla, Inc.", "exchange": "NASDAQ", "type": "equity", "base_price": "218.00"},
    "META": {"name": "Meta Platforms, Inc.", "exchange": "NASDAQ", "type": "equity", "base_price": "585.00"},
    "SPY": {"name": "SPDR S&P 500 ETF Trust", "exchange": "NYSE Arca", "type": "etf", "base_price": "570.00"},
    "QQQ": {"name": "Invesco QQQ Trust", "exchange": "NASDAQ", "type": "etf", "base_price": "485.00"},
}

SAMPLE_NEWS_TEMPLATES = [
    ("{ticker} Reports Record Quarterly Cloud & AI Segment Revenue", "Reuters", "Strong execution in enterprise cloud infrastructure drove double-digit margin growth.", 0),
    ("{ticker} Unveils Next-Generation Architecture Ahead of Schedule", "Bloomberg", "Management projects accelerated commercial adoption across international enterprise accounts.", 1),
    ("Wall Street Brokerages Upgrade {ticker} Price Targets Following Earnings Beat", "Wall Street Journal", "Analysts cite resilient consumer demand and improved supply chain efficiency.", 2),
    ("Supply Chain Constraints Moderate Component Deliveries for {ticker}", "CNBC", "Short-term delivery delays could temper sequential gross margin expansion.", 3),
    ("Regulatory Authorities Open Preliminary Inquiry into {ticker} Software Ecosystem", "Financial Times", "Inquiry examines enterprise licensing provisions and third-party developer terms.", 4),
    ("{ticker} Partners with Global Telecoms to Deploy Edge Computing Nodes", "PR Newswire", "Syndicated press release announcing multi-year strategic deployment agreements.", 5),
    # Wire duplicate of template 5
    ("{ticker} Partners with Global Telecoms to Deploy Edge Computing Nodes", "Business Wire", "Syndicated press release announcing multi-year strategic deployment agreements.", 5),
]


class MockFinancialDataProvider(BaseNewsProvider, BaseMarketDataProvider, BaseTickerProvider):
    """Deterministic provider that simulates financial news and market pricing without external network calls."""

    def __init__(self, simulate_failure: Optional[str] = None):
        """
        simulate_failure options:
            None, 'rate_limit', 'timeout', 'auth_error', 'coverage_limit', 'empty_news'
        """
        self.simulate_failure = simulate_failure

    def get_coverage(self) -> ProviderCoverageReport:
        return ProviderCoverageReport(
            provider_name="MockFinancialDataProvider",
            news_supported=True,
            market_data_supported=True,
            historical_news_days_limit=365,
            market_data_delay_minutes=0,
            rate_limit_per_minute=1000,
            commercial_redistribution_allowed=True,
            attribution_notice_required="Mock Financial Data for testing purposes.",
        )

    def validate_ticker(self, symbol: str) -> TickerInfo:
        if self.simulate_failure == "auth_error":
            raise AuthenticationError(provider="MockProvider", message="Simulated invalid credentials.")
        
        clean = symbol.strip().upper()
        if clean in KNOWN_TICKERS:
            meta = KNOWN_TICKERS[clean]
            return TickerInfo(
                symbol=clean,
                name=meta["name"],
                asset_type=meta["type"],  # type: ignore
                exchange=meta["exchange"],
                currency="USD",
                is_valid=True,
            )
        return TickerInfo(
            symbol=clean,
            name="Unknown Asset",
            asset_type="other",
            exchange="UNKNOWN",
            currency="USD",
            is_valid=False,
        )

    def search_tickers(self, query: str) -> List[TickerInfo]:
        q = query.strip().upper()
        matches = []
        for sym, meta in KNOWN_TICKERS.items():
            if q in sym or q in meta["name"].upper():
                matches.append(
                    TickerInfo(
                        symbol=sym,
                        name=meta["name"],
                        asset_type=meta["type"],  # type: ignore
                        exchange=meta["exchange"],
                        currency="USD",
                        is_valid=True,
                    )
                )
        return matches

    def fetch_news(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
    ) -> List[CanonicalNewsItem]:
        if self.simulate_failure == "rate_limit":
            raise RateLimitExceeded(provider="MockNewsProvider", retry_after_sec=60)
        elif self.simulate_failure == "timeout":
            raise NetworkTimeoutError(provider="MockNewsProvider", timeout_sec=10.0)
        elif self.simulate_failure == "auth_error":
            raise AuthenticationError(provider="MockNewsProvider")
        elif self.simulate_failure == "coverage_limit":
            raise CoverageLimitation(provider="MockNewsProvider", detail="Historical window exceeds allowed tier.")
        elif self.simulate_failure == "empty_news":
            return []

        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
        if start_dt > end_dt:
            raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date}).")

        now_utc = datetime.now(timezone.utc).isoformat()
        results: List[CanonicalNewsItem] = []

        clean_tickers = [t.strip().upper() for t in tickers if t.strip()]
        days_range = max(1, (end_dt - start_dt).days)

        for ticker in clean_tickers:
            if ticker not in KNOWN_TICKERS:
                continue

            for idx, (template, publisher, summary, synd_id) in enumerate(SAMPLE_NEWS_TEMPLATES):
                # Spread publication dates deterministically across date window
                day_offset = (idx * 5) % days_range
                pub_date = start_dt + timedelta(days=day_offset)
                pub_iso = datetime(pub_date.year, pub_date.month, pub_date.day, 13, 30, 0, tzinfo=timezone.utc).isoformat()

                article_id = f"mock_{ticker.lower()}_{pub_date.strftime('%Y%m%d')}_{idx}"
                headline = template.format(ticker=ticker)
                url = f"https://finance.mockwire.com/news/{ticker.lower()}/{article_id}"
                synd_group = f"synd_wire_{ticker}_{synd_id}" if synd_id == 5 else None

                item = CanonicalNewsItem(
                    article_id=article_id,
                    ticker_association=[ticker],
                    headline=headline,
                    publisher=publisher,
                    source_url=url,
                    published_at_utc=pub_iso,
                    retrieved_at_utc=now_utc,
                    summary_or_description=summary.format(ticker=ticker),
                    provider_identification="MockNewsProvider",
                    content_availability="summary_only",
                    language="en",
                    syndication_group=synd_group,
                    is_duplicate=False,
                    evidence_flags=["corroborated"] if idx < 3 else [],
                )
                results.append(item)

        # Sort chronologically (newest first)
        results.sort(key=lambda x: x.published_at_utc, reverse=True)
        return results

    def fetch_historical_prices(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> List[CanonicalPriceBar]:
        if self.simulate_failure == "rate_limit":
            raise RateLimitExceeded(provider="MockMarketDataProvider", retry_after_sec=60)
        elif self.simulate_failure == "timeout":
            raise NetworkTimeoutError(provider="MockMarketDataProvider", timeout_sec=10.0)
        elif self.simulate_failure == "auth_error":
            raise AuthenticationError(provider="MockMarketDataProvider")

        clean_symbol = symbol.strip().upper()
        if clean_symbol not in KNOWN_TICKERS:
            raise TickerNotFoundError(provider="MockMarketDataProvider", symbol=clean_symbol)

        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
        if start_dt > end_dt:
            raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date}).")

        base = float(KNOWN_TICKERS[clean_symbol]["base_price"])
        now_utc = datetime.now(timezone.utc).isoformat()
        bars: List[CanonicalPriceBar] = []

        current = start_dt
        current_price = base

        while current <= end_dt:
            if is_trading_day(current):
                seed_val = int(hashlib.md5(f"{clean_symbol}_{current}".encode()).hexdigest(), 16)
                pct_change = ((seed_val % 100) - 48) / 1000.0  # -4.8% to +5.1%
                
                open_p = round(current_price, 2)
                close_p = round(open_p * (1.0 + pct_change), 2)
                high_p = round(max(open_p, close_p) * (1.0 + ((seed_val % 25) / 1000.0)), 2)
                low_p = round(min(open_p, close_p) * (1.0 - ((seed_val % 25) / 1000.0)), 2)
                adj_close = round(close_p * 0.995, 2)  # realistic slight dividend adjustment
                volume = float(1500000 + (seed_val % 3000000))

                bars.append(
                    CanonicalPriceBar(
                        ticker=clean_symbol,
                        trading_date=current.isoformat(),
                        open=open_p,
                        high=high_p,
                        low=low_p,
                        close=close_p,
                        adjusted_close=adj_close,
                        volume=volume,
                        data_provider="MockMarketDataProvider",
                        retrieved_at_utc=now_utc,
                        delayed_flag=False,
                        exchange_timezone="America/New_York",
                    )
                )
                current_price = close_p

            current += timedelta(days=1)

        return bars

