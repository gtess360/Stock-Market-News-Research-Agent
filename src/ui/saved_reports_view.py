"""Dedicated Saved Reports view displaying curated completed reports, previews, and instant multi-format downloads."""
import json
import math
from typing import Any, Dict
import streamlit as st
from src.services.export_service import (
    export_to_csv,
    export_to_json,
    export_to_markdown,
    export_to_pdf,
)
from src.services.history_service import query_user_research_history


def render_saved_reports_view(user) -> None:
    """Render curated saved research reports repository with instant multi-format exports."""
    st.subheader("📑 Saved Research Reports")
    st.caption("Access and export all completed financial research reports. Download in PDF, Markdown, JSON, or CSV, or reopen in the active dashboard.")

    # 1. Search & Filter Bar
    with st.container(border=True):
        col_search, col_ticker, col_tab = st.columns([3, 2, 2])
        with col_search:
            keyword = st.text_input(
                "Search Reports",
                placeholder="Search key developments, executive summaries...",
                key="saved_reports_search_input",
            )
        with col_ticker:
            ticker = st.text_input(
                "Filter by Ticker",
                placeholder="e.g. AAPL, NVDA",
                key="saved_reports_ticker_input",
            )
        with col_tab:
            report_mode = st.selectbox(
                "Report Type",
                options=["All Reports", "Stock News Reports", "Sentiment Reports"],
                key="saved_reports_mode_select",
            )

    tab_filter = None
    if report_mode == "Stock News Reports":
        tab_filter = "news"
    elif report_mode == "Sentiment Reports":
        tab_filter = "sentiment"

    # Query completed reports only
    records, total_count = query_user_research_history(
        user_id=user.id,
        ticker=ticker if ticker else None,
        tab_type=tab_filter,
        status_filter="completed",
        keyword=keyword if keyword else None,
        page=1,
        page_size=50,
    )

    # Filter records that have report content
    saved_records = [r for r in records if r.get("has_report")]

    if not saved_records:
        st.info("ℹ️ No saved research reports match your criteria. Launch research from the Dashboard to generate and save reports.")
        return

    st.markdown(f"**Found {len(saved_records)} saved report(s):**")

    # 2. Render Report Cards
    for rec in saved_records:
        tickers = rec.get("tickers", [])
        tab_name = "📰 Stock News" if rec.get("tab") == "news" else "🧠 Forward Sentiment"
        completed_date = rec.get("completed_at", rec.get("created_at", ""))[:16].replace("T", " ")
        summary_text = rec.get("summary_snippet") or "Financial research report generated with grounded market evidence."

        with st.container(border=True):
            col_info, col_actions = st.columns([5, 3])

            with col_info:
                # Ticker badges
                ticker_badges = " ".join([f"`{t}`" for t in tickers])
                st.markdown(f"### {tab_name} Analysis — {ticker_badges}")
                st.caption(f"🗓️ Window: **{rec.get('start_at')}** to **{rec.get('end_at')}** · Completed: **{completed_date} UTC**")
                st.markdown(f"> *{summary_text}*")

                meta_col1, meta_col2 = st.columns(2)
                with meta_col1:
                    st.caption(f"📚 Verified Sources: **{rec.get('source_count', 0)}**")
                with meta_col2:
                    if rec.get("horizon_days"):
                        st.caption(f"🎯 Forecast Horizon: **{rec.get('horizon_days')} Days**")

            with col_actions:
                st.markdown("**Download Report**")
                btn_c1, btn_c2 = st.columns(2)

                # Export downloads
                report_dict = rec.get("report_json") or {}
                raw_md = rec.get("report_markdown") or ""

                with btn_c1:
                    pdf_bytes = export_to_pdf(rec)
                    st.download_button(
                        "📥 PDF",
                        data=pdf_bytes,
                        file_name=f"Report_{rec['id'][:8]}.pdf",
                        mime="application/pdf",
                        key=f"saved_pdf_{rec['id']}",
                        use_container_width=True,
                    )
                    json_str = export_to_json(rec)
                    st.download_button(
                        "📥 JSON",
                        data=json_str,
                        file_name=f"Report_{rec['id'][:8]}.json",
                        mime="application/json",
                        key=f"saved_json_{rec['id']}",
                        use_container_width=True,
                    )

                with btn_c2:
                    md_str = export_to_markdown(rec)
                    st.download_button(
                        "📥 Markdown",
                        data=md_str,
                        file_name=f"Report_{rec['id'][:8]}.md",
                        mime="text/markdown",
                        key=f"saved_md_{rec['id']}",
                        use_container_width=True,
                    )
                    csv_str = export_to_csv(rec)
                    st.download_button(
                        "📥 CSV",
                        data=csv_str,
                        file_name=f"Report_{rec['id'][:8]}.csv",
                        mime="text/csv",
                        key=f"saved_csv_{rec['id']}",
                        use_container_width=True,
                    )

                # Reopen Report in Session
                if st.button("🔄 Reopen Report", key=f"reopen_btn_{rec['id']}", use_container_width=True):
                    st.session_state["selected_tickers"] = tickers
                    st.session_state["date_preset"] = "Custom"
                    st.session_state["custom_start"] = rec.get("start_at")
                    st.session_state["custom_end"] = rec.get("end_at")
                    if rec.get("horizon_days"):
                        st.session_state["horizon_days"] = rec.get("horizon_days")

                    # Reconstruct research result
                    cache_key = f"{rec.get('tab')}_{','.join(sorted(tickers))}_Custom_{rec.get('start_at')}_{rec.get('end_at')}_{rec.get('horizon_days')}"
                    reopened_result = {
                        "status": "completed",
                        "tab": rec.get("tab"),
                        "validated_tickers": [],
                        "market_prices": {},
                        "deduplicated_news": [],
                        "news_summaries": [],
                        "sentiment_outlooks": [],
                        "verified_citations": [],
                        "unverified_claims": [],
                        "limitations": [],
                        "report": None,
                        "report_markdown": raw_md,
                        "report_json": report_dict,
                    }
                    st.session_state["research_results"][cache_key] = reopened_result
                    st.session_state["active_nav_view"] = "dashboard"
                    st.success("Report reopened! Navigating to Dashboard...")
                    st.rerun()

