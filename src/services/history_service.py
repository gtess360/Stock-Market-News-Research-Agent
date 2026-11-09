"""Research history query, search, filtering, and user ownership isolation service."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from src.database.connection import get_connection


def query_user_research_history(
    user_id: str,
    ticker: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tab_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 5,
    db_path: Optional[Path | str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Query paginated research history strictly scoped to the requesting user.
    
    Returns:
        Tuple[List[Dict], int]: (page_records, total_matching_count)
    """
    if not user_id:
        return [], 0

    base_conditions = ["j.user_id = ?"]
    params: List[Any] = [user_id]

    # 1. Ticker Filter
    if ticker and ticker.strip() and ticker.strip().upper() != "ALL":
        clean_ticker = ticker.strip().upper()
        base_conditions.append("j.ticker_list_json LIKE ?")
        params.append(f'%"{clean_ticker}"%')

    # 2. Date Range Filters
    if start_date:
        base_conditions.append("j.start_at >= ?")
        params.append(start_date)
    if end_date:
        base_conditions.append("j.end_at <= ?")
        params.append(end_date)

    # 3. Tab Type Filter (news vs sentiment)
    if tab_type and tab_type.lower() in ("news", "sentiment"):
        base_conditions.append("j.tab = ?")
        params.append(tab_type.lower())

    # 4. Status Filter
    if status_filter and status_filter.lower() in ("completed", "failed", "requested"):
        base_conditions.append("j.status = ?")
        params.append(status_filter.lower())

    # 5. Keyword Search across markdown, report json, and ticker list
    if keyword and keyword.strip():
        search_kw = f"%{keyword.strip().lower()}%"
        base_conditions.append(
            "(LOWER(COALESCE(r.markdown, '')) LIKE ? OR "
            "LOWER(COALESCE(r.report_json, '')) LIKE ? OR "
            "LOWER(j.ticker_list_json) LIKE ?)"
        )
        params.extend([search_kw, search_kw, search_kw])

    where_clause = " WHERE " + " AND ".join(base_conditions)

    conn = get_connection(db_path)
    try:
        # Count total matching records
        count_sql = f"""
            SELECT COUNT(DISTINCT j.id) as total
            FROM research_jobs j
            LEFT JOIN research_reports r ON j.id = r.job_id
            {where_clause};
        """
        count_row = conn.execute(count_sql, params).fetchone()
        total_count = count_row["total"] if count_row else 0

        if total_count == 0:
            return [], 0

        # Query paginated page records
        offset = max(0, (page - 1) * page_size)
        query_sql = f"""
            SELECT j.id, j.user_id, j.idempotency_key, j.tab, j.ticker_list_json,
                   j.start_at, j.end_at, j.horizon_days, j.status, j.created_at,
                   j.completed_at, j.error_code, j.credit_debited,
                   r.markdown, r.report_json, r.generated_at, r.model_version
            FROM research_jobs j
            LEFT JOIN research_reports r ON j.id = r.job_id
            {where_clause}
            ORDER BY j.created_at DESC
            LIMIT ? OFFSET ?;
        """
        page_params = list(params) + [page_size, offset]
        rows = conn.execute(query_sql, page_params).fetchall()

        records = []
        for r in rows:
            rep_dict = json.loads(r["report_json"]) if r["report_json"] else {}
            records.append({
                "id": r["id"],
                "user_id": r["user_id"],
                "tab": r["tab"],
                "tickers": json.loads(r["ticker_list_json"]),
                "start_at": r["start_at"],
                "end_at": r["end_at"],
                "horizon_days": r["horizon_days"],
                "status": r["status"],
                "created_at": r["created_at"],
                "completed_at": r["completed_at"],
                "error_code": r["error_code"],
                "credit_debited": bool(r["credit_debited"]),
                "markdown": r["markdown"] or "",
                "report_json": rep_dict,
                "generated_at": r["generated_at"],
                "model_version": r["model_version"],
            })
        return records, total_count
    finally:
        conn.close()


def get_user_job_detail(
    user_id: str,
    job_id: str,
    db_path: Optional[Path | str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve full details of a single research job with strict ownership verification."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT j.id, j.user_id, j.idempotency_key, j.tab, j.ticker_list_json,
                   j.start_at, j.end_at, j.horizon_days, j.status, j.created_at,
                   j.completed_at, j.error_code, j.credit_debited,
                   r.markdown, r.report_json, r.generated_at, r.model_version
            FROM research_jobs j
            LEFT JOIN research_reports r ON j.id = r.job_id
            WHERE j.id = ? AND j.user_id = ?;
            """,
            (job_id, user_id),
        ).fetchone()

        if not row:
            return None

        # Fetch source records
        src_rows = conn.execute(
            """
            SELECT id, ticker, source_url, publisher, published_at, evidence_type, normalized_metadata_json
            FROM source_records
            WHERE job_id = ?
            ORDER BY published_at DESC;
            """,
            (job_id,),
        ).fetchall()

        sources = []
        for s in src_rows:
            meta = json.loads(s["normalized_metadata_json"]) if s["normalized_metadata_json"] else {}
            sources.append({
                "id": s["id"],
                "ticker": s["ticker"],
                "source_url": s["source_url"],
                "publisher": s["publisher"],
                "published_at": s["published_at"],
                "evidence_type": s["evidence_type"],
                "headline": meta.get("headline", ""),
                "is_duplicate": meta.get("is_duplicate", False),
            })

        rep_dict = json.loads(row["report_json"]) if row["report_json"] else {}

        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "tab": row["tab"],
            "tickers": json.loads(row["ticker_list_json"]),
            "start_at": row["start_at"],
            "end_at": row["end_at"],
            "horizon_days": row["horizon_days"],
            "status": row["status"],
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
            "error_code": row["error_code"],
            "credit_debited": bool(row["credit_debited"]),
            "markdown": row["markdown"] or "",
            "report_json": rep_dict,
            "generated_at": row["generated_at"],
            "model_version": row["model_version"],
            "sources": sources,
        }
    finally:
        conn.close()

