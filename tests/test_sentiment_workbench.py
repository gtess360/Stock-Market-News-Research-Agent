"""Automated tests for Phase 3.6 Sentiment Research Workbench enhancements."""
from datetime import datetime
import pytest
from src.agent.analyzer import EvidenceAnalyzer
from src.agent.schemas import (
    ClaimCitation,
    EvidenceTransparencyMetrics,
    SentimentTimelinePoint,
    StockSentimentOutlook,
    WeightedFactor,
)
from src.models.financial import CanonicalNewsItem
from src.ui.charts import (
    create_multi_stock_sentiment_comparison_chart,
    create_sentiment_timeline_chart,
)


@pytest.fixture
def mock_articles_positive():
    """Fixture providing positive sentiment canonical articles."""
    return [
        CanonicalNewsItem(
            article_id="art_pos_1",
            ticker_association=["NVDA"],
            headline="NVDA Reports Record Quarterly Cloud Revenue Beat",
            publisher="Bloomberg",
            source_url="https://finance.mockwire.com/news/nvda/1",
            published_at_utc="2026-11-02T10:00:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            summary_or_description="Cloud data center segment surged 112% year-over-year.",
            provider_identification="mock",
            is_duplicate=False,
        ),
        CanonicalNewsItem(
            article_id="art_pos_2",
            ticker_association=["NVDA"],
            headline="Wall Street Brokerages Upgrade NVDA Following Earnings",
            publisher="Reuters",
            source_url="https://finance.mockwire.com/news/nvda/2",
            published_at_utc="2026-11-03T11:00:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            summary_or_description="Strong multi-quarter growth runway cited.",
            provider_identification="mock",
            is_duplicate=False,
        ),
        CanonicalNewsItem(
            article_id="art_pos_3",
            ticker_association=["NVDA"],
            headline="NVDA Unveils Next-Gen AI Architecture Ahead of Schedule",
            publisher="Wall Street Journal",
            source_url="https://finance.mockwire.com/news/nvda/3",
            published_at_utc="2026-11-04T12:00:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            summary_or_description="Next-generation accelerator production ramping smoothly.",
            provider_identification="mock",
            is_duplicate=False,
        ),
        CanonicalNewsItem(
            article_id="art_pos_4",
            ticker_association=["NVDA"],
            headline="Hyperscalers Expand Long-Term Cloud Partnership with NVDA",
            publisher="Financial Times",
            source_url="https://finance.mockwire.com/news/nvda/4",
            published_at_utc="2026-11-05T13:00:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            summary_or_description="Multi-year infrastructure supply commitments secured.",
            provider_identification="mock",
            is_duplicate=False,
        ),
    ]


@pytest.fixture
def mock_articles_negative():
    """Fixture providing negative sentiment canonical articles."""
    return [
        CanonicalNewsItem(
            article_id="art_neg_1",
            ticker_association=["INTC"],
            headline="Regulatory Authorities Open Preliminary Inquiry into INTC Software Ecosystem",
            publisher="Bloomberg",
            source_url="https://finance.mockwire.com/news/intc/1",
            published_at_utc="2026-11-02T10:00:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            summary_or_description="Antitrust scrutiny intensifies regarding bundling practices.",
            provider_identification="mock",
            is_duplicate=False,
        ),
        CanonicalNewsItem(
            article_id="art_neg_2",
            ticker_association=["INTC"],
            headline="Supply Chain Bottlenecks Moderate Component Deliveries for INTC",
            publisher="Reuters",
            source_url="https://finance.mockwire.com/news/intc/2",
            published_at_utc="2026-11-03T11:00:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            summary_or_description="Fabrication delays impact server chip availability.",
            provider_identification="mock",
            is_duplicate=False,
        ),
    ]


# ---------------- 1. Sentiment Classifications & Horizons ----------------

