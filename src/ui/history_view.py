"""Research history view displaying search, filters, saved reports, reopen actions, and multi-format exports."""
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


def render_history_view(user) -> None:
    """Render historical research jobs, multi-field filters, pagination, and export tools."""
    st.subheader("🕒 Research History & Saved Reports")
    st.caption("Search past research jobs, reopen previous sessions without consuming credits, and export reports in Markdown, JSON, CSV, or PDF.")

    # 1. Search and Filtering Controls
    with st.container(border=True):
        st.markdown("##### 🔍 Search & Filter Research History")
        f_row1_col1, f_row1_col2, f_row1_col3 = st.columns([3, 2, 2])

        with f_row1_col1:
            keyword = st.text_input(
                "Keyword Search",
                placeholder="Search summaries, findings, or company developments...",
                key="history_search_keyword",
            )

        with f_row1_col2:
            ticker_filter = st.text_input(
                "Filter by Ticker Symbol",
                placeholder="e.g. AAPL, NVDA (Leave blank for all)",
                key="history_ticker_filter",
            )

        with f_row1_col3:
            tab_filter = st.selectbox(
                "Research Mode",
                options=["All Modes", "News", "Sentiment"],
                index=0,
                key="history_tab_filter",
            )

        f_row2_col1, f_row2_col2, f_row2_col3 = st.columns([2, 2, 3])
        with f_row2_col1:
            status_filter = st.selectbox(
                "Job Status",
                options=["All Statuses", "Completed", "Failed"],
                index=0,
                key="history_status_filter",
            )
        with f_row2_col2:
            page_size = st.selectbox(
                "Reports per Page",
                options=[5, 10, 20],
                index=0,
                key="history_page_size",
            )
        with f_row2_col3:
            st.caption("Filter Actions")
            reset_filters = st.button("Reset Filters", width="stretch", key="history_reset_btn")
            if reset_filters:
                st.session_state["history_search_keyword"] = ""
                st.session_state["history_ticker_filter"] = ""
                st.session_state["history_tab_filter"] = "All Modes"
                st.session_state["history_status_filter"] = "All Statuses"
                st.session_state["history_current_page"] = 1
                st.rerun()

    # Pagination state
    if "history_current_page" not in st.session_state:
        st.session_state["history_current_page"] = 1

    current_page = st.session_state["history_current_page"]

    # Query filtered history
    clean_tab = tab_filter.lower() if tab_filter in ("News", "Sentiment") else None
    clean_status = status_filter.lower() if status_filter in ("Completed", "Failed") else None

    jobs, total_matching = query_user_research_history(
        user_id=user.id,
        ticker=ticker_filter.strip() if ticker_filter else None,
        tab_type=clean_tab,
        status_filter=clean_status,
        keyword=keyword.strip() if keyword else None,
        page=current_page,
        page_size=page_size,
    )

    total_pages = max(1, math.ceil(total_matching / page_size))
    if current_page > total_pages:
        st.session_state["history_current_page"] = total_pages
        current_page = total_pages

    # 2. Results Header & Pagination Navigation
    col_count, col_pnav = st.columns([3, 2])
    with col_count:
        st.markdown(f"**Found {total_matching} Matching Research Reports** (Page {current_page} of {total_pages})")
    with col_pnav:
        p_prev, p_page_txt, p_next = st.columns([1, 2, 1])
        with p_prev:
            if st.button("◀ Prev", disabled=current_page <= 1, width="stretch", key="p_prev_btn"):
                st.session_state["history_current_page"] -= 1
                st.rerun()
        with p_page_txt:
            st.markdown(f"<div style='text-align: center; padding-top: 5px; color: #64748B;'>Page {current_page} / {total_pages}</div>", unsafe_allow_html=True)
        with p_next:
            if st.button("Next ▶", disabled=current_page >= total_pages, width="stretch", key="p_next_btn"):
                st.session_state["history_current_page"] += 1
                st.rerun()

    if not jobs:
        st.info("No research reports match your search criteria. Try modifying your filter parameters or search keyword.")
        return

    # 3. Report Cards
    for job in jobs:
        status_color = "#10B981" if job["status"] == "completed" else "#EF4444"
        badge_text = "COMPLETED" if job["status"] == "completed" else job["status"].upper()

        with st.container(border=True):
            col_meta, col_stat, col_actions = st.columns([3, 2, 3])

            with col_meta:
                tickers_str = ", ".join(job["tickers"])
                st.markdown(f"#### 🏷️ **{tickers_str}**")
                st.caption(f"Mode: `{job['tab'].upper()}` · Window: `{job['start_at']} to {job['end_at']}`")
                if job.get("horizon_days"):
                    st.caption(f"Forward Horizon: `{job['horizon_days']} Days`")

            with col_stat:
                st.markdown(
                    f"<span style='color: {status_color}; font-weight: 700;'>● {badge_text}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(f"Job ID: `{job['id'][:8]}...`")
                st.caption(f"Executed: {job['created_at'][:19]} UTC")
                credit_label = "1 Credit Debited" if job["credit_debited"] else "0 Credits (Protected)"
                st.caption(f"Quota: {credit_label}")

            with col_actions:
                # Reopen Button (Restores session state without re-running or debiting credit)
                reopen_clicked = st.button(
                    "📂 Reopen in Dashboard",
                    key=f"reopen_{job['id']}",
                    width="stretch",
                    help="Restore this research report to the active Dashboard tabs without re-running or debiting credits.",
                )
                if reopen_clicked:
                    st.session_state["selected_tickers"] = job["tickers"]
                    st.session_state["date_preset"] = "Custom"
                    st.session_state["custom_start"] = job["start_at"]
                    st.session_state["custom_end"] = job["end_at"]
                    if job.get("horizon_days"):
                        st.session_state["horizon_days"] = job["horizon_days"]

                    # Populate cache key so active tab immediately loads without re-running
                    cache_key = f"{job['tab']}_{','.join(sorted(job['tickers']))}_Custom_{job['start_at']}_{job['end_at']}_{job.get('horizon_days')}"
                    rep_payload = job.get("report_json", {})
                    # Reconstruct lightweight research state
                    reconstructed_state = {
                        "job_id": job["id"],
                        "status": job["status"],
                        "tab": job["tab"],
                        "tickers": job["tickers"],
                        "start_date": job["start_at"],
                        "end_date": job["end_at"],
                        "horizon_days": job.get("horizon_days"),
                        "report_markdown": job.get("markdown", ""),
                        "report_json": rep_payload,
                        "report": None,
                        "news_summaries": [],
                        "sentiment_outlooks": [],
                        "verified_citations": [],
                        "deduplicated_news": [],
                        "market_prices": {},
                    }
                    st.session_state["research_results"][cache_key] = reconstructed_state
                    st.session_state["sidebar_navigation_radio"] = "📊 Research Dashboard"
                    st.toast(f"✅ Reopened {tickers_str} in Dashboard without quota deduction!", icon="📂")
                    st.rerun()

                # Multi-Format Export Buttons
                with st.popover("📥 Export Report", width="stretch"):
                    st.markdown("**Download Report in Desired Format:**")

                    # Markdown Download
                    md_text = export_to_markdown(job)
                    st.download_button(
                        label="📄 Download Markdown (.md)",
                        data=md_text,
                        file_name=f"report_{job['id'][:8]}_{job['tab']}.md",
                        mime="text/markdown",
                        key=f"dl_md_{job['id']}",
                        width="stretch",
                    )

                    # JSON Download
                    json_str = export_to_json(job)
                    st.download_button(
                        label="📦 Download JSON (.json)",
                        data=json_str,
                        file_name=f"report_{job['id'][:8]}_{job['tab']}.json",
                        mime="application/json",
                        key=f"dl_json_{job['id']}",
                        width="stretch",
                    )

                    # CSV Download
                    csv_str = export_to_csv(job)
                    st.download_button(
                        label="📊 Download CSV (.csv)",
                        data=csv_str,
                        file_name=f"report_{job['id'][:8]}_{job['tab']}.csv",
                        mime="text/csv",
                        key=f"dl_csv_{job['id']}",
                        width="stretch",
                    )

                    # PDF Download
                    try:
                        pdf_bytes = export_to_pdf(job)
                        st.download_button(
                            label="📕 Download PDF (.pdf)",
                            data=pdf_bytes,
                            file_name=f"report_{job['id'][:8]}_{job['tab']}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{job['id']}",
                            width="stretch",
                        )
                    except Exception as err:
                        st.caption(f"PDF export notice: {err}")

            # Expandable Report Viewer
            if job.get("markdown"):
                with st.expander(f"View Full Report — {tickers_str} ({job['created_at'][:10]})"):
                    st.markdown(job["markdown"])
            elif job.get("error_code"):
                with st.expander("View Failure Diagnostic"):
                    st.error(f"Error Code: {job['error_code']}")
                    st.caption("No credits debited.")
