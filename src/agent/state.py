"""TypedDict defining the LangGraph research orchestrator state."""
from typing import Any, Dict, List, Literal, Optional, TypedDict
from src.agent.schemas import ClaimCitation, CompiledResearchReport, StockNewsSummary, StockSentimentOutlook
from src.models.financial import CanonicalNewsItem, CanonicalPriceBar, TickerInfo


class ResearchState(TypedDict, total=False):
    """Execution state for the LangGraph research agent workflow."""
    # Request & session parameters
    user_id: str
    session_token: Optional[str]
    job_id: str
    idempotency_key: str
    tab: Literal["news", "sentiment"]
    tickers: List[str]
    date_preset: str
    custom_start: Optional[str]
    custom_end: Optional[str]
    start_date: str
    end_date: str
    horizon_days: Optional[Literal[1, 7, 30, 90]]
    as_of_date: str
    db_path: Optional[str]
    provider_mode: str

    # Workflow tracking & stage
    current_stage: str
    status: Literal[
        "requested", "validating", "authorized", "collecting",
        "normalizing", "verifying", "analyzing", "reporting",
        "completed", "failed", "cancelled", "rate_limited", "no_data", "invalid_input"
    ]
    error_message: Optional[str]
    error_code: Optional[str]
    quota_debited: bool

    # Retrieved & processed data
    validated_tickers: List[TickerInfo]
    invalid_tickers: List[str]
    raw_news: List[CanonicalNewsItem]
    deduplicated_news: List[CanonicalNewsItem]
    market_prices: Dict[str, List[CanonicalPriceBar]]

    # Agent analysis & evidence outputs
    news_summaries: List[StockNewsSummary]
    sentiment_outlooks: List[StockSentimentOutlook]
    verified_citations: List[ClaimCitation]
    unverified_claims: List[str]
    limitations: List[str]

    # Final report & persistence
    report: Optional[CompiledResearchReport]
    report_markdown: str
    report_json: Dict[str, Any]

