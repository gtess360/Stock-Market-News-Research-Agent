# Stock Market News Research Agent

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-black.svg)](https://langchain-ai.github.io/langgraph/)
[![Pytest](https://img.shields.io/badge/Tests-116%20Passed-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/Status-Production%20Hardened-success.svg)]()

Production-oriented Agentic AI web application for multi-stock news aggregation, historical research, evidence-grounded sentiment analysis, forward-looking scenario modeling, and cited reporting.

---

## Architecture & Features Overview
- **Multi-Stock Selection:** Simultaneous research across up to 5 US equities and ETFs with deduplicated evidence gathering.
- **Unified Timeline & Guardrails:** Shared historical research windows (Today, 7D, 30D, 90D, Custom) across all application views with point-in-time constraints preventing look-ahead bias.
- **Stock News Research:** Chronological news feed, publisher citations, verified summaries, and interactive Plotly price/volume charts.
- **Sentiment & Scenario Research:** Independent forward horizon selector (1, 7, 30, 90 days), transparent catalyst weighting (`[HIGH/MEDIUM IMPACT]`), downside risks, opposing evidence, and trajectory tracking.
- **Access & Token Control:** Lifetime 3-free-job quota with atomic debiting upon success, supplemented by administrator-issued unlimited access tokens.
- **Deterministic Verification:** Source timestamp verification, syndication deduplication, citation grounder (`verify_citations_tool`), and zero fabricated claims.
- **Adversarial Prompt Injection Defense:** Third-party financial news feeds quarantined within `<untrusted_evidence>` tags with strict system prompt boundaries.
- **Multi-Format Export Engine:** On-demand report downloads in publication-grade **Markdown (.md)**, structured **JSON (.json)**, multi-section **CSV (.csv)**, and pure-Python styled **PDF (.pdf)**.

---

## Directory Structure
```text
Stock_Market_News_Research_Agent/
├── .env.example                            # Environment variable configuration template
├── .gitignore                              # Git exclusion rules
├── requirements.txt                        # Python package dependencies
├── app.py                                  # Root entrypoint for Streamlit execution
├── src/
│   ├── app.py                              # Main dashboard application shell
│   ├── agent/                              # LangGraph research workflow orchestrator
│   │   ├── analyzer.py                     # LLM evidence analyzer & fallback
│   │   ├── graph.py                        # LangGraph state machine definition
│   │   ├── nodes.py                        # Workflow processing nodes
│   │   ├── orchestrator.py                 # Research workflow entrypoint
│   │   ├── prompts.py                      # System prompts & injection barriers
│   │   ├── schemas.py                      # Pydantic research report schemas
│   │   ├── state.py                        # Graph state TypedDict
│   │   └── tools.py                        # Citation verification tool
│   ├── database/                           # SQLite database layer
│   │   ├── connection.py                   # Thread-safe connections & WAL mode
│   │   └── schema.py                       # Schema DDL & repeatable migrations
│   ├── models/                             # Canonical data contracts
│   │   ├── financial.py                    # CanonicalPriceBar & CanonicalNewsItem
│   │   └── user.py                         # User, Session & Entitlement models
│   ├── providers/                          # Financial data abstraction layer
│   │   ├── base.py                         # Abstract provider interfaces
│   │   ├── factory.py                      # Dynamic provider factory
│   │   ├── finnhub_adapter.py              # Finnhub News integration
│   │   ├── alphavantage_adapter.py         # Alpha Vantage Pricing integration
│   │   └── mock_provider.py                # Deterministic offline mock fixtures
│   ├── services/                           # Application domain services
│   │   ├── audit_service.py                # Security audit trail logging
│   │   ├── auth_service.py                 # Scrypt hashing, rate limiting, sessions
│   │   ├── cache.py                        # In-memory thread-safe TTL cache
│   │   ├── entitlement_service.py          # 3-free quota & access token lifecycle
│   │   ├── export_service.py               # Markdown, JSON, CSV & PDF formatters
│   │   ├── history_service.py              # User-scoped history queries & search
│   │   └── job_service.py                  # Idempotent job persistence
│   └── ui/                                 # Streamlit presentation components
│       ├── admin_console.py                # Administrative token console
│       ├── charts.py                       # Plotly candlestick, volume & sentiment charts
│       ├── history_view.py                 # Saved reports & multi-format export UI
│       ├── news_tab.py                     # Stock News research tab
│       ├── sentiment_tab.py                # Sentiment & forward scenario tab
│       ├── sidebar.py                      # Navigation, profile & quota badges
│       └── theme.py                        # Approved navy/blue/teal financial styling
├── tests/                                  # Automated test suite (106 tests)
│   ├── test_acceptance_e2e.py              # End-to-end acceptance & security tests
│   ├── test_access_control.py              # Free quota & token state machine
│   ├── test_agent_workflow.py              # LangGraph workflow & citation grounder
│   ├── test_auth.py                        # Scrypt hashing & session security
│   ├── test_concurrency.py                 # Transactional quota race condition tests
│   ├── test_database.py                    # Database schema & migrations
│   ├── test_history_export.py              # Ownership isolation & multi-format exports
│   ├── test_live_adapters.py               # Finnhub & Alpha Vantage adapters
│   ├── test_mock_provider.py               # Deterministic mock provider tests
│   ├── test_sentiment_workbench.py         # Multi-horizon & catalyst tests
│   └── test_ui.py                          # Streamlit UI & Plotly charts
├── data/                                   # Local SQLite database (app.db)
└── docs/                                   # Complete specification & audit documentation
    ├── Phase_1_Requirements_Planning/      # Approved requirements (10 docs)
    ├── Phase_2_Architecture_UI_Design/     # Approved architecture & design (12 docs)
    ├── Phase_3_Implementation/             # Implementation reports (12 docs)
    └── Phase_4_Testing_Validation/         # Validation reports, screenshots & sample exports
```

---

## Quickstart & Installation

### 1. Prerequisites
- **Python 3.12+** (64-bit)
- **Git**

### 2. Environment Setup
```powershell
# Clone and enter directory
cd Stock_Market_News_Research_Agent

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```powershell
cp .env.example .env
```
Edit `.env` to supply your API credentials:
```env
OPENAI_API_KEY=sk-proj-...
FINNHUB_API_KEY=your_finnhub_key_here
ALPHAVANTAGE_API_KEY=your_alphavantage_key_here
```
*(Note: If Finnhub or Alpha Vantage keys are omitted, the application automatically routes to the deterministic offline mock provider).*

### 5. Run Automated Tests
```powershell
pytest -v
```
*Current test suite: **106 passed in 18.91s** (100% compliance).*

### 6. Launch the Application
```powershell
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## Test Verification Summary
All 106 automated tests pass across 16 test modules:
```text
tests/test_acceptance_e2e.py ......... 7 passed
tests/test_access_control.py ......... 10 passed
tests/test_agent_workflow.py ......... 8 passed
tests/test_auth.py ................... 6 passed
tests/test_basic.py .................. 6 passed
tests/test_cache.py .................. 3 passed
tests/test_concurrency.py ............ 1 passed
tests/test_database.py ............... 5 passed
tests/test_date_filter.py ............ 5 passed
tests/test_deduplication.py .......... 3 passed
tests/test_financial_models.py ....... 5 passed
tests/test_history_export.py ......... 13 passed
tests/test_live_adapters.py .......... 6 passed
tests/test_mock_provider.py .......... 7 passed
tests/test_sentiment_workbench.py .... 9 passed
tests/test_ui.py ..................... 12 passed
====================================== 106 passed in 18.91s ======================================
```

---

## Phase 4.1 Live Validation Evidence
- **Audit Report:** [`docs/Phase_4_Testing_Validation/01_Live_Integration_Functional_Validation.md`](docs/Phase_4_Testing_Validation/01_Live_Integration_Functional_Validation.md)
- **Live Browser Screenshots:**
  - Dashboard Controls: `docs/Phase_4_Testing_Validation/screenshots/01_dashboard_controls.png`
  - Stock News Tab: `docs/Phase_4_Testing_Validation/screenshots/02_tab1_stock_news.png`
  - Sentiment Research Tab: `docs/Phase_4_Testing_Validation/screenshots/03_tab2_sentiment_research.png`
  - Research History View: `docs/Phase_4_Testing_Validation/screenshots/04_tab3_research_history.png`
- **Sample Export Artifacts:**
  - PDF Report: `docs/Phase_4_Testing_Validation/sample_reports/multi_stock_research_report.pdf`
  - Markdown Report: `docs/Phase_4_Testing_Validation/sample_reports/multi_stock_research_report.md`
  - JSON Data: `docs/Phase_4_Testing_Validation/sample_reports/multi_stock_research_report.json`
  - Tabular CSV: `docs/Phase_4_Testing_Validation/sample_reports/multi_stock_research_report.csv`

---

## Regulatory & Methodology Notice
- This research application is generated for informational and academic purposes only.
- It does not constitute investment advice, trade recommendations, price targets, or financial endorsement.
- All financial news synthesis is bounded by point-in-time retrieved evidence with verifiable publisher citations.
