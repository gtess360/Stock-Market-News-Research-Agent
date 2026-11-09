"""Pydantic schemas and structured output contracts for LangGraph agent research."""
from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ClaimCitation(BaseModel):
    """Citation linking a factual claim to a retrieved canonical article."""
    claim: str
    article_id: str
    publisher: str
    source_url: str
    publication_date: str
    is_verified: bool = True
    grounding_notes: Optional[str] = None


class StockNewsSummary(BaseModel):
    """Structured news summary for a specific stock ticker."""
    ticker: str
    company_name: str
    total_articles_found: int
    primary_themes: List[str] = Field(default_factory=list)
    key_developments: List[str] = Field(default_factory=list)
    citations: List[ClaimCitation] = Field(default_factory=list)


class WeightedFactor(BaseModel):
    """Transparently weighted positive catalyst or downside risk factor."""
    factor_text: str
    category: Literal["catalyst", "risk", "opposing"]
    impact_weight: Literal["high", "medium", "low"] = "medium"
    time_horizon: Literal["immediate", "tactical", "strategic"] = "tactical"
    corroborating_sources_count: int = 1
    source_article_ids: List[str] = Field(default_factory=list)


class SentimentTimelinePoint(BaseModel):
    """Timestamped sentiment data point derived from canonical news articles."""
    date: str
    ticker: str
    headline: str
    publisher: str
    sentiment_label: Literal["positive", "negative", "neutral", "mixed"]
    sentiment_score: float  # -1.0 (bearish) to +1.0 (bullish)
    article_id: str
    source_url: str


class EvidenceTransparencyMetrics(BaseModel):
    """Transparent audit metrics detailing evidence diversity and recency."""
    total_articles_evaluated: int
    canonical_unique_articles: int
    syndicated_duplicates_filtered: int
    unique_publishers_count: int
    unique_publishers: List[str] = Field(default_factory=list)
    recency_last_7d_count: int = 0
    recency_older_count: int = 0
    source_diversity_rating: Literal["high", "moderate", "low", "single_source"] = "moderate"


class StockSentimentOutlook(BaseModel):
    """Structured forward-looking sentiment and scenario analysis for a specific ticker."""
    ticker: str
    company_name: str
    current_news_sentiment: Literal["positive", "negative", "neutral", "mixed"]
    forward_scenario_outlook: Literal["bullish", "bearish", "neutral", "mixed"]
    horizon_days: Literal[1, 7, 30, 90]
    evidence_strength: Literal["strong", "moderate", "weak", "insufficient"]
    catalysts: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    opposing_evidence: List[str] = Field(default_factory=list)
    citations: List[ClaimCitation] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    # Phase 3.6 Enhancements
    weighted_catalysts: List[WeightedFactor] = Field(default_factory=list)
    weighted_risks: List[WeightedFactor] = Field(default_factory=list)
    weighted_opposing: List[WeightedFactor] = Field(default_factory=list)
    sentiment_timeline: List[SentimentTimelinePoint] = Field(default_factory=list)
    transparency_metrics: Optional[EvidenceTransparencyMetrics] = None
    scenario_triggers: List[str] = Field(default_factory=list)
    net_sentiment_score: float = 0.0  # Normalized between -1.0 and +1.0


class CompiledResearchReport(BaseModel):
    """Canonical research report schema combining citations, summaries, and audit metadata."""
    report_id: str
    job_id: str
    user_id: str
    tab: Literal["news", "sentiment"]
    as_of_date: str
    date_range: Dict[str, str]  # {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    tickers: List[str]
    horizon_days: Optional[Literal[1, 7, 30, 90]] = None
    executive_summary: str
    stock_news_summaries: List[StockNewsSummary] = Field(default_factory=list)
    stock_sentiment_outlooks: List[StockSentimentOutlook] = Field(default_factory=list)
    all_citations: List[ClaimCitation] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    generated_at_utc: str
    model_version: str
    prompt_version: str = "v1.0"

