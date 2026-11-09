"""Unit tests for news article deduplication and syndication detection."""
from src.models.financial import CanonicalNewsItem
from src.providers.deduplication import deduplicate_news_articles


def test_exact_url_deduplication():
    """Verify identical URLs are marked duplicate and linked to canonical item."""
    item1 = CanonicalNewsItem(
        article_id="art_orig",
        ticker_association=["AAPL"],
        headline="Apple Unveils New Product Line",
        publisher="Reuters",
        source_url="https://example.com/apple1",
        published_at_utc="2026-11-01T10:00:00Z",
        retrieved_at_utc="2026-11-01T12:00:00Z",
        provider_identification="Test",
    )
    item2 = CanonicalNewsItem(
        article_id="art_dup",
        ticker_association=["AAPL"],
        headline="Apple Unveils New Product Line (Repost)",
        publisher="Yahoo Finance",
        source_url="https://example.com/apple1",  # Same URL
        published_at_utc="2026-11-01T11:00:00Z",
        retrieved_at_utc="2026-11-01T12:00:00Z",
        provider_identification="Test",
    )

    results = deduplicate_news_articles([item1, item2])
    assert len(results) == 2

    # Find duplicate and canonical
    canonical = next(r for r in results if r.article_id == "art_orig")
    duplicate = next(r for r in results if r.article_id == "art_dup")

    assert canonical.is_duplicate is False
    assert duplicate.is_duplicate is True
    assert duplicate.canonical_article_id == "art_orig"
    assert "syndicated_duplicate" in duplicate.evidence_flags


def test_syndication_group_deduplication():
    """Verify matching syndication groups link articles together."""
    wire1 = CanonicalNewsItem(
        article_id="wire_pr",
        ticker_association=["MSFT"],
        headline="Microsoft Partners with Telecom Provider",
        publisher="PR Newswire",
        source_url="https://prn.example.com/wire1",
        published_at_utc="2026-11-02T08:00:00Z",
        retrieved_at_utc="2026-11-02T09:00:00Z",
        syndication_group="synd_msft_001",
        provider_identification="Test",
    )
    wire2 = CanonicalNewsItem(
        article_id="wire_bw",
        ticker_association=["MSFT"],
        headline="Microsoft and Telecom Sign Strategic Deployment Pact",
        publisher="Business Wire",
        source_url="https://bw.example.com/wire2",
        published_at_utc="2026-11-02T08:05:00Z",
        retrieved_at_utc="2026-11-02T09:00:00Z",
        syndication_group="synd_msft_001",  # Same group
        provider_identification="Test",
    )

    results = deduplicate_news_articles([wire1, wire2])
    dup = next(r for r in results if r.article_id == "wire_bw")
    orig = next(r for r in results if r.article_id == "wire_pr")

    assert orig.is_duplicate is False
    assert dup.is_duplicate is True
    assert dup.canonical_article_id == "wire_pr"


def test_headline_similarity_deduplication():
    """Verify high headline semantic overlap on the same day triggers duplicate flag."""
    a1 = CanonicalNewsItem(
        article_id="head_1",
        ticker_association=["NVDA"],
        headline="NVIDIA Reports Record Cloud & AI Segment Revenue",
        publisher="Bloomberg",
        source_url="https://bloomberg.example.com/nvda1",
        published_at_utc="2026-11-03T16:00:00Z",
        retrieved_at_utc="2026-11-03T17:00:00Z",
        provider_identification="Test",
    )
    a2 = CanonicalNewsItem(
        article_id="head_2",
        ticker_association=["NVDA"],
        headline="NVIDIA Reports Record Cloud and AI Segment Revenues",
        publisher="CNBC",
        source_url="https://cnbc.example.com/nvda2",
        published_at_utc="2026-11-03T16:15:00Z",
        retrieved_at_utc="2026-11-03T17:00:00Z",
        provider_identification="Test",
    )

    results = deduplicate_news_articles([a1, a2])
    dup = next(r for r in results if r.article_id == "head_2")
    canonical = next(r for r in results if r.article_id == "head_1")

    assert canonical.is_duplicate is False
    assert dup.is_duplicate is True
    assert dup.canonical_article_id == "head_1"
    # Canonical item receives 'corroborated' flag from secondary publisher
    assert "corroborated" in canonical.evidence_flags

