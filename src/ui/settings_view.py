"""Settings and provider configuration view."""
import os
import streamlit as st


def render_settings_view() -> None:
    """Render application settings and data provider status."""
    st.subheader("⚙️ Settings & Financial Data Providers")
    st.caption("Manage data provider modes, verify API credentials, and review rate limit settings.")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("#### 🔌 Active Provider Mode")
            current_mode = st.session_state.get("provider_mode", "mock")

            mode_selection = st.radio(
                "Select Provider Mode",
                options=["mock", "live"],
                index=0 if current_mode == "mock" else 1,
                format_func=lambda m: "🧪 Mock Provider (Deterministic Local Fixtures)" if m == "mock" else "🌐 Live Providers (Finnhub & Alpha Vantage)",
                key="settings_provider_mode_radio",
            )
            if mode_selection != current_mode:
                st.session_state["provider_mode"] = mode_selection
                st.success(f"Provider mode updated to: {mode_selection.upper()}")
                st.rerun()

            if mode_selection == "mock":
                st.info(
                    "**Mock Provider:** Uses deterministic local financial fixtures for stocks like AAPL, MSFT, and NVDA. "
                    "Ideal for rapid local development, CI/CD testing, and offline demonstrations without consuming API quotas."
                )
            else:
                st.warning(
                    "**Live Provider Mode:** Connects to Finnhub for financial news and Alpha Vantage for daily prices. "
                    "Requires valid API keys set in your `.env` or system environment."
                )

    with col2:
        with st.container(border=True):
            st.markdown("#### 🔑 Provider API Keys Status")
            keys = {
                "OpenAI API Key": bool(os.getenv("OPENAI_API_KEY")),
                "Finnhub API Key": bool(os.getenv("FINNHUB_API_KEY")),
                "Alpha Vantage API Key": bool(os.getenv("ALPHA_VANTAGE_API_KEY")),
            }
            for name, is_set in keys.items():
                status_icon = "🟢 Configured" if is_set else "⚪ Not Set (Mock Available)"
                st.markdown(f"- **{name}:** {status_icon}")

            st.caption(
                "Never commit API keys to version control. Keys are safely loaded from `.env` or environment variables."
            )