def test_sentiment_classification_categories(mock_articles_positive, mock_articles_negative):
    """Verify Bullish, Bearish, and Neutral classifications under deterministic engine."""
    analyzer = EvidenceAnalyzer()

    # Positive -> Bullish
    outlook_pos = analyzer.analyze_stock_sentiment(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        articles=mock_articles_positive,
        horizon_days=30,
        as_of_date="2026-11-07",
    )
    assert outlook_pos.current_news_sentiment == "positive"
    assert outlook_pos.forward_scenario_outlook == "bullish"
    assert outlook_pos.net_sentiment_score > 0.0

    # Negative -> Bearish
    outlook_neg = analyzer.analyze_stock_sentiment(
        ticker="INTC",
        company_name="Intel Corporation",
        articles=mock_articles_negative,
        horizon_days=30,
        as_of_date="2026-11-07",
    )
    assert outlook_neg.current_news_sentiment == "negative"
    assert outlook_neg.forward_scenario_outlook == "bearish"
    assert outlook_neg.net_sentiment_score < 0.0


def test_multi_horizon_handling(mock_articles_positive):
    """Verify all four approved forward horizons (1, 7, 30, 90 days) operate correctly."""
    analyzer = EvidenceAnalyzer()
    for horizon in (1, 7, 30, 90):
        res = analyzer.analyze_stock_sentiment(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            articles=mock_articles_positive,
            horizon_days=horizon,  # type: ignore
            as_of_date="2026-11-07",
        )
        assert res.horizon_days == horizon
        assert len(res.weighted_catalysts) > 0
        # 1-day maps to immediate, 7/30 to tactical, 90 to strategic
        expected_time_horizon = "immediate" if horizon == 1 else "tactical" if horizon in (7, 30) else "strategic"
        assert res.weighted_catalysts[0].time_horizon == expected_time_horizon


def test_distinguish_historical_sentiment_vs_forward_outlook(mock_articles_positive):
    """Verify historical news sentiment (retrospective) is decoupled from forward scenario outlook."""
    analyzer = EvidenceAnalyzer()
    outlook = analyzer.analyze_stock_sentiment(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        articles=mock_articles_positive,
        horizon_days=30,
        as_of_date="2026-11-07",
    )
    # Both fields exist and use independent taxonomies
    assert hasattr(outlook, "current_news_sentiment")
    assert hasattr(outlook, "forward_scenario_outlook")
    assert outlook.current_news_sentiment in ("positive", "negative", "neutral", "mixed")
    assert outlook.forward_scenario_outlook in ("bullish", "bearish", "neutral", "mixed")


# ---------------- 2. Evidence Grounding & Transparency ----------------

def test_evidence_transparency_metrics_calculation(mock_articles_positive):
    """Verify transparent audit metrics: publisher count, unique articles, and diversity."""
    analyzer = EvidenceAnalyzer()
    outlook = analyzer.analyze_stock_sentiment(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        articles=mock_articles_positive,
        horizon_days=30,
        as_of_date="2026-11-07",
    )
    metrics = outlook.transparency_metrics
    assert metrics is not None
    assert metrics.total_articles_evaluated == 4
    assert metrics.canonical_unique_articles == 4
    assert metrics.unique_publishers_count == 4
    assert "Bloomberg" in metrics.unique_publishers
    assert "Reuters" in metrics.unique_publishers
    assert metrics.source_diversity_rating == "high"


def test_syndicated_duplicates_do_not_inflate_evidence_strength():
    """Verify duplicate wire stories do not count as independent corroboration."""
    analyzer = EvidenceAnalyzer()
    # 1 canonical + 3 duplicates from the same wire story
    articles = [
        CanonicalNewsItem(
            article_id="dup_1",
            ticker_association=["XYZ"],
            headline="XYZ Announces Acquisition",
            publisher="WireFeed",
            source_url="https://feed.com/1",
            published_at_utc="2026-11-02T10:00:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            provider_identification="mock",
            is_duplicate=False,
        ),
        CanonicalNewsItem(
            article_id="dup_2",
            ticker_association=["XYZ"],
            headline="XYZ Announces Acquisition",
            publisher="WireFeed",
            source_url="https://feed.com/2",
            published_at_utc="2026-11-02T10:05:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            provider_identification="mock",
            is_duplicate=True,  # Duplicate
        ),
        CanonicalNewsItem(
            article_id="dup_3",
            ticker_association=["XYZ"],
            headline="XYZ Announces Acquisition",
            publisher="WireFeed",
            source_url="https://feed.com/3",
            published_at_utc="2026-11-02T10:10:00Z",
            retrieved_at_utc="2026-11-07T20:00:00Z",
            provider_identification="mock",
            is_duplicate=True,  # Duplicate
        ),
    ]

    outlook = analyzer.analyze_stock_sentiment(
        ticker="XYZ",
        company_name="XYZ Corp",
        articles=articles,
        horizon_days=30,
        as_of_date="2026-11-07",
    )
    # With only 1 canonical article and 1 publisher, evidence strength MUST NOT be 'strong'
    assert outlook.evidence_strength in ("weak", "moderate")
    assert outlook.evidence_strength != "strong"
    assert outlook.transparency_metrics.syndicated_duplicates_filtered == 2
    assert outlook.transparency_metrics.canonical_unique_articles == 1


