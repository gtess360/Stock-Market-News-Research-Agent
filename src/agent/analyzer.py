"""Evidence synthesis engine supporting OpenAI structured outputs and deterministic offline fallback."""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional
from src.agent.prompts import (
    NEWS_SUMMARY_PROMPT,
    SENTIMENT_OUTLOOK_PROMPT,
    SYSTEM_PROMPT_RESEARCH_ORCHESTRATOR,
)
from src.agent.schemas import (
    ClaimCitation,
    EvidenceTransparencyMetrics,
    SentimentTimelinePoint,
    StockNewsSummary,
    StockSentimentOutlook,
    WeightedFactor,
)
from src.models.financial import CanonicalNewsItem

POSITIVE_KEYWORDS = {"record", "beat", "growth", "strong", "upgrade", "partnership", "unveils", "profit", "surge", "accelerated"}
NEGATIVE_KEYWORDS = {"drop", "cut", "inquiry", "investigation", "supply chain", "bottleneck", "loss", "delays", "downgrade", "decline"}


class EvidenceAnalyzer:
    """Performs synthesis and claim extraction on retrieved news evidence."""

    def __init__(self, model_name: Optional[str] = None):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._llm = None

        if self.model_name != "offline-fallback-v1" and self.api_key and not self.api_key.startswith("your_"):
            try:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=self.model_name,
                    api_key=self.api_key,
                    temperature=0.0,
                    timeout=30.0,
                    max_retries=2,
                )
            except Exception:
                self._llm = None

    def analyze_stock_news(
        self,
        ticker: str,
        company_name: str,
        articles: List[CanonicalNewsItem],
        start_date: str,
        end_date: str,
    ) -> StockNewsSummary:
        """Synthesize news developments and link citations."""
        if not articles:
            return StockNewsSummary(
                ticker=ticker,
                company_name=company_name,
                total_articles_found=0,
                primary_themes=["No historical coverage located for specified date window."],
                key_developments=[],
                citations=[],
            )

        # Prepare evidence JSON (sanitized, untrusted data container)
        evidence_payload = [
            {
                "article_id": a.article_id,
                "headline": a.headline,
                "publisher": a.publisher,
                "published_at": a.published_at_utc,
                "summary": a.summary_or_description or "No abstract provided.",
                "url": a.source_url,
            }
            for a in articles if not a.is_duplicate  # Only canonical articles analyzed
        ]

        # Use Live LLM if available
        if self._llm:
            try:
                structured_llm = self._llm.with_structured_output(StockNewsSummary)
                prompt = NEWS_SUMMARY_PROMPT.format(
                    ticker=ticker,
                    company_name=company_name,
                    start_date=start_date,
                    end_date=end_date,
                    articles_json=json.dumps(evidence_payload, indent=2),
                )
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT_RESEARCH_ORCHESTRATOR},
                    {"role": "user", "content": prompt},
                ]
                result = structured_llm.invoke(messages)
                return result
            except Exception:
                # Graceful fallback to deterministic rule engine on network/credential error
                pass

        # Deterministic offline analysis fallback
        citations: List[ClaimCitation] = []
        developments: List[str] = []
        themes: List[str] = []

        for a in articles[:4]:
            claim_text = f"{company_name}: {a.headline} reported by {a.publisher}."
            developments.append(claim_text)
            citations.append(
                ClaimCitation(
                    claim=claim_text,
                    article_id=a.article_id,
                    publisher=a.publisher,
                    source_url=a.source_url,
                    publication_date=a.published_at_utc,
                    is_verified=True,
                )
            )

        if len(articles) > 0:
            themes.append(f"Strategic developments and operational execution in {articles[0].headline[:40]}...")

        return StockNewsSummary(
            ticker=ticker,
            company_name=company_name,
            total_articles_found=len(articles),
            primary_themes=themes or ["Market updates"],
            key_developments=developments,
            citations=citations,
        )

    def analyze_stock_sentiment(
        self,
        ticker: str,
        company_name: str,
        articles: List[CanonicalNewsItem],
        horizon_days: Literal[1, 7, 30, 90],
        as_of_date: str,
    ) -> StockSentimentOutlook:
        """Synthesize forward-looking catalysts, risks, and scenario outlook."""
        if not articles:
            return StockSentimentOutlook(
                ticker=ticker,
                company_name=company_name,
                current_news_sentiment="neutral",
                forward_scenario_outlook="neutral",
                horizon_days=horizon_days,
                evidence_strength="insufficient",
                catalysts=[],
                risks=["Insufficient evidence: No verified articles retrieved for research period."],
                opposing_evidence=[],
                citations=[],
                limitations=["No articles available within historical date window."],
            )

        evidence_payload = [
            {
                "article_id": a.article_id,
                "headline": a.headline,
                "publisher": a.publisher,
                "published_at": a.published_at_utc,
                "summary": a.summary_or_description or "No abstract provided.",
                "url": a.source_url,
            }
            for a in articles if not a.is_duplicate
        ]

        if self._llm:
            try:
                structured_llm = self._llm.with_structured_output(StockSentimentOutlook)
                prompt = SENTIMENT_OUTLOOK_PROMPT.format(
                    ticker=ticker,
                    company_name=company_name,
                    horizon_days=horizon_days,
                    as_of_date=as_of_date,
                    articles_json=json.dumps(evidence_payload, indent=2),
                )
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT_RESEARCH_ORCHESTRATOR},
                    {"role": "user", "content": prompt},
                ]
                result = structured_llm.invoke(messages)
                return result
            except Exception:
                pass

        # Deterministic offline rule-based sentiment calculation
        pos_count = 0
        neg_count = 0
        catalysts = []
        risks = []
        citations = []
        weighted_catalysts: List[WeightedFactor] = []
        weighted_risks: List[WeightedFactor] = []
        sentiment_timeline: List[SentimentTimelinePoint] = []

        # Determine time horizon label
        horizon_label: Literal["immediate", "tactical", "strategic"] = (
            "immediate" if horizon_days == 1 else "tactical" if horizon_days in (7, 30) else "strategic"
        )

        for a in articles:
            text = f"{a.headline} {a.summary_or_description or ''}".lower()
            is_pos = any(w in text for w in POSITIVE_KEYWORDS)
            is_neg = any(w in text for w in NEGATIVE_KEYWORDS)
            pub_date = (a.published_at_utc or "2026-11-01")[:10]

            score = 0.0
            label: Literal["positive", "negative", "neutral", "mixed"] = "neutral"
            if is_pos and not is_neg:
                score = 1.0
                label = "positive"
            elif is_neg and not is_pos:
                score = -1.0
                label = "negative"
            elif is_pos and is_neg:
                score = 0.0
                label = "mixed"

            # Record timeline point
            sentiment_timeline.append(
                SentimentTimelinePoint(
                    date=pub_date,
                    ticker=ticker,
                    headline=a.headline,
                    publisher=a.publisher,
                    sentiment_label=label,
                    sentiment_score=score,
                    article_id=a.article_id,
                    source_url=a.source_url,
                )
            )

            if is_pos:
                pos_count += 1
                cat = f"Catalyst: {a.headline}"
                catalysts.append(cat)
                citations.append(
                    ClaimCitation(
                        claim=cat,
                        article_id=a.article_id,
                        publisher=a.publisher,
                        source_url=a.source_url,
                        publication_date=a.published_at_utc,
                    )
                )
                impact: Literal["high", "medium", "low"] = "high" if any(k in text for k in ("record", "surge", "beat")) else "medium"
                weighted_catalysts.append(
                    WeightedFactor(
                        factor_text=a.headline,
                        category="catalyst",
                        impact_weight=impact,
                        time_horizon=horizon_label,
                        corroborating_sources_count=1,
                        source_article_ids=[a.article_id],
                    )
                )

            if is_neg:
                neg_count += 1
                risk = f"Risk factor: {a.headline}"
                risks.append(risk)
                citations.append(
                    ClaimCitation(
                        claim=risk,
                        article_id=a.article_id,
                        publisher=a.publisher,
                        source_url=a.source_url,
                        publication_date=a.published_at_utc,
                    )
                )
                impact = "high" if any(k in text for k in ("inquiry", "investigation", "cut", "drop")) else "medium"
                weighted_risks.append(
                    WeightedFactor(
                        factor_text=a.headline,
                        category="risk",
                        impact_weight=impact,
                        time_horizon=horizon_label,
                        corroborating_sources_count=1,
                        source_article_ids=[a.article_id],
                    )
                )

        # Sort timeline by date ascending
        sentiment_timeline.sort(key=lambda p: p.date)

        if pos_count > neg_count:
            sentiment = "positive"
            outlook = "bullish"
        elif neg_count > pos_count:
            sentiment = "negative"
            outlook = "bearish"
        elif pos_count > 0 and neg_count > 0:
            sentiment = "mixed"
            outlook = "mixed"
        else:
            sentiment = "neutral"
            outlook = "neutral"

        # Evidence strength based strictly on canonical article volume & publisher diversity
        unique_publishers = sorted(list({a.publisher for a in articles}))
        num_canonical = len([a for a in articles if not a.is_duplicate])
        num_syndicated = len([a for a in articles if a.is_duplicate])

        if num_canonical >= 4 and len(unique_publishers) >= 2:
            evidence_strength = "strong"
        elif num_canonical >= 2:
            evidence_strength = "moderate"
        else:
            evidence_strength = "weak"

        # Recency distribution relative to as_of_date
        recency_last_7d = 0
        recency_older = 0
        try:
            ref_dt = datetime.fromisoformat(as_of_date.replace("Z", "+00:00"))
        except Exception:
            ref_dt = datetime.now()

        for a in articles:
            try:
                a_dt = datetime.fromisoformat((a.published_at_utc or "").replace("Z", "+00:00"))
                if (ref_dt - a_dt).days <= 7:
                    recency_last_7d += 1
                else:
                    recency_older += 1
            except Exception:
                recency_last_7d += 1

        diversity_rating: Literal["high", "moderate", "low", "single_source"] = (
            "high" if len(unique_publishers) >= 3 else "moderate" if len(unique_publishers) == 2 else "single_source" if len(unique_publishers) == 1 else "low"
        )

        transparency = EvidenceTransparencyMetrics(
            total_articles_evaluated=len(articles),
            canonical_unique_articles=num_canonical,
            syndicated_duplicates_filtered=num_syndicated,
            unique_publishers_count=len(unique_publishers),
            unique_publishers=unique_publishers,
            recency_last_7d_count=recency_last_7d,
            recency_older_count=recency_older,
            source_diversity_rating=diversity_rating,
        )

        # Net sentiment score normalized between -1.0 and +1.0
        total_eval = max(len(articles), 1)
        net_score = round((pos_count - neg_count) / total_eval, 2)

        # Scenario triggers (conditions that could alter or reverse the scenario)
        if outlook == "bullish":
            triggers = [
                "Unexpected regulatory investigation or software stack inquiry escalation.",
                f"Supply chain component delivery constraints extending past {horizon_days} days.",
                "Macroeconomic tightening moderating enterprise cloud infrastructure commitments.",
            ]
        elif outlook == "bearish":
            triggers = [
                "Swift resolution of preliminary regulatory inquiries without enforcement.",
                "Accelerated commercial shipment milestones outpacing brokerage consensus.",
                "Key enterprise customer wins or expanded hyperscaler partnership agreements.",
            ]
        else:
            triggers = [
                f"Decisive quarterly earnings release clarifying commercial momentum within {horizon_days} days.",
                "Broad enterprise AI infrastructure spend acceleration or deceleration.",
            ]

        opposing_items = risks[:1] if sentiment == "positive" else catalysts[:1] if sentiment == "negative" else []
        weighted_opposing: List[WeightedFactor] = (
            weighted_risks[:1] if sentiment == "positive" else weighted_catalysts[:1] if sentiment == "negative" else []
        )

        return StockSentimentOutlook(
            ticker=ticker,
            company_name=company_name,
            current_news_sentiment=sentiment,  # type: ignore
            forward_scenario_outlook=outlook,  # type: ignore
            horizon_days=horizon_days,
            evidence_strength=evidence_strength,  # type: ignore
            catalysts=catalysts[:3] or [f"Market momentum over {horizon_days}-day horizon"],
            risks=risks[:3] or ["Macroeconomic volatility and general market conditions"],
            opposing_evidence=opposing_items,
            citations=citations,
            limitations=["Rule-based deterministic synthesis applied (offline/mock mode)."],
            weighted_catalysts=weighted_catalysts[:4],
            weighted_risks=weighted_risks[:4],
            weighted_opposing=weighted_opposing[:2],
            sentiment_timeline=sentiment_timeline,
            transparency_metrics=transparency,
            scenario_triggers=triggers,
            net_sentiment_score=net_score,
        )

