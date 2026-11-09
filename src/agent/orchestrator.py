"""Research orchestrator entry point invoking the compiled LangGraph workflow."""
import uuid
from typing import Any, Dict, List, Literal, Optional
from src.agent.graph import research_graph
from src.agent.state import ResearchState


def run_research_workflow(
    user_id: str,
    tab: Literal["news", "sentiment"],
    tickers: List[str],
    date_preset: str = "30D",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    horizon_days: Optional[Literal[1, 7, 30, 90]] = None,
    as_of_date: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    session_token: Optional[str] = None,
    db_path: Optional[str] = None,
    provider_mode: str = "mock",
) -> ResearchState:
    """Execute the end-to-end bounded research workflow via LangGraph."""
    initial_state: ResearchState = {
        "user_id": user_id,
        "session_token": session_token,
        "job_id": "",
        "idempotency_key": idempotency_key or str(uuid.uuid4()),
        "tab": tab,
        "tickers": tickers,
        "date_preset": date_preset,
        "custom_start": custom_start,
        "custom_end": custom_end,
        "start_date": "",
        "end_date": "",
        "horizon_days": horizon_days,
        "as_of_date": as_of_date or "",
        "db_path": db_path,
        "provider_mode": provider_mode,
        "current_stage": "INITIALIZED",
        "status": "requested",
        "error_message": None,
        "error_code": None,
        "quota_debited": False,
        "validated_tickers": [],
        "invalid_tickers": [],
        "raw_news": [],
        "deduplicated_news": [],
        "market_prices": {},
        "news_summaries": [],
        "sentiment_outlooks": [],
        "verified_citations": [],
        "unverified_claims": [],
        "limitations": [],
        "report": None,
        "report_markdown": "",
        "report_json": {},
    }

    final_state = research_graph.invoke(initial_state)
    return final_state
