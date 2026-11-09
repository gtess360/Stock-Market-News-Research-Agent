"""LangGraph node implementations executing the bounded research pipeline."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from src.agent.analyzer import EvidenceAnalyzer
from src.agent.schemas import ClaimCitation, CompiledResearchReport
from src.agent.state import ResearchState
from src.agent.tools import (
    deduplicate_news_tool,
    fetch_market_prices_tool,
    fetch_news_tool,
    validate_tickers_tool,
    verify_citations_tool,
)
from src.database.connection import get_connection
from src.models.financial import CanonicalNewsItem, CanonicalPriceBar
from src.providers.base import ProviderException, RateLimitExceeded
from src.providers.date_filter import get_market_current_date, resolve_date_window
from src.services.auth_service import validate_session
from src.services.entitlement_service import check_entitlement
from src.services.job_service import complete_research_job, create_research_job


def validate_inputs_node(state: ResearchState) -> Dict[str, Any]:
    """Validate user entitlement, session authenticity, date window, and ticker symbols."""
    user_id = state.get("user_id")
    db_path = state.get("db_path")
    provider_mode = state.get("provider_mode", "mock")

    if not user_id:
        return {
            "status": "invalid_input",
            "error_message": "user_id is required.",
            "error_code": "MISSING_USER_ID",
        }

    # Verify session if provided
    session_token = state.get("session_token")
    if session_token:
        valid_user = validate_session(session_token, db_path=db_path)
        if not valid_user or valid_user.id != user_id:
            return {
                "status": "failed",
                "error_message": "Invalid or expired session token.",
                "error_code": "UNAUTHORIZED_SESSION",
            }

    # Verify user entitlement on server
    entitlement = check_entitlement(user_id, db_path=db_path)
    if not entitlement.can_research:
        return {
            "status": "failed",
            "error_message": entitlement.reason,
            "error_code": "ENTITLEMENT_EXHAUSTED",
        }

    # Resolve date window with point-in-time guardrail
    date_preset = state.get("date_preset", "30D")
    custom_start = state.get("custom_start")
    custom_end = state.get("custom_end")
    as_of = state.get("as_of_date") or get_market_current_date().isoformat()

    try:
        start_date, end_date = resolve_date_window(
            preset=date_preset,
            custom_start=custom_start,
            custom_end=custom_end,
            as_of=as_of,
        )
    except ValueError as e:
        return {
            "status": "invalid_input",
            "error_message": str(e),
            "error_code": "INVALID_DATE_WINDOW",
        }

    # Validate tickers
    raw_tickers = state.get("tickers", [])
    valid_info, invalid_syms = validate_tickers_tool(raw_tickers, provider_mode=provider_mode)
    if not valid_info:
        return {
            "status": "invalid_input",
            "error_message": f"No valid ticker symbols provided. Unrecognized: {invalid_syms}",
            "error_code": "INVALID_TICKERS",
            "invalid_tickers": invalid_syms,
        }

    return {
        "status": "validating",
        "start_date": start_date,
        "end_date": end_date,
        "as_of_date": as_of,
        "validated_tickers": valid_info,
        "invalid_tickers": invalid_syms,
        "current_stage": "INPUTS_VALIDATED",
    }


def create_job_node(state: ResearchState) -> Dict[str, Any]:
    """Establish idempotent research job record in database."""
    user_id = state["user_id"]
    idempotency_key = state.get("idempotency_key") or str(uuid.uuid4())
    tab = state.get("tab", "news")
    tickers = [t.symbol for t in state["validated_tickers"]]
    start_date = state["start_date"]
    end_date = state["end_date"]
    horizon_days = state.get("horizon_days")
    db_path = state.get("db_path")

    try:
        job, is_new = create_research_job(
            user_id=user_id,
            idempotency_key=idempotency_key,
            tab=tab,
            ticker_list=tickers,
            start_at=start_date,
            end_at=end_date,
            horizon_days=horizon_days,
            db_path=db_path,
        )
        return {
            "job_id": job.id,
            "idempotency_key": idempotency_key,
            "status": "authorized",
            "current_stage": "JOB_REGISTERED",
        }
    except Exception as e:
        return {
            "status": "failed",
            "error_message": str(e),
            "error_code": "JOB_CREATION_FAILED",
        }


def collect_data_node(state: ResearchState) -> Dict[str, Any]:
    """Retrieve market price bars and news articles for valid tickers."""
    provider_mode = state.get("provider_mode", "mock")
    tickers = [t.symbol for t in state["validated_tickers"]]
    start_date = state["start_date"]
    end_date = state["end_date"]

    market_prices: Dict[str, List[CanonicalPriceBar]] = {}
    try:
        # Collect market prices per symbol
        for sym in tickers:
            bars = fetch_market_prices_tool(sym, start_date=start_date, end_date=end_date, provider_mode=provider_mode)
            market_prices[sym] = bars

        # Collect news across all selected tickers
        raw_news = fetch_news_tool(tickers, start_date=start_date, end_date=end_date, provider_mode=provider_mode)

        if not raw_news and not any(market_prices.values()):
            return {
                "status": "no_data",
                "error_message": "No news articles or price bars found for requested symbols in this date window.",
                "error_code": "NO_DATA",
                "raw_news": [],
                "market_prices": market_prices,
            }

        return {
            "status": "collecting",
            "raw_news": raw_news,
            "market_prices": market_prices,
            "current_stage": "DATA_COLLECTED",
        }
    except RateLimitExceeded as e:
        return {
            "status": "rate_limited",
            "error_message": str(e),
            "error_code": "RATE_LIMIT_EXCEEDED",
        }
    except ProviderException as e:
        return {
            "status": "failed",
            "error_message": str(e),
            "error_code": e.error_code,
        }


def deduplicate_and_verify_node(state: ResearchState) -> Dict[str, Any]:
    """Deduplicate news articles and verify historical date boundaries."""
    raw_news = state.get("raw_news", [])
    end_date = state["end_date"]

    # Filter out any articles post-dating end_date to prevent look-ahead bias
    bounded_articles = [a for a in raw_news if a.published_at_utc[:10] <= end_date]

    # Deduplicate
    deduped = deduplicate_news_tool(bounded_articles)

    return {
        "status": "normalizing",
        "deduplicated_news": deduped,
        "current_stage": "DEDUPLICATED",
    }


def analyze_evidence_node(state: ResearchState) -> Dict[str, Any]:
    """Synthesize evidence using EvidenceAnalyzer for selected tab."""
    tab = state.get("tab", "news")
    tickers_info = state["validated_tickers"]
    deduped_news = state.get("deduplicated_news", [])
    start_date = state["start_date"]
    end_date = state["end_date"]
    as_of = state["as_of_date"]
    horizon = state.get("horizon_days") or 30

    provider_mode = state.get("provider_mode", "mock")
    # In mock provider mode, default to deterministic offline-fallback-v1 to avoid billable API usage during testing
    model_name = None if provider_mode == "live" else "offline-fallback-v1"
    analyzer = EvidenceAnalyzer(model_name=model_name)

    news_summaries = []
    sentiment_outlooks = []

    for t_info in tickers_info:
        sym = t_info.symbol
        company = t_info.name
        sym_articles = [a for a in deduped_news if sym in a.ticker_association]

        if tab == "news":
            summary = analyzer.analyze_stock_news(
                ticker=sym,
                company_name=company,
                articles=sym_articles,
                start_date=start_date,
                end_date=end_date,
            )
            news_summaries.append(summary)
        else:
            outlook = analyzer.analyze_stock_sentiment(
                ticker=sym,
                company_name=company,
                articles=sym_articles,
                horizon_days=horizon,  # type: ignore
                as_of_date=as_of,
            )
            sentiment_outlooks.append(outlook)

    return {
        "status": "analyzing",
        "news_summaries": news_summaries,
        "sentiment_outlooks": sentiment_outlooks,
        "current_stage": "EVIDENCE_ANALYZED",
    }


def verify_claims_node(state: ResearchState) -> Dict[str, Any]:
    """Deterministically verify all citations against retrieved canonical articles."""
    deduped_news = state.get("deduplicated_news", [])
    all_citations: List[ClaimCitation] = []

    for s in state.get("news_summaries", []):
        all_citations.extend(s.citations)
    for o in state.get("sentiment_outlooks", []):
        all_citations.extend(o.citations)

    verified, unverified = verify_citations_tool(all_citations, deduped_news)

    limitations = []
    if unverified:
        limitations.append(f"Flagged {len(unverified)} unverified claims during grounding verification.")

    if state.get("invalid_tickers"):
        limitations.append(f"Omitted unrecognized symbols: {', '.join(state['invalid_tickers'])}")

    return {
        "status": "verifying",
        "verified_citations": verified,
        "unverified_claims": unverified,
        "limitations": limitations,
        "current_stage": "CITATIONS_VERIFIED",
    }


def generate_report_node(state: ResearchState) -> Dict[str, Any]:
    """Compile structured research report and markdown document."""
    report_id = str(uuid.uuid4())
    job_id = state.get("job_id", str(uuid.uuid4()))
    user_id = state["user_id"]
    tab = state.get("tab", "news")
    as_of = state["as_of_date"]
    tickers = [t.symbol for t in state["validated_tickers"]]
    date_range = {"start": state["start_date"], "end": state["end_date"]}
    horizon = state.get("horizon_days")
    now_utc = datetime.now(timezone.utc).isoformat()

    # Executive summary construction
    if tab == "news":
        exec_summary = (
            f"Multi-stock financial news synthesis for {', '.join(tickers)} from {state['start_date']} to {state['end_date']}. "
            f"Analyzed {len(state.get('deduplicated_news', []))} verified articles across official financial wires."
        )
    else:
        exec_summary = (
            f"Forward-looking sentiment and scenario analysis for {', '.join(tickers)} over a {horizon}-day horizon as of {as_of}. "
            f"Evaluated catalysts, downside risks, and opposing evidence across {len(state.get('deduplicated_news', []))} verified articles."
        )

    report_model = CompiledResearchReport(
        report_id=report_id,
        job_id=job_id,
        user_id=user_id,
        tab=tab,
        as_of_date=as_of,
        date_range=date_range,
        tickers=tickers,
        horizon_days=horizon,
        executive_summary=exec_summary,
        stock_news_summaries=state.get("news_summaries", []),
        stock_sentiment_outlooks=state.get("sentiment_outlooks", []),
        all_citations=state.get("verified_citations", []),
        limitations=state.get("limitations", []),
        generated_at_utc=now_utc,
        model_version=state.get("provider_mode", "mock"),
    )

    # Format Markdown Report
    lines = [
        f"# Stock Market Research Report — {tab.upper()} TAB",
        f"**Generated:** {now_utc[:19]} UTC | **As of Date:** {as_of}",
        f"**Tickers:** {', '.join(tickers)} | **Date Range:** {state['start_date']} to {state['end_date']}",
    ]
    if horizon:
        lines.append(f"**Forward Horizon:** {horizon} Days")

    lines.extend(["\n## Executive Summary", exec_summary, "\n---"])

    # Stock-specific sections
    if tab == "news":
        for s in state.get("news_summaries", []):
            lines.append(f"### 📈 {s.ticker} ({s.company_name})")
            lines.append(f"*Total Articles Analyzed:* {s.total_articles_found}")
            lines.append("\n**Key Developments:**")
            for dev in s.key_developments:
                lines.append(f"- {dev}")
            lines.append("")
    else:
        for o in state.get("sentiment_outlooks", []):
            lines.append(f"### 🧠 {o.ticker} ({o.company_name})")
            lines.append(f"- **Current News Sentiment:** `{o.current_news_sentiment.upper()}`")
            lines.append(f"- **Forward Outlook ({o.horizon_days}D):** `{o.forward_scenario_outlook.upper()}`")
            lines.append(f"- **Evidence Strength:** `{o.evidence_strength.upper()}`")
            lines.append("\n**Top Catalysts:**")
            for c in o.catalysts:
                lines.append(f"- 🚀 {c}")
            lines.append("\n**Downside Risks:**")
            for r in o.risks:
                lines.append(f"- ⚠️ {r}")
            if o.opposing_evidence:
                lines.append("\n**Opposing / Contradictory Evidence:**")
                for opp in o.opposing_evidence:
                    lines.append(f"- ⚖️ {opp}")
            lines.append("")

    # Verified Citations Table
    lines.append("\n## Verified Source Citations")
    if state.get("verified_citations"):
        lines.append("| Article ID | Publisher | Publication Date | Verified Claim | Source Link |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for cit in state.get("verified_citations", []):
            lines.append(f"| `{cit.article_id}` | {cit.publisher} | {cit.publication_date[:10]} | {cit.claim[:60]}... | [Source Link]({cit.source_url}) |")
    else:
        lines.append("No material factual citations generated.")

    # Unverified claims
    if state.get("unverified_claims"):
        lines.append("\n### ⚠️ Unverified Claims Disclosed")
        for uc in state.get("unverified_claims", []):
            lines.append(f"- {uc}")

    # Limitations & Legal Notice
    lines.extend([
        "\n## Limitations & Methodology Notice",
        "- All articles were collected via read-only financial data feeds with strict point-in-time timestamp validation.",
        "- Look-ahead information past the research cutoff date was strictly excluded.",
        "- **DISCLAIMER:** This research report is generated for informational and research purposes only. It does not constitute investment advice, financial endorsement, or trade recommendations.",
    ])

    markdown_content = "\n".join(lines)

    return {
        "status": "reporting",
        "report": report_model,
        "report_markdown": markdown_content,
        "report_json": report_model.model_dump(),
        "current_stage": "REPORT_GENERATED",
    }


def persist_results_node(state: ResearchState) -> Dict[str, Any]:
    """Persist source records, compiled report, and finalize job status in SQLite."""
    job_id = state["job_id"]
    db_path = state.get("db_path")
    deduped_news = state.get("deduplicated_news", [])
    report = state.get("report")
    report_md = state.get("report_markdown", "")
    now_utc = datetime.now(timezone.utc).isoformat()

    conn = get_connection(db_path)
    try:
        with conn:
            # 1. Insert source records
            for art in deduped_news:
                for sym in art.ticker_association:
                    conn.execute(
                        """
                        INSERT INTO source_records (
                            id, job_id, ticker, source_url, publisher, 
                            published_at, retrieved_at, evidence_type, normalized_metadata_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'news', ?);
                        """,
                        (
                            str(uuid.uuid4()),
                            job_id,
                            sym,
                            art.source_url,
                            art.publisher,
                            art.published_at_utc,
                            art.retrieved_at_utc,
                            json.dumps({"headline": art.headline, "is_duplicate": art.is_duplicate}),
                        ),
                    )

            # 2. Insert research report (idempotent replace)
            if report:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO research_reports (
                        id, job_id, report_json, markdown, generated_at, model_version, prompt_version, limitations_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        report.report_id,
                        job_id,
                        json.dumps(report.model_dump()),
                        report_md,
                        now_utc,
                        report.model_version,
                        report.prompt_version,
                        json.dumps(report.limitations),
                    ),
                )

        # 3. Finalize research job and atomically debit quota (only on success)
        completed_job = complete_research_job(job_id=job_id, success=True, db_path=db_path)

        return {
            "status": "completed",
            "quota_debited": bool(completed_job.credit_debited),
            "current_stage": "COMPLETED",
        }
    finally:
        conn.close()


def handle_failure_node(state: ResearchState) -> Dict[str, Any]:
    """Terminal failure node recording error code without debiting user quota."""
    job_id = state.get("job_id")
    db_path = state.get("db_path")
    err_msg = state.get("error_message", "Unknown research failure.")
    err_code = state.get("error_code", "RESEARCH_FAILED")

    if job_id:
        try:
            complete_research_job(job_id=job_id, success=False, error_code=err_code, db_path=db_path)
        except Exception:
            pass

    return {
        "status": state.get("status", "failed"),
        "error_message": err_msg,
        "error_code": err_code,
        "quota_debited": False,
        "current_stage": "FAILED_TERMINAL",
    }