def test_no_fabricated_probabilities_in_output(mock_articles_positive):
    """Verify output contains strictly qualitative assessments, not arbitrary percentages."""
    analyzer = EvidenceAnalyzer()
    outlook = analyzer.analyze_stock_sentiment(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        articles=mock_articles_positive,
        horizon_days=30,
        as_of_date="2026-11-07",
    )
    # Check that no raw probability strings or hallucinated percentage values exist
    text_representation = str(outlook.model_dump())
    assert "%" not in text_representation or "net_sentiment_score" not in text_representation
    assert outlook.evidence_strength in ("strong", "moderate", "weak", "insufficient")


# ---------------- 3. Timeline Points & Missing Data ----------------

def test_sentiment_timeline_point_generation(mock_articles_positive):
    """Verify timestamped sentiment points are accurately generated."""
    analyzer = EvidenceAnalyzer()
    outlook = analyzer.analyze_stock_sentiment(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        articles=mock_articles_positive,
        horizon_days=30,
        as_of_date="2026-11-07",
    )
    assert len(outlook.sentiment_timeline) == 4
    for pt in outlook.sentiment_timeline:
        assert pt.ticker == "NVDA"
        assert pt.date.startswith("2026-11-")
        assert pt.sentiment_score in (-1.0, 0.0, 1.0)
        assert len(pt.headline) > 0


def test_missing_evidence_graceful_handling():
    """Verify empty news articles degrade gracefully with insufficient evidence label."""
    analyzer = EvidenceAnalyzer()
    outlook = analyzer.analyze_stock_sentiment(
        ticker="UNKNOWN",
        company_name="Unknown Corp",
        articles=[],
        horizon_days=30,
        as_of_date="2026-11-07",
    )
    assert outlook.evidence_strength == "insufficient"
    assert outlook.forward_scenario_outlook == "neutral"
    assert len(outlook.catalysts) == 0
    assert len(outlook.risks) >= 1
    assert "Insufficient evidence" in outlook.risks[0]


# ---------------- 4. Sentiment Chart Visualizations ----------------

def test_sentiment_charts_rendering(mock_articles_positive):
    """Verify sentiment timeline and multi-stock comparison Plotly figures."""
    analyzer = EvidenceAnalyzer()
    nvda_outlook = analyzer.analyze_stock_sentiment(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        articles=mock_articles_positive,
        horizon_days=30,
        as_of_date="2026-11-07",
    )

    # 1. Timeline Chart
    timeline_fig = create_sentiment_timeline_chart(nvda_outlook.sentiment_timeline, "NVDA")
    assert timeline_fig is not None
    assert len(timeline_fig.data) >= 1
    assert timeline_fig.data[0].type == "scatter"

    # 2. Multi-Stock Comparison Chart
    aapl_outlook = StockSentimentOutlook(
        ticker="AAPL",
        company_name="Apple Inc.",
        current_news_sentiment="neutral",
        forward_scenario_outlook="neutral",
        horizon_days=30,
        evidence_strength="moderate",
        catalysts=["Services revenue stability"],
        risks=["China market competition"],
        net_sentiment_score=0.15,
    )
    comp_fig = create_multi_stock_sentiment_comparison_chart([nvda_outlook, aapl_outlook])
    assert comp_fig is not None
    assert len(comp_fig.data) == 3  # Catalysts bar, Risks bar, Net Sentiment scatter line

