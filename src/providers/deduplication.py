"""Financial news article deduplication and syndication analysis engine."""
import difflib
import re
from typing import List, Set
from src.models.financial import CanonicalNewsItem

PUNCT_REGEX = re.compile(r"[^\w\s]")
STOP_WORDS = {"and", "the", "for", "with", "from", "into", "over", "than"}


def normalize_headline(headline: str) -> Set[str]:
    """Tokenize and stem headline for semantic comparison, retaining key financial terms (e.g., AI, EV, Q3)."""
    cleaned = PUNCT_REGEX.sub(" ", headline.lower())
    tokens = set()
    for w in cleaned.split():
        if w in STOP_WORDS or len(w) < 2:
            continue
        # Simple plural stemming (e.g. revenues -> revenue)
        stemmed = w[:-1] if w.endswith("s") and len(w) > 4 else w
        tokens.add(stemmed)
    return tokens


def compute_headline_similarity(headline_a: str, headline_b: str, tokens_a: Set[str], tokens_b: Set[str]) -> float:
    """Compute combined Jaccard token similarity and string sequence similarity."""
    # 1. Jaccard token similarity
    jaccard = 0.0
    if tokens_a and tokens_b:
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        jaccard = intersection / union if union > 0 else 0.0

    # 2. Sequence matcher ratio
    seq_ratio = difflib.SequenceMatcher(None, headline_a.lower(), headline_b.lower()).ratio()

    # Weighted blend
    return max(jaccard, seq_ratio)


def deduplicate_news_articles(
    articles: List[CanonicalNewsItem],
    similarity_threshold: float = 0.65,
) -> List[CanonicalNewsItem]:
    """Identify duplicate and syndicated articles, flagging duplicates and linking to canonical records.
    
    Processing Rules:
    1. Sort articles chronologically (earliest published first becomes canonical).
    2. Group by ticker.
    3. If URLs match, mark as duplicate.
    4. If syndication_group matches, mark as syndicated duplicate.
    5. If publication dates are within 48 hours and headline similarity >= threshold,
       flag as duplicate.
    6. Attach 'syndicated_duplicate' and 'corroborated' evidence flags accordingly.
    
    Returns:
        List[CanonicalNewsItem]: Updated list with duplicate metadata populated.
    """
    if not articles:
        return []

    sorted_articles = sorted(articles, key=lambda a: a.published_at_utc)
    processed: List[CanonicalNewsItem] = []

    for item in sorted_articles:
        tokens = normalize_headline(item.headline)
        pub_day = item.published_at_utc[:10]
        duplicate_of = None

        for prev in processed:
            if prev.is_duplicate:
                continue

            shared_tickers = set(item.ticker_association) & set(prev.ticker_association)
            if not shared_tickers:
                continue

            # 1. Exact URL match
            if item.source_url == prev.source_url:
                duplicate_of = prev
                break

            # 2. Matching explicit syndication group
            if (
                item.syndication_group
                and prev.syndication_group
                and item.syndication_group == prev.syndication_group
            ):
                duplicate_of = prev
                break

            # 3. High headline similarity within 48-hour window
            sim = compute_headline_similarity(
                item.headline,
                prev.headline,
                tokens,
                normalize_headline(prev.headline),
            )
            if sim >= similarity_threshold:
                duplicate_of = prev
                break

        if duplicate_of:
            flags = list(set(item.evidence_flags + ["syndicated_duplicate"]))
            updated = item.model_copy(
                update={
                    "is_duplicate": True,
                    "canonical_article_id": duplicate_of.article_id,
                    "evidence_flags": flags,
                }
            )
            if item.publisher.lower() != duplicate_of.publisher.lower():
                if "corroborated" not in duplicate_of.evidence_flags:
                    duplicate_of.evidence_flags.append("corroborated")
            processed.append(updated)
        else:
            processed.append(item)

    processed.sort(key=lambda a: a.published_at_utc, reverse=True)
    return processed
