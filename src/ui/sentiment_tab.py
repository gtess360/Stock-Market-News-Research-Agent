"""Sentiment Research tab view rendering scenario cards, catalysts, risks, and forward horizon outlooks."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import streamlit as st
from src.services.export_service import (
    export_to_csv,
    export_to_json,
    export_to_markdown,
    export_to_pdf,
)
from src.ui.charts import (
    create_multi_stock_sentiment_comparison_chart,
    create_sentiment_timeline_chart,
)


def get_sentiment_badge_html(sentiment: str) -> str:
    """Format sentiment badge with semantic colors."""
    s = sentiment.lower()
    if s in ("bullish", "positive"):
        return '<span class="sentiment-badge-bullish">🟢 BULLISH</span>'
    elif s in ("bearish", "negative"):
        return '<span class="sentiment-badge-bearish">🔴 BEARISH</span>'
    elif s == "neutral":
        return '<span class="sentiment-badge-neutral">⚪ NEUTRAL</span>'
    else:
        return '<span class="sentiment-badge-mixed">🟡 MIXED</span>'


def render_sentiment_tab(
    research_state: Optional[Dict[str, Any]],
    provider_mode: str = "mock",
) -> None:
    """Render the enhanced Sentiment Research Workbench."""
    # Provider Notice Header
    if provider_mode == "mock":
        st.markdown(
            '<div style="margin-bottom: 1rem;"><span class="badge-mock">Mock Provider Active</span> <small style="color: #64748B;">Offline deterministic financial fixtures for testing.</small></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="margin-bottom: 1rem;"><span class="badge-live">Live Market Feeds Active</span> <small style="color: #64748B;">Real-time Finnhub news & Alpha Vantage feeds.</small></div>',
            unsafe_allow_html=True,
        )

    if not research_state or research_state.get("status") not in ("completed", "failed") or research_state.get("tab") != "sentiment":
        st.info(
            "👉 Configure your selected stock tickers and date window above, select your desired "
            "**Forward Scenario Horizon**, then click **'🚀 Launch Research'** to evaluate catalysts, risks, and forward scenario sentiment."
        )
        return

    if research_state.get("status") == "failed":
        st.error(
            f"**Sentiment Research Error ({research_state.get('error_code')}):** {research_state.get('error_message')}"
        )
        st.caption("Your free quota was protected; 0 credits were debited.")
        return

    # Forward Horizon Banner & Lens Explanation
    horizon = research_state.get("horizon_days", 30)
    horizon_desc = {
        1: "Immediate 24-hour tactical reaction to recent announcements and headline volatility.",
        7: "Short-term 7-day momentum and corporate event follow-through.",
        30: "Monthly 30-day scenario outlook balancing operational catalysts with macro headwinds.",
        90: "Quarterly 90-day strategic horizon assessing multi-month earnings delivery and pipeline traction.",
    }.get(horizon, "Scenario modeling horizon.")

    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1.1rem 1.35rem; margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 1.15rem; font-weight: 700; color: #0B192C;">Forward Scenario Horizon: {horizon} Days</span><br>
                    <small style="color: #64748B;"><b>Analysis Lens:</b> {horizon_desc} (Reference date: {research_state.get('as_of_date')})</small>
                </div>
                <div>
                    <span class="badge-unlimited">{horizon}D Horizon</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    outlooks = research_state.get("sentiment_outlooks", [])
    if not outlooks:
        st.warning("No sentiment outlooks could be synthesized from available evidence.")
        return

    # 1. Multi-Stock Scenario Comparison Section
    if len(outlooks) > 1:
        st.markdown("### 📊 Multi-Stock Comparative Sentiment Matrix")
        comp_fig = create_multi_stock_sentiment_comparison_chart(outlooks)
        if comp_fig:
            st.plotly_chart(comp_fig, width="stretch")

        comp_rows = []
        for o in outlooks:
            metrics = getattr(o, "transparency_metrics", None)
            comp_rows.append({
                "Ticker": o.ticker,
                "Company": o.company_name,
                "Historical News Sentiment": o.current_news_sentiment.upper(),
                f"Forward Outlook ({o.horizon_days}D)": o.forward_scenario_outlook.upper(),
                "Net Sentiment Score": f"{getattr(o, 'net_sentiment_score', 0.0):+.2f}",
                "Evidence Strength": o.evidence_strength.upper(),
                "Catalysts": len(o.catalysts),
                "Risks": len(o.risks),
                "Source Diversity": metrics.source_diversity_rating.upper() if metrics else "N/A",
            })
        st.dataframe(comp_rows, width="stretch", hide_index=True)
        st.markdown("---")

    # 2. Detailed Per-Stock Scenario Analysis
    st.markdown("### 🧠 In-Depth Scenario Analysis & Catalyst Breakdown")
    for o in outlooks:
        with st.container(border=True):
            col_hdr_left, col_hdr_right = st.columns([3, 2])
            with col_hdr_left:
                st.markdown(f"#### {o.ticker} — {o.company_name}")
                st.caption(
                    f"Evidence Strength: **{o.evidence_strength.upper()}** · "
                    f"Net Score: **{getattr(o, 'net_sentiment_score', 0.0):+.2f}** · "
                    f"Forward Horizon: **{o.horizon_days} Days**"
                )
            with col_hdr_right:
                badge_html = (
                    f"<div style='text-align: right;'>"
                    f"<span style='color: #64748B; font-size: 0.8rem;'>Historical:</span> {get_sentiment_badge_html(o.current_news_sentiment)} &nbsp; "
                    f"<span style='color: #64748B; font-size: 0.8rem;'>Forward:</span> {get_sentiment_badge_html(o.forward_scenario_outlook)}"
                    f"</div>"
                )
                st.markdown(badge_html, unsafe_allow_html=True)

            st.markdown("---")

            # Historical News Sentiment Trajectory Plot
            timeline_pts = getattr(o, "sentiment_timeline", [])
            if timeline_pts:
                t_fig = create_sentiment_timeline_chart(timeline_pts, o.ticker)
                st.plotly_chart(t_fig, width="stretch")

            # Evidence Transparency & Diversity Card
            metrics = getattr(o, "transparency_metrics", None)
            if metrics:
                with st.container(border=True):
                    st.markdown("##### 🔍 Evidence Grounding & Source Diversity")
                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                    with m_col1:
                        st.metric("Total Articles", metrics.total_articles_evaluated)
                    with m_col2:
                        st.metric("Unique Publishers", metrics.unique_publishers_count)
                    with m_col3:
                        st.metric("Deduplicated Wire Copies", metrics.syndicated_duplicates_filtered)
                    with m_col4:
                        st.metric("Source Diversity", metrics.source_diversity_rating.upper())

                    pub_list = ", ".join(metrics.unique_publishers) if metrics.unique_publishers else "None"
                    st.caption(f"**Contributing Publishers:** {pub_list}")
                    st.caption(f"**Recency Breakdown:** {metrics.recency_last_7d_count} within last 7 days · {metrics.recency_older_count} older")

            st.markdown("---")

            # Catalysts, Risks, Opposing Evidence Grid
            col_cat, col_risk, col_opp = st.columns(3)

            with col_cat:
                st.markdown("##### 🚀 Top Positive Catalysts")
                weighted_cats = getattr(o, "weighted_catalysts", [])
                if weighted_cats:
                    for wc in weighted_cats:
                        st.markdown(
                            f"- **{wc.factor_text}**  \n"
                            f"  <small style='color: #10B981;'>[{wc.impact_weight.upper()} IMPACT] · [{wc.time_horizon.upper()}]</small>",
                            unsafe_allow_html=True,
                        )
                elif o.catalysts:
                    for c in o.catalysts:
                        st.markdown(f"- {c}")
                else:
                    st.caption("No positive catalysts detected.")

            with col_risk:
                st.markdown("##### ⚠️ Downside Risks & Headwinds")
                weighted_rs = getattr(o, "weighted_risks", [])
                if weighted_rs:
                    for wr in weighted_rs:
                        st.markdown(
                            f"- **{wr.factor_text}**  \n"
                            f"  <small style='color: #EF4444;'>[{wr.impact_weight.upper()} HEADWIND] · [{wr.time_horizon.upper()}]</small>",
                            unsafe_allow_html=True,
                        )
                elif o.risks:
                    for r in o.risks:
                        st.markdown(f"- {r}")
                else:
                    st.caption("No material downside risks detected.")

            with col_opp:
                st.markdown("##### ⚖️ Opposing / Counter-Evidence")
                weighted_opp = getattr(o, "weighted_opposing", [])
                if weighted_opp:
                    for wo in weighted_opp:
                        st.markdown(f"- ⚖️ **{wo.factor_text}** ({wo.impact_weight.upper()})")
                elif o.opposing_evidence:
                    for opp in o.opposing_evidence:
                        st.markdown(f"- ⚖️ {opp}")
                else:
                    st.caption("No conflicting counter-narratives identified.")

            # Scenario Triggers: What could change this outlook?
            triggers = getattr(o, "scenario_triggers", [])
            if triggers:
                with st.expander(f"🔄 Scenario Sensitivity: What could alter the {o.ticker} outlook?"):
                    for tr in triggers:
                        st.markdown(f"- ⚡ {tr}")

    st.markdown("---")

    # 3. Verified Citations Section
    st.markdown("### 🔍 Grounded Source Citations")
    citations = research_state.get("verified_citations", [])
    if citations:
        c_table = [
            {
                "Article ID": c.article_id,
                "Publisher": c.publisher,
                "Date": c.publication_date[:10],
                "Verified Claim": c.claim[:100] + ("..." if len(c.claim) > 100 else ""),
                "Source Link": c.source_url,
            }
            for c in citations
        ]
        st.dataframe(c_table, width="stretch", hide_index=True)
    else:
        st.info("No explicit factual citations were extracted for this scenario run.")

    if research_state.get("unverified_claims"):
        with st.expander("⚠️ Disclosed Unverified Evidence"):
            for uc in research_state["unverified_claims"]:
                st.warning(uc)

    # Direct Sentiment Report Export Toolbar
    if research_state.get("report"):
        st.markdown("---")
        tickers_str = [getattr(t, "symbol", getattr(t, "ticker", str(t))) for t in research_state.get("validated_tickers", [])]
        if not tickers_str and research_state.get("tickers"):
            tickers_str = research_state["tickers"]

        rep_dict = research_state.get("report_json")
        if not rep_dict and research_state.get("report"):
            r_obj = research_state["report"]
            rep_dict = r_obj.model_dump() if hasattr(r_obj, "model_dump") else {}

        export_payload = {
            "id": research_state.get("job_id", "sentiment_report"),
            "user_id": research_state.get("user_id", "current_user"),
            "tab": "sentiment",
            "tickers": tickers_str,
            "start_at": research_state.get("start_date", ""),
            "end_at": research_state.get("end_date", ""),
            "horizon_days": research_state.get("horizon_days"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "markdown": research_state.get("report_markdown", ""),
            "report_json": rep_dict,
        }

        with st.container(border=True):
            st.markdown("#### 📥 Export Sentiment Research Report")
            c_pdf, c_md, c_json, c_csv = st.columns(4)
            with c_pdf:
                pdf_data = export_to_pdf(export_payload)
                st.download_button(
                    "📥 PDF Report",
                    data=pdf_data,
                    file_name=f"Sentiment_Report_{'-'.join(tickers_str)}_{research_state.get('horizon_days', 30)}D.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="sent_tab_export_pdf",
                )
            with c_md:
                md_data = export_to_markdown(export_payload)
                st.download_button(
                    "📥 Markdown Report",
                    data=md_data,
                    file_name=f"Sentiment_Report_{'-'.join(tickers_str)}_{research_state.get('horizon_days', 30)}D.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key="sent_tab_export_md",
                )
            with c_json:
                json_data = export_to_json(export_payload)
                st.download_button(
                    "📥 JSON Data",
                    data=json_data,
                    file_name=f"Sentiment_Report_{'-'.join(tickers_str)}_{research_state.get('horizon_days', 30)}D.json",
                    mime="application/json",
                    use_container_width=True,
                    key="sent_tab_export_json",
                )
            with c_csv:
                csv_data = export_to_csv(export_payload)
                st.download_button(
                    "📥 CSV Citations",
                    data=csv_data,
                    file_name=f"Sentiment_Report_{'-'.join(tickers_str)}_{research_state.get('horizon_days', 30)}D.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="sent_tab_export_csv",
                )

    # 4. Regulatory & Methodology Disclaimers
    st.markdown("---")
    st.caption(
        "**Regulatory Disclaimer & Methodology Notice:** Sentiment and scenario outlooks are synthesized from publicly available news items "
        "and corporate filings using bounded agentic AI. Outlooks represent probabilistic scenario possibilities over the selected horizon, "
        "**NOT guaranteed future price predictions, price targets, or investment advice.** Historical news sentiment reflects past reporting "
        "and does not ensure future market performance. Evidence strength is assessed transparently based on source corroboration without "
        "speculative probability inflation."
    )
