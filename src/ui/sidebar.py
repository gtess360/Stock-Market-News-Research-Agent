"""Sidebar navigation matching the approved reference screenshot."""
import streamlit as st
from src.services.auth_service import revoke_session
from src.services.entitlement_service import check_entitlement, redeem_token
from src.ui.theme import get_sidebar_bull_svg


def render_sidebar(user, is_visitor: bool = False, visitor_token: str = "") -> str:
    """Render dark navy sidebar navigation matching the approved reference screenshot."""
    active_view = st.session_state.get("active_nav_view", "dashboard")

    with st.sidebar:
        # Top Logo: Teal upward-trending chart icon + Two-line Stock Research Agent branding
        st.markdown(
            """
            <div style="text-align: center; padding: 0.5rem 0 1.25rem 0;">
                <div style="display: flex; justify-content: center; margin-bottom: 0.5rem;">
                    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="20" x2="18" y2="10"></line>
                        <line x1="12" y1="20" x2="12" y2="4"></line>
                        <line x1="6" y1="20" x2="6" y2="14"></line>
                        <path d="M4 14L12 4L18 10L22 6"></path>
                    </svg>
                </div>
                <div style="color: #FFFFFF; font-size: 1.15rem; font-weight: 700; line-height: 1.25; letter-spacing: -0.01em;">
                    Stock Research<br><span style="color: #F8FAFC;">Agent</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Navigation Options matching screenshot icons
        nav_options = [
            "🏠 Dashboard",
            "🕒 Research History",
            "📑 Saved Reports",
            "⚙️ Settings",
        ]
        if user and not is_visitor and user.role == "admin":
            nav_options.append("🛡️ Admin Console")

        current_idx = 0
        if active_view == "history":
            current_idx = 1
        elif active_view == "saved_reports":
            current_idx = 2
        elif active_view == "settings":
            current_idx = 3
        elif active_view == "admin" and "🛡️ Admin Console" in nav_options:
            current_idx = 4

        selected_nav = st.radio(
            "Navigation",
            options=nav_options,
            index=current_idx,
            label_visibility="collapsed",
            key="sidebar_navigation_radio",
        )

        if "Dashboard" in selected_nav:
            active_view = "dashboard"
        elif "History" in selected_nav:
            active_view = "history"
        elif "Saved Reports" in selected_nav:
            active_view = "saved_reports"
        elif "Settings" in selected_nav:
            active_view = "settings"
        elif "Admin" in selected_nav:
            active_view = "admin"

        st.session_state["active_nav_view"] = active_view

        # Spacing to push bull illustration toward the bottom
        st.markdown("<div style='margin-top: 5rem;'></div>", unsafe_allow_html=True)

        # Large glowing blue charging bull illustration with ascending bars at footer
        bull_html = f'<div style="text-align: center; display: flex; justify-content: center; padding-top: 1rem;">{get_sidebar_bull_svg()}</div>'
        st.markdown(bull_html, unsafe_allow_html=True)

    return active_view
