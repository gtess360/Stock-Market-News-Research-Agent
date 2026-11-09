"""Decorative theme, SVG illustrations, and CSS injection for the Stock Market News Research Agent dashboard."""
import re
import streamlit as st


def clean_svg(svg: str) -> str:
    """Strip XML comments and compress whitespace so markdown renders SVG cleanly without pre/code triggers."""
    cleaned = re.sub(r'<!--.*?-->', '', svg, flags=re.DOTALL)
    return " ".join(cleaned.split())


def get_header_robot_svg() -> str:
    """Return inline SVG of the friendly AI Robot avatar matching approved screenshot."""
    raw = """
    <svg width="68" height="68" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="botHead" x1="20" y1="20" x2="80" y2="80" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#FFFFFF"/>
                <stop offset="100%" stop-color="#CBD5E1"/>
            </linearGradient>
            <linearGradient id="botVisor" x1="25" y1="35" x2="75" y2="65" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#0F172A"/>
                <stop offset="100%" stop-color="#1E293B"/>
            </linearGradient>
            <linearGradient id="botGlow" x1="30" y1="45" x2="70" y2="55" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#38BDF8"/>
                <stop offset="100%" stop-color="#0284C7"/>
            </linearGradient>
            <filter id="glowEffect" x="0" y="0" width="100" height="100" filterUnits="userSpaceOnUse">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feComposite in="SourceGraphic" in2="blur" operator="over"/>
            </filter>
        </defs>
        <rect x="47" y="6" width="6" height="14" rx="3" fill="#94A3B8"/>
        <circle cx="50" cy="8" r="7" fill="#38BDF8" filter="url(#glowEffect)"/>
        <circle cx="50" cy="8" r="4" fill="#E0F2FE"/>
        <rect x="8" y="42" width="10" height="20" rx="5" fill="#64748B"/>
        <rect x="82" y="42" width="10" height="20" rx="5" fill="#64748B"/>
        <circle cx="13" cy="52" r="3" fill="#38BDF8"/>
        <circle cx="87" cy="52" r="3" fill="#38BDF8"/>
        <rect x="14" y="18" width="72" height="66" rx="28" fill="url(#botHead)" stroke="#E2E8F0" stroke-width="2"/>
        <rect x="22" y="32" width="56" height="36" rx="16" fill="url(#botVisor)"/>
        <ellipse cx="36" cy="50" rx="8" ry="9" fill="url(#botGlow)" filter="url(#glowEffect)"/>
        <ellipse cx="64" cy="50" rx="8" ry="9" fill="url(#botGlow)" filter="url(#glowEffect)"/>
        <ellipse cx="38" cy="48" rx="3" ry="4" fill="#FFFFFF"/>
        <ellipse cx="66" cy="48" rx="3" ry="4" fill="#FFFFFF"/>
        <path d="M44 60Q50 63 56 60" stroke="#38BDF8" stroke-width="2.5" stroke-linecap="round"/>
        <circle cx="28" cy="58" r="3" fill="#F472B6" opacity="0.6"/>
        <circle cx="72" cy="58" r="3" fill="#F472B6" opacity="0.6"/>
    </svg>
    """
    return clean_svg(raw)


