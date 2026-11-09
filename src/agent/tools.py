"""Specialized read-only tools invoked by the LangGraph research orchestrator."""
from typing import Dict, List, Optional, Tuple
from src.agent.schemas import ClaimCitation
from src.models.financial import CanonicalNewsItem, CanonicalPriceBar, TickerInfo
from src.providers.base import ProviderException, TickerNotFoundError
from src.providers.cache import default_cache
from src.providers.deduplication import deduplicate_news_articles
from src.providers.factory import ProviderFactory


def validate_tickers_tool(
    tickers: List[str],
    provider_mode: str = "mock",
) -> Tuple[List[TickerInfo], List[str]]:
    """Validate a list of ticker symbols through the configured provider.
    
    Returns:
        Tuple[List[TickerInfo], List[str]]: (valid_tickers_info, invalid_symbols)
    """
    ticker_provider = ProviderFactory.get_ticker_provider(provider_mode)
    valid_list: List[TickerInfo] = []
    invalid_list: List[str] = []

    for sym in tickers:
        clean = sym.strip().upper()
        if not clean:
            continue
        try:
            info = ticker_provider.validate_ticker(clean)
            if info.is_valid:
                valid_list.append(info)
            else:
                invalid_list.append(clean)
        except Exception:
            invalid_list.append(clean)

    return valid_list, invalid_list


def fetch_market_prices_tool(
    symbol: str,
    start_date: str,
    end_date: str,
    provider_mode: str = "mock",
    use_cache: bool = True,
) -> List[CanonicalPriceBar]:
    """Retrieve daily OHLCV price series for a symbol with TTL caching."""
    clean = symbol.strip().upper()
    cache_params = {"symbol": clean, "start": start_date, "end": end_date}
    
    if use_cache:
        cached = default_cache.get(provider_mode, "market_data", cache_params)
        if cached is not None:
            return cached

    market_provider = ProviderFactory.get_market_data_provider(provider_mode)
    try:
        bars = market_provider.fetch_historical_prices(clean, start_date=start_date, end_date=end_date)
        if use_cache:
            default_cache.set(provider_mode, "market_data", cache_params, bars)
        return bars
    except TickerNotFoundError:
        return []
    except ProviderException:
        raise


def fetch_news_tool(
    tickers: List[str],
    start_date: str,
    end_date: str,
    provider_mode: str = "mock",
    use_cache: bool = True,
) -> List[CanonicalNewsItem]:
    """Fetch financial news articles across specified tickers with TTL caching."""
    clean_tickers = sorted(list({t.strip().upper() for t in tickers if t.strip()}))
    cache_params = {"tickers": clean_tickers, "start": start_date, "end": end_date}

    if use_cache:
        cached = default_cache.get(provider_mode, "news", cache_params)
        if cached is not None:
            return cached

    news_provider = ProviderFactory.get_news_provider(provider_mode)
    articles = news_provider.fetch_news(clean_tickers, start_date=start_date, end_date=end_date)
    if use_cache:
        default_cache.set(provider_mode, "news", cache_params, articles)
    return articles


def deduplicate_news_tool(
    articles: List[CanonicalNewsItem],
) -> List[CanonicalNewsItem]:
    """Apply the deduplication engine to link syndicated and duplicate news stories."""
    return deduplicate_news_articles(articles)


def verify_citations_tool(
    citations: List[ClaimCitation],
    available_articles: List[CanonicalNewsItem],
) -> Tuple[List[ClaimCitation], List[str]]:
    """Deterministically verify each claim citation against the set of retrieved canonical articles.
    
    Returns:
        Tuple[List[ClaimCitation], List[str]]: (verified_citations, unverified_or_hallucinated_claims)
    """
    article_index: Dict[str, CanonicalNewsItem] = {a.article_id: a for a in available_articles}
    verified: List[ClaimCitation] = []
    unverified_claims: List[str] = []

    for cit in citations:
        art = article_index.get(cit.article_id)
        if not art:
            # Fabricated / hallucinated article ID
            unverified_claims.append(f"Unverified Claim: '{cit.claim}' (Article ID '{cit.article_id}' not found in retrieved evidence)")
            continue

        # Check factual content support: verify claim has grounding in the cited article content
        content_haystack = f"{art.headline} {art.summary_or_description or ''}".lower()
        stopwords = {"this", "that", "with", "from", "have", "were", "been", "their", "about", "which", "after", "before", "over", "under", "also", "into", "than"}
        claim_words = [w.strip(".,;:\"'!?()[]{}").lower() for w in cit.claim.split() if len(w) >= 4 and w.lower() not in stopwords]
        if claim_words:
            matched_words = [w for w in claim_words if w in content_haystack]
            if not matched_words:
                unverified_claims.append(f"Ungrounded Claim: '{cit.claim}' (Factual content not found in cited Article '{cit.article_id}')")
                continue

        # Check publisher corroboration
        is_exact_publisher = art.publisher.strip().lower() == cit.publisher.strip().lower()
        verified.append(
            ClaimCitation(
                claim=cit.claim,
                article_id=art.article_id,
                publisher=art.publisher,
                source_url=art.source_url,
                publication_date=art.published_at_utc,
                is_verified=True,
                grounding_notes=None if is_exact_publisher else f"Cited via publisher: {art.publisher}",
            )
        )

    return verified, unverified_claims

