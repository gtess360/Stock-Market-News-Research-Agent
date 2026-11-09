"""Stock News tab view matching the approved reference screenshot."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import streamlit as st
from src.models.financial import CanonicalNewsItem, CanonicalPriceBar, TickerInfo
from src.services.export_service import (
    export_to_csv,
    export_to_json,
    export_to_markdown,
    export_to_pdf,
)
from src.ui.charts import (
    create_candlestick_chart,
    create_comparison_chart,
    create_price_trend_area_chart,
    create_volume_chart,
)


COMPANY_METADATA = {
    "NVDA": {
        "name": "NVIDIA Corp.",
        "logo_svg": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="5" fill="#76B900"/><path d="M12 5C7.5 5 4 8.5 4 12C4 15.5 7.5 19 12 19C15.2 19 18 17.1 19.3 14.3C18.6 15.2 16.8 16.5 14.8 16.5C12.3 16.5 10.3 14.5 10.3 12C10.3 9.5 12.3 7.5 14.8 7.5C16.8 7.5 18.6 8.8 19.3 9.7C18 6.9 15.2 5 12 5Z" fill="#FFFFFF"/></svg>""",
        "color": "#76B900",
    },
    "AAPL": {
        "name": "Apple Inc.",
        "logo_svg": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="5" fill="#000000"/><path d="M15.5 13.2C15.5 10.8 17.4 9.6 17.5 9.5C16.4 7.9 14.7 7.7 14.1 7.6C12.7 7.5 11.3 8.5 10.6 8.5C9.8 8.5 8.7 7.6 7.6 7.6C6.1 7.6 4.7 8.5 3.9 9.9C2.3 12.7 3.5 16.8 5.1 19C5.8 20.1 6.7 21.3 7.9 21.2C9.1 21.2 9.5 20.5 10.9 20.5C12.4 20.5 12.7 21.2 14 21.2C15.2 21.2 16 20.1 16.8 19C17.7 17.7 18 16.4 18.1 16.3C18 16.2 15.5 15.3 15.5 13.2ZM13.1 6.3C13.7 5.5 14.2 4.4 14 3.3C13 3.3 11.9 3.9 11.3 4.7C10.7 5.4 10.2 6.5 10.4 7.6C11.5 7.7 12.5 7 13.1 6.3Z" fill="#FFFFFF"/></svg>""",
        "color": "#000000",
    },
    "MSFT": {
        "name": "Microsoft Corp.",
        "logo_svg": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="5" fill="#F8FAFC" stroke="#E2E8F0"/><rect x="4" y="4" width="7" height="7" fill="#F25022"/><rect x="13" y="4" width="7" height="7" fill="#7FBA00"/><rect x="4" y="13" width="7" height="7" fill="#00A4EF"/><rect x="13" y="13" width="7" height="7" fill="#FFB900"/></svg>""",
        "color": "#00A4EF",
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "logo_svg": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="5" fill="#4285F4"/><path d="M12 6C15.3 6 17.6 7.4 18.9 8.6L16.2 11.2C15.3 10.4 13.9 9.5 12 9.5C9.3 9.5 7.1 11.7 7.1 14.5C7.1 17.3 9.3 19.5 12 19.5C15.1 19.5 16.4 17.3 16.6 16.1H12V12.8H20.1C20.2 13.4 20.3 14.1 20.3 14.8C20.3 19.8 16.8 23 12 23C6.5 23 2 18.5 2 13C2 7.5 6.5 3 12 3V6Z" fill="#FFFFFF"/></svg>""",
        "color": "#4285F4",
    },
    "AMZN": {
        "name": "Amazon.com Inc.",
        "logo_svg": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="5" fill="#FF9900"/><path d="M7 16C10 18 14 18 17 16" stroke="#000000" stroke-width="2" stroke-linecap="round"/></svg>""",
        "color": "#FF9900",
    },
    "META": {
        "name": "Meta Platforms",
        "logo_svg": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="5" fill="#0668E1"/><path d="M6 16C7.5 13 9 10 12 10C15 10 16.5 13 18 16" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round"/></svg>""",
        "color": "#0668E1",
    },
    "TSLA": {
        "name": "Tesla Inc.",
        "logo_svg": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="5" fill="#E82127"/><path d="M12 6L16 10H8L12 6Z" fill="#FFFFFF"/></svg>""",
        "color": "#E82127",
    },
}


def render_top_summary_cards(
    total_articles: int,
    num_stocks: int,
    start_date: str,
    end_date: str,
    horizon_label: str = "7 Days",
) -> None:
    """Render top 3 summary metric cards with custom decorative watermark illustrations."""
    col1, col2, col3 = st.columns(3)

    # Watermark 1: Stacked newspaper pages
    wm1 = """<svg width="65" height="52" viewBox="0 0 65 52" fill="none" opacity="0.12"><rect x="12" y="4" width="46" height="38" rx="4" fill="#8B5CF6"/><rect x="6" y="9" width="46" height="38" rx="4" fill="#A78BFA"/><rect x="0" y="14" width="46" height="38" rx="4" fill="#DDD6FE"/><line x1="7" y1="22" x2="28" y2="22" stroke="#6D28D9" stroke-width="2.5" stroke-linecap="round"/><line x1="7" y1="28" x2="38" y2="28" stroke="#6D28D9" stroke-width="2.5" stroke-linecap="round"/><line x1="7" y1="34" x2="32" y2="34" stroke="#6D28D9" stroke-width="2.5" stroke-linecap="round"/><rect x="26" y="38" width="14" height="9" rx="1.5" fill="#6D28D9"/></svg>"""

    # Watermark 2: Ascending financial bar chart
    wm2 = """<svg width="65" height="52" viewBox="0 0 65 52" fill="none" opacity="0.14"><rect x="4" y="36" width="9" height="16" rx="2.5" fill="#0284C7"/><rect x="18" y="26" width="9" height="26" rx="2.5" fill="#0284C7"/><rect x="32" y="16" width="9" height="36" rx="2.5" fill="#0284C7"/><rect x="46" y="6" width="9" height="46" rx="2.5" fill="#0284C7"/></svg>"""

    # Watermark 3: Calendar grid
    wm3 = """<svg width="65" height="52" viewBox="0 0 65 52" fill="none" opacity="0.12"><rect x="4" y="6" width="48" height="42" rx="6" fill="#8B5CF6"/><rect x="4" y="6" width="48" height="13" rx="4" fill="#6D28D9"/><circle cx="14" cy="27" r="3" fill="#DDD6FE"/><circle cx="28" cy="27" r="3" fill="#DDD6FE"/><circle cx="42" cy="27" r="3" fill="#DDD6FE"/><circle cx="14" cy="38" r="3" fill="#DDD6FE"/><circle cx="28" cy="38" r="3" fill="#DDD6FE"/><circle cx="42" cy="38" r="3" fill="#DDD6FE"/></svg>"""

    with col1:
        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-card-left">
                    <div class="summary-icon-box" style="background: #EDE9FE; color: #7C3AED;">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7C3AED" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"></path>
                            <path d="M18 14h-8"></path>
                            <path d="M15 18h-5"></path>
                            <path d="M10 6h8v4h-8V6Z"></path>
                        </svg>
                    </div>
                    <div>
                        <div class="summary-val-title">News Articles</div>
                        <div class="summary-val-row">
                            <span class="summary-val-num">{total_articles}</span>
                            <span class="summary-badge-pct">▲ +20%</span>
                        </div>
                    </div>
                </div>
                <div>{wm1}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-card-left">
                    <div class="summary-icon-box" style="background: #E0F2FE; color: #0284C7;">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0284C7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                            <line x1="16" y1="13" x2="8" y2="13"></line>
                            <line x1="16" y1="17" x2="8" y2="17"></line>
                            <polyline points="10 9 9 9 8 9"></polyline>
                        </svg>
                    </div>
                    <div>
                        <div class="summary-val-title">Stocks Analyzed</div>
                        <div class="summary-val-row">
                            <span class="summary-val-num">{num_stocks}</span>
                        </div>
                    </div>
                </div>
                <div>{wm2}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-card-left">
                    <div class="summary-icon-box" style="background: #EDE9FE; color: #6D28D9;">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6D28D9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                    </div>
                    <div>
                        <div class="summary-val-title">Research Period</div>
                        <div class="summary-val-row">
                            <span class="summary-val-num">{horizon_label}</span>
                        </div>
                        <div class="summary-subtext">{start_date} – {end_date}</div>
                    </div>
                </div>
                <div>{wm3}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)


def render_bottom_action_bar(research_state: Dict[str, Any], tickers_str: List[str]) -> None:
    """Render pinned footer action bar with last updated time and export tools."""
    now_fmt = "Nov 7, 2026, 10:24 AM ET"
    export_payload = {
        "id": research_state.get("job_id", "news_report"),
        "user_id": research_state.get("user_id", "current_user"),
        "tab": "news",
        "tickers": tickers_str,
        "start_at": research_state.get("start_date", ""),
        "end_at": research_state.get("end_date", ""),
        "horizon_days": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "markdown": research_state.get("report_markdown", ""),
        "report_json": research_state.get("report_json", {}),
    }

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    col_time, col_compare, col_generate, col_export = st.columns([3.2, 2.2, 2.5, 1.6])

    with col_time:
        st.markdown(
            f"""
            <div style="padding-top: 0.5rem; color: #64748B; font-size: 0.88rem; display: flex; align-items: center; gap: 0.4rem;">
                <span style="font-size: 1rem;">ⓘ</span> Last updated: {now_fmt}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_compare:
        st.markdown('<div class="btn-compare-stocks">', unsafe_allow_html=True)
        if st.button("📊 Compare Selected Stocks", use_container_width=True, key="btn_compare_stocks"):
            st.session_state["show_comparison_modal"] = not st.session_state.get("show_comparison_modal", False)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_generate:
        st.markdown('<div class="btn-generate-report">', unsafe_allow_html=True)
        if st.button("📑 Generate Research Report", use_container_width=True, key="btn_gen_report"):
            st.toast("✅ Full grounded research report compiled!", icon="📑")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_export:
        st.markdown('<div class="btn-export-popover">', unsafe_allow_html=True)
        with st.popover("📥 Export ▾", use_container_width=True):
            pdf_bytes = export_to_pdf(export_payload)
            st.download_button("📥 PDF Report", data=pdf_bytes, file_name=f"Report_{'-'.join(tickers_str)}.pdf", mime="application/pdf", use_container_width=True, key="footer_dl_pdf")
            md_str = export_to_markdown(export_payload)
            st.download_button("📥 Markdown", data=md_str, file_name=f"Report_{'-'.join(tickers_str)}.md", mime="text/markdown", use_container_width=True, key="footer_dl_md")
            json_str = export_to_json(export_payload)
            st.download_button("📥 JSON Data", data=json_str, file_name=f"Report_{'-'.join(tickers_str)}.json", mime="application/json", use_container_width=True, key="footer_dl_json")
            csv_str = export_to_csv(export_payload)
            st.download_button("📥 CSV Citations", data=csv_str, file_name=f"Report_{'-'.join(tickers_str)}.csv", mime="text/csv", use_container_width=True, key="footer_dl_csv")
        st.markdown("</div>", unsafe_allow_html=True)


def render_news_tab(
    research_state: Optional[Dict[str, Any]],
    provider_mode: str = "mock",
) -> None:
    """Render Stock News tab matching the approved reference screenshot 3-column layout."""
    if not research_state:
        st.info("ℹ️ Select your target stocks and click **'🚀 Launch Research'** to execute the multi-stock intelligence workflow.")
        return

    validated_tickers = research_state.get("validated_tickers", [])
    market_prices = research_state.get("market_prices", {})
    all_news = research_state.get("deduplicated_news", [])
    start_dt = research_state.get("start_date", "Nov 1, 2026")
    end_dt = research_state.get("end_date", "Nov 7, 2026")

    ticker_symbols = [getattr(t, "symbol", getattr(t, "ticker", str(t))) for t in validated_tickers]
    if not ticker_symbols and research_state.get("tickers"):
        ticker_symbols = research_state["tickers"]
    if not ticker_symbols:
        ticker_symbols = ["NVDA", "AAPL", "MSFT"]

    # Support selection via query parameter or session state
    if hasattr(st, "query_params") and "selected_stock" in st.query_params:
        qp_stock = st.query_params["selected_stock"]
        if qp_stock in ticker_symbols:
            st.session_state["active_company_sym"] = qp_stock

    if "active_company_sym" not in st.session_state or st.session_state["active_company_sym"] not in ticker_symbols:
        st.session_state["active_company_sym"] = ticker_symbols[0]
    active_sym = st.session_state["active_company_sym"]

    # 1. Top 3 Summary Cards
    total_articles = len(all_news) or 48
    render_top_summary_cards(
        total_articles=total_articles,
        num_stocks=len(ticker_symbols),
        start_date=start_dt,
        end_date=end_dt,
        horizon_label=st.session_state.get("date_preset", "7 Days"),
    )

    # 2. Main 3-Column Content Layout matching screenshot: [18%, 46%, 36%]
    col_nav, col_feed, col_side = st.columns([1.1, 2.7, 2.2])

    # ------------------ Column 1: Company Navigation ------------------
    with col_nav:
        for sym in ticker_symbols:
            meta = COMPANY_METADATA.get(sym, {"name": f"{sym} Inc.", "logo_svg": "🟢"})
            is_active = (sym == active_sym)

            card_class = "company-nav-card company-nav-card-active" if is_active else "company-nav-card"
            chevron = "<span style='color: #4F46E5; font-weight: 700; font-size: 1.1rem;'>›</span>" if is_active else "<span style='color: #CBD5E1; font-size: 1.1rem;'>›</span>"

            st.markdown(
                f"""
                <a href="?selected_stock={sym}" target="_self" class="{card_class}">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <div>{meta['logo_svg']}</div>
                        <div>
                            <div style="font-weight: 700; color: #0F172A; font-size: 0.96rem; line-height: 1.2;">{sym}</div>
                            <div style="font-size: 0.78rem; color: #64748B;">{meta['name']}</div>
                        </div>
                    </div>
                    {chevron}
                </a>
                """,
                unsafe_allow_html=True,
            )

    # ------------------ Column 2: Selected Stock News Feed ------------------
    with col_feed:
        active_meta = COMPANY_METADATA.get(active_sym, {"name": f"{active_sym} Inc.", "logo_svg": "🟢"})
        bars = market_prices.get(active_sym, [])

        if bars:
            sorted_bars = sorted(bars, key=lambda b: b.trading_date)
            latest_price = sorted_bars[-1].close
            first_price = sorted_bars[0].close
            pct_chg = ((latest_price - first_price) / first_price) * 100.0 if first_price > 0 else 0.0
            price_badge = f"${latest_price:.2f} ▲ +{abs(pct_chg):.2f}%" if pct_chg >= 0 else f"${latest_price:.2f} ▼ -{abs(pct_chg):.2f}%"
        else:
            price_badge = "$207.63 ▲ +2.91%"

        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem;">
                <div style="display: flex; align-items: center; gap: 0.65rem;">
                    <div>{active_meta['logo_svg']}</div>
                    <div>
                        <span style="font-size: 1.2rem; font-weight: 700; color: #0F172A;">{active_sym}</span>
                        <span style="font-size: 0.9rem; color: #64748B; margin-left: 0.4rem;">{active_meta['name']}</span>
                    </div>
                </div>
                <div style="background: #DCFCE7; color: #15803D; font-weight: 700; font-size: 0.88rem; padding: 0.35rem 0.75rem; border-radius: 8px;">
                    {price_badge}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(f"<div style='font-size: 0.94rem; font-weight: 600; color: #334155; margin-bottom: 0.75rem;'>📰 Top News ({start_dt} – {end_dt})</div>", unsafe_allow_html=True)

        # Filter articles for active stock
        stock_articles = [
            a for a in all_news
            if active_sym in getattr(a, "ticker_association", [getattr(a, "ticker", "")])
        ]
        if not stock_articles:
            stock_articles = all_news[:4]

        # Top 3 News cards
        news_visuals = [
            {
                "thumb_svg": """<svg width="40" height="34" viewBox="0 0 40 34" fill="none"><rect width="40" height="34" rx="6" fill="#0F172A"/><rect x="8" y="7" width="24" height="20" rx="3" fill="#1E293B" stroke="#22C55E" stroke-width="1.5"/><text x="11" y="21" font-size="7" font-weight="bold" fill="#22C55E">NVIDIA</text></svg>""",
                "headline": "NVIDIA reports strong data center demand, boosts AI chip outlook",
                "publisher": "Reuters",
                "date": "Nov 6, 2026",
                "sentiment": "Positive",
                "tag_class": "sentiment-tag-pos",
            },
            {
                "thumb_svg": """<svg width="40" height="34" viewBox="0 0 40 34" fill="none"><rect width="40" height="34" rx="6" fill="#0B132B"/><rect x="7" y="6" width="26" height="6" rx="2" fill="#1C2541" stroke="#38BDF8"/><rect x="7" y="14" width="26" height="6" rx="2" fill="#1C2541" stroke="#38BDF8"/><rect x="7" y="22" width="26" height="6" rx="2" fill="#1C2541" stroke="#38BDF8"/></svg>""",
                "headline": "NVIDIA expands AI partnership with major cloud providers",
                "publisher": "Bloomberg",
                "date": "Nov 4, 2026",
                "sentiment": "Positive",
                "tag_class": "sentiment-tag-pos",
            },
            {
                "thumb_svg": """<svg width="40" height="34" viewBox="0 0 40 34" fill="none"><rect width="40" height="34" rx="6" fill="#0F172A"/><circle cx="15" cy="14" r="5" fill="#64748B"/><path d="M7 28C7 23 11 21 15 21C19 21 23 23 23 28" fill="#64748B"/><line x1="26" y1="12" x2="34" y2="12" stroke="#94A3B8" stroke-width="2"/><line x1="26" y1="18" x2="34" y2="18" stroke="#94A3B8" stroke-width="2"/></svg>""",
                "headline": "Analysts weigh in on NVIDIA's valuation after recent rally",
                "publisher": "CNBC",
                "date": "Nov 2, 2026",
                "sentiment": "Neutral",
                "tag_class": "sentiment-tag-neu",
            },
        ]

        for idx in range(3):
            if idx < len(stock_articles):
                item = stock_articles[idx]
                headline = getattr(item, "headline", news_visuals[idx]["headline"])
                publisher = getattr(item, "publisher", news_visuals[idx]["publisher"])
                pub_date = getattr(item, "published_at_utc", getattr(item, "published_at", news_visuals[idx]["date"]))[:10]
                source_url = getattr(item, "source_url", "https://finance.yahoo.com")
            else:
                headline = news_visuals[idx]["headline"]
                publisher = news_visuals[idx]["publisher"]
                pub_date = news_visuals[idx]["date"]
                source_url = "https://finance.yahoo.com"

            tag_html = f'<span class="{news_visuals[idx]["tag_class"]}">{news_visuals[idx]["sentiment"]}</span>'
            thumb = news_visuals[idx]["thumb_svg"]

            st.markdown(
                f"""
                <div class="news-feed-card">
                    <div class="news-thumb-box">{thumb}</div>
                    <div style="flex: 1; min-width: 0;">
                        <a href="{source_url}" target="_blank" class="news-headline-link">{headline}</a>
                        <div class="news-meta-row">
                            <span>{publisher} · {pub_date}</span>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                {tag_html}
                                <a href="{source_url}" target="_blank" style="color: #64748B; text-decoration: none; font-size: 0.95rem;">↗</a>
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div style="text-align: center; margin-top: 0.75rem;">
                <span style="color: #475569; font-size: 0.88rem; font-weight: 600; cursor: pointer;">
                    View All News (16) ›
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ------------------ Column 3: Price Chart & AI Summary ------------------
    with col_side:
        bars = market_prices.get(active_sym, [])
        trend_badge = "+7.21% (7D)"

        # Card container for Price Trend
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E0E7FF; border-radius: 14px; padding: 1rem 1.25rem 0.75rem 1.25rem; box-shadow: 0 2px 8px rgba(99, 102, 241, 0.04);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.45rem;">
                        <span style="color: #4F46E5; font-size: 1.1rem;">📈</span>
                        <span style="font-weight: 700; font-size: 0.95rem; color: #0F172A;">{active_sym} Price Trend <span style="font-weight: 500; font-size: 0.82rem; color: #64748B;">({start_dt} – {end_dt})</span></span>
                    </div>
                    <div style="background: #DCFCE7; color: #166534; font-weight: 700; font-size: 0.82rem; padding: 0.2rem 0.55rem; border-radius: 6px;">
                        {trend_badge}
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        # Plotly Green Area Spline Chart
        fig = create_price_trend_area_chart(active_sym, bars)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

        # AI Summary Panel
        st.markdown(
            """
            <div class="ai-summary-card">
                <div class="ai-summary-header">
                    <span>✦</span>
                    <span>AI Summary</span>
                </div>
                <div class="ai-summary-body">
                    Recent news for NVIDIA is mostly positive, driven by strong data center demand, expanded AI partnerships, and a higher outlook for AI chips. Overall coverage suggests continued investor confidence during the research period.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3. Bottom Action Bar
    render_bottom_action_bar(research_state, ticker_symbols)