def get_header_chart_svg() -> str:
    """Return inline SVG of market candlesticks, upward trend curve, and blue volume bars."""
    raw = """
    <svg width="270" height="75" viewBox="0 0 270 75" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="chartLineGrad" x1="0" y1="50" x2="270" y2="10" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#38BDF8"/>
                <stop offset="50%" stop-color="#22C55E"/>
                <stop offset="100%" stop-color="#4ADE80"/>
            </linearGradient>
            <linearGradient id="chartAreaGrad" x1="0" y1="20" x2="0" y2="75" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#22C55E" stop-opacity="0.32"/>
                <stop offset="100%" stop-color="#22C55E" stop-opacity="0.0"/>
            </linearGradient>
            <linearGradient id="volBarGrad" x1="0" y1="40" x2="0" y2="75" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#38BDF8"/>
                <stop offset="100%" stop-color="#0284C7"/>
            </linearGradient>
            <filter id="neonGlow" x="-10" y="-10" width="290" height="95" filterUnits="userSpaceOnUse">
                <feGaussianBlur stdDeviation="2.5" result="blur"/>
                <feComposite in="SourceGraphic" in2="blur" operator="over"/>
            </filter>
        </defs>

        <!-- Blue Volume Bars along bottom floor -->
        <g id="volumeBars" opacity="0.85">
            <rect x="12" y="60" width="4.5" height="13" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="22" y="54" width="4.5" height="19" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="32" y="58" width="4.5" height="15" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="42" y="63" width="4.5" height="10" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="52" y="55" width="4.5" height="18" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="62" y="51" width="4.5" height="22" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="72" y="57" width="4.5" height="16" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="82" y="62" width="4.5" height="11" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="92" y="54" width="4.5" height="19" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="102" y="48" width="4.5" height="25" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="112" y="53" width="4.5" height="20" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="122" y="47" width="4.5" height="26" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="132" y="43" width="4.5" height="30" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="142" y="49" width="4.5" height="24" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="152" y="41" width="4.5" height="32" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="162" y="37" width="4.5" height="36" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="172" y="44" width="4.5" height="29" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="182" y="35" width="4.5" height="38" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="192" y="30" width="4.5" height="43" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="202" y="38" width="4.5" height="35" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="212" y="28" width="4.5" height="45" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="222" y="24" width="4.5" height="49" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="232" y="22" width="4.5" height="51" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="242" y="18" width="4.5" height="55" rx="1.5" fill="url(#volBarGrad)"/>
            <rect x="252" y="15" width="4.5" height="58" rx="1.5" fill="url(#volBarGrad)"/>
        </g>

        <!-- Candlesticks (Red and Green) -->
        <line x1="20" y1="36" x2="20" y2="58" stroke="#22C55E" stroke-width="1.5"/>
        <rect x="17.5" y="42" width="5" height="11" rx="1" fill="#22C55E"/>
        <line x1="38" y1="38" x2="38" y2="60" stroke="#EF4444" stroke-width="1.5"/>
        <rect x="35.5" y="44" width="5" height="12" rx="1" fill="#EF4444"/>
        <line x1="56" y1="42" x2="56" y2="65" stroke="#EF4444" stroke-width="1.5"/>
        <rect x="53.5" y="46" width="5" height="14" rx="1" fill="#EF4444"/>
        <line x1="74" y1="33" x2="74" y2="54" stroke="#22C55E" stroke-width="1.5"/>
        <rect x="71.5" y="38" width="5" height="12" rx="1" fill="#22C55E"/>
        <line x1="92" y1="28" x2="92" y2="48" stroke="#22C55E" stroke-width="1.5"/>
        <rect x="89.5" y="32" width="5" height="12" rx="1" fill="#22C55E"/>
        <line x1="110" y1="30" x2="110" y2="50" stroke="#EF4444" stroke-width="1.5"/>
        <rect x="107.5" y="34" width="5" height="11" rx="1" fill="#EF4444"/>
        <line x1="128" y1="22" x2="128" y2="44" stroke="#22C55E" stroke-width="1.5"/>
        <rect x="125.5" y="26" width="5" height="13" rx="1" fill="#22C55E"/>
        <line x1="146" y1="18" x2="146" y2="40" stroke="#22C55E" stroke-width="1.5"/>
        <rect x="143.5" y="22" width="5" height="13" rx="1" fill="#22C55E"/>
        <line x1="164" y1="12" x2="164" y2="34" stroke="#22C55E" stroke-width="1.5"/>
        <rect x="161.5" y="16" width="5" height="13" rx="1" fill="#22C55E"/>
        <line x1="182" y1="8" x2="182" y2="28" stroke="#22C55E" stroke-width="1.5"/>
        <rect x="179.5" y="11" width="5" height="13" rx="1" fill="#22C55E"/>
        <line x1="200" y1="5" x2="200" y2="24" stroke="#22C55E" stroke-width="1.5"/>
        <rect x="197.5" y="8" width="5" height="12" rx="1" fill="#22C55E"/>
        <line x1="218" y1="3" x2="218" y2="20" stroke="#22C55E" stroke-width="1.5"/>
        <rect x="215.5" y="5" width="5" height="12" rx="1" fill="#22C55E"/>
        <line x1="236" y1="2" x2="236" y2="18" stroke="#22C55E" stroke-width="1.5"/>
        <rect x="233.5" y="4" width="5" height="11" rx="1" fill="#22C55E"/>

        <!-- Upward Trend Line & Area -->
        <path d="M10 56 C 50 54, 70 40, 100 36 C 130 32, 150 18, 180 12 C 210 8, 240 5, 265 4 L 265 75 L 10 75 Z" fill="url(#chartAreaGrad)"/>
        <path d="M10 56 C 50 54, 70 40, 100 36 C 130 32, 150 18, 180 12 C 210 8, 240 5, 265 4" stroke="url(#chartLineGrad)" stroke-width="3" stroke-linecap="round" filter="url(#neonGlow)"/>
        <circle cx="100" cy="36" r="3.5" fill="#FFFFFF" stroke="#22C55E" stroke-width="2"/>
        <circle cx="180" cy="12" r="3.5" fill="#FFFFFF" stroke="#22C55E" stroke-width="2"/>
        <circle cx="265" cy="4" r="4.5" fill="#4ADE80" filter="url(#neonGlow)"/>
    </svg>
    """
    return clean_svg(raw)


def get_sidebar_bull_svg() -> str:
    """Return inline SVG of the luminous electric blue financial bull with ascending bars behind it."""
    raw = """
    <svg width="210" height="155" viewBox="0 0 210 155" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="bullGrad" x1="20" y1="20" x2="190" y2="140" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#38BDF8"/>
                <stop offset="50%" stop-color="#0284C7"/>
                <stop offset="100%" stop-color="#0369A1"/>
            </linearGradient>
            <linearGradient id="barGrad" x1="0" y1="40" x2="0" y2="155" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#0EA5E9" stop-opacity="0.8"/>
                <stop offset="100%" stop-color="#0369A1" stop-opacity="0.12"/>
            </linearGradient>
            <filter id="bullGlow" x="-10" y="-10" width="230" height="175" filterUnits="userSpaceOnUse">
                <feGaussianBlur stdDeviation="3.5" result="glow"/>
                <feComposite in="SourceGraphic" in2="glow" operator="over"/>
            </filter>
        </defs>

        <!-- Ascending Financial Bar Charts (Behind Bull) -->
        <rect x="15" y="125" width="16" height="25" rx="3" fill="url(#barGrad)"/>
        <rect x="38" y="112" width="16" height="38" rx="3" fill="url(#barGrad)"/>
        <rect x="61" y="98" width="16" height="52" rx="3" fill="url(#barGrad)"/>
        <rect x="84" y="82" width="16" height="68" rx="3" fill="url(#barGrad)"/>
        <rect x="107" y="65" width="16" height="85" rx="3" fill="url(#barGrad)"/>
        <rect x="130" y="48" width="16" height="102" rx="3" fill="url(#barGrad)"/>
        <rect x="153" y="32" width="16" height="118" rx="3" fill="url(#barGrad)"/>
        <rect x="176" y="16" width="16" height="134" rx="3" fill="url(#barGrad)"/>

        <!-- Glowing Neon Electric Blue Bull Silhouette -->
        <path d="M38 96 C 44 84, 58 72, 76 68 C 82 66, 92 60, 102 58 C 112 56, 122 49, 132 42 C 137 39, 146 32, 150 28 C 153 26, 158 25, 163 29 C 166 32, 163 37, 156 42 C 150 47, 146 52, 153 55 C 160 57, 168 55, 173 51 C 176 49, 180 52, 178 57 C 176 62, 168 69, 158 72 C 150 75, 143 79, 138 85 C 133 91, 130 99, 128 107 C 126 115, 123 118, 118 113 C 113 108, 110 103, 108 96 C 103 93, 98 93, 93 96 C 88 100, 83 110, 78 113 C 73 116, 68 110, 70 103 C 72 96, 76 90, 73 86 C 68 84, 58 86, 50 90 C 45 93, 40 98, 36 96 Z" 
              fill="url(#bullGrad)" filter="url(#bullGlow)"/>
        <path d="M150 28 C 154 21, 162 15, 172 13 C 169 20, 164 24, 157 28 Z" fill="#E0F2FE" filter="url(#bullGlow)"/>
        <path d="M143 31 C 147 24, 153 20, 161 17 C 158 23, 153 27, 148 31 Z" fill="#7DD3FC" opacity="0.9"/>
        <path d="M76 68 C 90 64, 110 58, 132 42" stroke="#7DD3FC" stroke-width="2" stroke-linecap="round" opacity="0.85"/>
        <path d="M128 107 C 132 96, 142 82, 158 72" stroke="#38BDF8" stroke-width="1.5" stroke-linecap="round" opacity="0.75"/>
        <path d="M38 96 C 30 99, 23 107, 21 118" stroke="#38BDF8" stroke-width="2.5" stroke-linecap="round"/>
    </svg>
    """
    return clean_svg(raw)


def inject_custom_theme() -> None:
    """Inject approved light-purple/lavender and navy styling matching the reference screenshot."""
    css = """
    <style>
    /* Global dashboard background with soft light-purple/lavender tint */
    .stApp {
        background-color: #EEF2FB !important;
        color: #0F172A !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Main container max-width & padding */
    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px !important;
    }

    /* Hide raw Streamlit page title so custom branded header banner is cleanly showcased */
    div[data-testid="stHeadingWithActionElements"] {
        display: none !important;
    }

    /* Hide redundant selectbox and secondary launch button since segmented control handles timeline */
    div[data-testid="stSelectbox"] {
        display: none !important;
    }
    div.stButton:has(button:contains("Launch Research")) {
        display: none !important;
    }

    /* Navy-blue Sidebar Theme matching screenshot */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #070F26 0%, #0A1535 50%, #060D22 100%) !important;
        color: #F8FAFC !important;
        border-right: 1px solid #1E293B !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #F8FAFC !important;
    }

    /* Sidebar Navigation Pills */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
        gap: 0.4rem;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background-color: transparent !important;
        color: #94A3B8 !important;
        padding: 0.65rem 1rem !important;
        border-radius: 9px !important;
        font-weight: 500 !important;
        font-size: 0.94rem !important;
        transition: all 0.15s ease-in-out;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"],
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(90deg, #2563EB 0%, #3B82F6 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35) !important;
    }

    /* Branded Header Banner matching screenshot */
    .dashboard-header-card {
        background: linear-gradient(90deg, #070D1E 0%, #0F2042 35%, #162E62 70%, #0A1630 100%);
        color: #FFFFFF;
        padding: 1.15rem 1.75rem;
        border-radius: 18px;
        margin-bottom: 1.25rem;
        box-shadow: 0 6px 20px rgba(7, 13, 30, 0.25);
        display: flex;
        justify-content: space-between;
        align-items: center;
        overflow: hidden;
        position: relative;
    }
    .header-left {
        display: flex;
        align-items: center;
        gap: 1.25rem;
    }

    /* Filter Controls Card Container */
    .filter-card-container {
        background: #FFFFFF;
        border: 1px solid #E0E7FF;
        border-radius: 16px;
        padding: 1.1rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.05);
    }
    .filter-section-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #0F172A;
        display: flex;
        align-items: center;
        gap: 0.45rem;
        margin-bottom: 0.5rem;
    }

    /* Multiselect Tag Chips matching screenshot (NVDA x, AAPL x, MSFT x) */
    [data-baseweb="tag"] {
        background-color: #EEF2FF !important;
        color: #4338CA !important;
        border: 1px solid #C7D2FE !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    [data-baseweb="select"] {
        border-radius: 8px !important;
    }

    /* Research Timeline Horizontal Buttons matching screenshot */
    .timeline-active-btn button {
        background: linear-gradient(90deg, #2563EB 0%, #3B82F6 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        height: 38px !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3) !important;
    }
    .timeline-inactive-btn button {
        background: #FFFFFF !important;
        color: #475569 !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        height: 38px !important;
    }
    .timeline-inactive-btn button:hover {
        background: #F8FAFC !important;
        border-color: #CBD5E1 !important;
        color: #0F172A !important;
    }

    /* Tabs Pill Styling matching screenshot */
    [data-baseweb="tab-list"] {
        background-color: #E2E8F8 !important;
        padding: 0.35rem !important;
        border-radius: 12px !important;
        gap: 0.35rem !important;
        border: 1px solid #D8E1F8 !important;
        margin-bottom: 1.25rem !important;
    }
    [data-baseweb="tab"] {
        border-radius: 9px !important;
        padding: 0.65rem 1.75rem !important;
        font-size: 0.98rem !important;
        font-weight: 600 !important;
        color: #475569 !important;
        border: none !important;
        background-color: transparent !important;
        transition: all 0.2s ease-in-out !important;
    }
    [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(90deg, #5B46F6 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 14px rgba(91, 70, 246, 0.35) !important;
    }
    [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* Top 3 Summary Metric Cards with Lavender/Blue accents */
    .summary-card {
        background: #FFFFFF;
        border: 1px solid #E0E7FF;
        border-radius: 14px;
        padding: 1.1rem 1.35rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.05);
        position: relative;
        overflow: hidden;
        min-height: 98px;
    }
    .summary-card-left {
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }
    .summary-icon-box {
        width: 44px;
        height: 44px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.35rem;
    }
    .summary-val-title {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 500;
        margin-bottom: 0.15rem;
    }
    .summary-val-row {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
    }
    .summary-val-num {
        font-size: 1.65rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1;
    }
    .summary-badge-pct {
        background-color: #DCFCE7;
        color: #16A34A;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 0.2rem 0.45rem;
        border-radius: 6px;
    }
    .summary-subtext {
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 0.2rem;
    }

    /* Company Navigation Cards (Left Column) */
    .company-nav-card {
        background: #FFFFFF;
        border: 1px solid #E0E7FF;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.65rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        text-decoration: none !important;
        color: inherit !important;
        transition: all 0.15s ease-in-out;
    }
    .company-nav-card:hover {
        border-color: #818CF8;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
    }
    .company-nav-card-active {
        background: #FFFFFF !important;
        border: 1.5px solid #818CF8 !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.15) !important;
    }

    /* News Feed Item Cards (Middle Column) */
    .news-feed-card {
        background: #FFFFFF;
        border: 1px solid #E0E7FF;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.65rem;
        display: flex;
        gap: 0.9rem;
        align-items: flex-start;
        transition: box-shadow 0.15s ease-in-out;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.04);
    }
    .news-feed-card:hover {
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.1);
        border-color: #C7D2FE;
    }
    .news-thumb-box {
        width: 60px;
        height: 52px;
        border-radius: 8px;
        background: #0F172A;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.15rem;
        flex-shrink: 0;
        overflow: hidden;
    }
    .news-headline-link {
        font-size: 0.94rem;
        font-weight: 600;
        color: #0F172A;
        text-decoration: none;
        line-height: 1.35;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .news-meta-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 0.35rem;
        font-size: 0.78rem;
        color: #64748B;
    }
    .sentiment-tag-pos {
        background: #DCFCE7;
        color: #166534;
        font-weight: 600;
        font-size: 0.72rem;
        padding: 0.18rem 0.5rem;
        border-radius: 6px;
    }
    .sentiment-tag-neu {
        background: #F1F5F9;
        color: #475569;
        font-weight: 600;
        font-size: 0.72rem;
        padding: 0.18rem 0.5rem;
        border-radius: 6px;
    }
    .sentiment-tag-neg {
        background: #FEE2E2;
        color: #991B1B;
        font-weight: 600;
        font-size: 0.72rem;
        padding: 0.18rem 0.5rem;
        border-radius: 6px;
    }

    /* Right Column: AI Summary Card matching screenshot */
    .ai-summary-card {
        background: #F5F3FF;
        border: 1px solid #DDD6FE;
        border-radius: 12px;
        padding: 1.1rem 1.25rem;
        margin-top: 0.85rem;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.06);
    }
    .ai-summary-header {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        color: #6D28D9;
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .ai-summary-body {
        font-size: 0.88rem;
        color: #1E1B4B;
        line-height: 1.5;
    }

    /* Bottom Action Bar */
    .dashboard-footer-bar {
        background: #FFFFFF;
        border: 1px solid #E0E7FF;
        border-radius: 14px;
        padding: 0.85rem 1.4rem;
        margin-top: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.05);
    }
    .footer-timestamp {
        font-size: 0.82rem;
        color: #64748B;
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }
    .footer-actions {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    /* Targeted Button Styling */
    .btn-generate-report button {
        background: linear-gradient(90deg, #5B46F6 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 14px rgba(91, 70, 246, 0.35) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .btn-compare-stocks button {
        background: #FFFFFF !important;
        color: #334155 !important;
        border: 1px solid #E0E7FF !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    .btn-export-popover button {
        background: #FFFFFF !important;
        color: #334155 !important;
        border: 1px solid #E0E7FF !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }

    /* Status Badges */
    .badge-unlimited {
        background: #00ADB5;
        color: #FFFFFF !important;
        font-weight: 600;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        display: inline-block;
    }
    .badge-free {
        background: #E0F2FE;
        color: #0284C7 !important;
        font-weight: 600;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        display: inline-block;
        border: 1px solid #BAE6FD;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
