# Issues, Inconsistencies, and Design Resolutions

**Document:** 04_Issues_and_Resolutions.md  
**Project:** Stock Market News Research Agent  
**Last Updated:** 2026-11-08  
**Current Milestone:** Step 3.7 Completed  

---

## Step 3.1: Project Setup & Baseline

### Issue 1: Environment Reproducibility across OS Boundaries
- **Observation:** Differences between Windows and Unix virtual environments (`Scripts` vs `bin`) and terminal encodings could cause test invocation failures.
- **Resolution:** Explicitly standardized `.venv` activation paths, configured UTF-8 output encoding, and pinned dependencies in `requirements.txt`.

---

## Step 3.2: Database, Authentication & Access Control

### Issue 1: Transaction Safety & Concurrency during Quota Debiting
- **Observation:** Concurrent job executions could lead to a race condition where a user with 1 remaining credit submits two jobs in parallel, both passing the balance check.
- **Resolution:** Implemented an atomic `UPDATE usage_accounts SET used_requests = used_requests + 1 WHERE user_id = ? AND (used_requests + active_jobs) < total_allowed` inside an immediate transaction.

### Issue 2: Scrypt Parameters and Secure Password Hashing
- **Observation:** Default hashing without strict salt length and scrypt parameters leaves passwords vulnerable to rainbow tables.
- **Resolution:** Enforced `hashlib.scrypt` with 16-byte cryptographically secure salts (`os.urandom(16)`), `n=16384`, `r=8`, and `p=1`.

---

## Step 3.3: Financial News & Market Data Integrations

### Issue 1: Historical Look-Ahead Bias in News Retrieval
- **Observation:** Requesting "latest news" without point-in-time constraints allows future news to leak into historical analysis backtests.
- **Resolution:** Enforced rigorous upper and lower date boundaries on all provider adapters (`from_date` / `to_date`), strictly discarding any articles timestamped outside the evaluation window.

### Issue 2: Wire Syndication Duplication
- **Observation:** Financial news feeds frequently distribute identical syndicated articles across dozens of domains, skewing sentiment counts.
- **Resolution:** Built a multi-stage deduplication engine utilizing exact URL hashing, syndication cluster identifiers, and semantic headline similarity matching.

---

## Step 3.4: LangGraph Agent Workflow

### Issue 1: OpenAI SDK Structured Output Integration with LangGraph
- **Observation:** OpenAI SDK v1.x `client.beta.chat.completions.parse` requires strict Pydantic schemas, but LangGraph nodes exchange generalized state dictionaries.
- **Resolution:** Formatted the LLM call node to parse directly into canonical Pydantic models (`NewsResearchReport`, `SentimentResearchReport`), converting to dicts prior to state merging.

### Issue 2: Markdown Delimiter Matching in Test Assertions
- **Observation:** The generated report formatted the forward horizon header as `**Forward Horizon:** 30 Days`, causing an exact substring test assertion `assert "Forward Horizon: 30 Days" in markdown` to fail due to the markdown bold markers enclosing the colon.
- **Resolution:** Adjusted the test assertion to check `**Forward Horizon:** 30 Days` matching the exact markdown structure.

### Issue 3: LangGraph 1.2+ Top-Level Version Attribute
- **Observation:** In LangGraph 1.2.20, `langgraph.__version__` is not exposed at top-level package namespace, causing an attribute error if queried.
- **Resolution:** Confirmed graph compilation and execution rely directly on `from langgraph.graph import StateGraph, START, END`, which is fully supported and stable across all runtime environments.

---

## Step 3.5: Streamlit Dashboard & UI Layer

### Issue 1: `use_container_width` Deprecation Compliance
- **Observation:** Streamlit (>=1.57) deprecated `use_container_width=True` on buttons, link buttons, and form submit buttons in favor of `width="stretch"` or `width="content"`.
- **Resolution:** Standardized all UI components to use `width="stretch"` on buttons, charts, and dataframes, maintaining clean layout behavior without deprecation warnings.

### Issue 2: `AppTest.from_file` Script Path Resolution
- **Observation:** Calling `AppTest.from_file("app.py")` inside `tests/test_ui.py` caused a `FileNotFoundError` because `AppTest` resolves relative paths against the calling test file's directory (`tests/app.py` instead of root `app.py`).
- **Resolution:** Resolved the absolute path to the root entrypoint: `APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")`.

### Issue 3: Database Isolation in Streamlit Runtime Testing
- **Observation:** `AppTest` executes `app.py` in an isolated simulation thread, but backend service calls fell back to the default `data/app.db`, bypassing temporary test fixtures.
- **Resolution:** Updated `get_db_path()` in `src/database/connection.py` to prioritize `os.getenv("DATABASE_PATH")`, allowing `monkeypatch.setenv("DATABASE_PATH", str(db_file))` to seamlessly isolate database state during simulated UI runs.

### Issue 4: Dynamic Canonical Model Attribute Access in UI Cards
- **Observation:** Different data sources and schemas represent tickers as either `symbol` or `ticker`, and summaries as `summary_or_description` or `summary`. Direct attribute access risked `AttributeError` across heterogeneous test and live payloads.
- **Resolution:** Implemented defensive attribute extraction (`getattr(t, "symbol", getattr(t, "ticker", ""))`) across overview metrics, charts, and news timeline feeds.

---

## Step 3.6: Sentiment Research Enhancements

### Issue 1: Conflation of Historical News Sentiment and Forward Scenario Outlook
- **Observation:** Preliminary implementations risked treating positive news coverage as synonymous with a forward bullish price forecast, violating financial compliance guardrails against ungrounded prediction.
- **Resolution:** Strictly decoupled the schemas into retrospective `current_news_sentiment` (`positive`, `negative`, `neutral`, `mixed`) and prospective `forward_scenario_outlook` (`bullish`, `bearish`, `neutral`, `mixed`), requiring horizon-specific scenario triggers and opposing counter-narratives for all outlooks.

### Issue 2: Artificial Precision / Fabricated Probability Percentages
- **Observation:** Certain commercial sentiment tools display arbitrary probability figures (e.g. "73.2% Bullish") that lack statistical calibration and mislead users into assuming algorithmic certainty.
- **Resolution:** Replaced all arbitrary probability percentages with transparent, auditable evidence metrics: qualitative evidence strength (`strong`, `moderate`, `weak`, `insufficient`), empirical source diversity counts, and recency distributions.

### Issue 3: Syndication Bias in Evidence Corroboration
- **Observation:** Wire syndication services frequently redistribute an identical article across dozens of regional outlets, risking artificial inflation of sentiment confidence scores.
- **Resolution:** Enhanced `analyze_stock_sentiment` to explicitly filter `is_duplicate` wire copies from corroboration counts and track `syndicated_duplicates_filtered` in the transparency metrics audit card.

---

## Step 3.7: Research History, Persistence & Multi-Format Export

### Issue 1: Multi-Cell Cursor Offset in `fpdf2` Producing Negative Margin Space
- **Observation:** In `fpdf2` (v2.9.0), calling `pdf.cell(5)` for indentation before calling `pdf.multi_cell(0, ...)` shifted the cursor coordinate `x` beyond the left margin. Because `multi_cell(0, ...)` defaults to calculating width from margins, this triggered `fpdf.errors.FPDFException: Not enough horizontal space to render a single character`.
- **Resolution:** Removed manual `cell(5)` offsets and incorporated bullet indentations directly into string payloads with explicit `new_x=XPos.LMARGIN, new_y=YPos.NEXT`, guaranteeing the cursor automatically resets to the left margin on subsequent lines.

### Issue 2: FPDF Unicode Font Compatibility with Non-Latin Characters
- **Observation:** Default core fonts in PDF engines (`Helvetica`, `Times`, `Courier`) use Latin-1 (ISO-8859-1) character encoding. Attempting to render non-Latin characters (smart quotes `“...”`, em-dashes `—`, or accents) triggered a `UnicodeEncodeError`.
- **Resolution:** Implemented defensive `.encode("latin-1", "replace").decode("latin-1")` sanitization across all dynamic user and agent strings prior to PDF rendering, ensuring uninterrupted PDF generation without encoding crashes.

### Issue 3: Idempotent Insertion of Duplicate Research Reports
- **Observation:** Re-running or re-persisting an identical research job could trigger a primary key uniqueness constraint violation on `research_reports.id` or duplicate foreign key rows.
- **Resolution:** Implemented `INSERT OR REPLACE INTO research_reports` in `src/agent/nodes.py` to ensure duplicate or updated job reports seamlessly overwrite prior records idempotently.

### Issue 4: Strict Quota Invariance on Report Reopening
- **Observation:** Loading a past research job into active view risked triggering new agent research execution pipelines or deducting additional user credits.
- **Resolution:** Built a dedicated session state restoration path in `history_view.py` that populates `st.session_state["research_results"]` from the existing persisted SQLite payload, bypassing LangGraph orchestration and preserving user credits with zero debit.

---

## Step 3.8: Production Hardening & Final Acceptance

### Issue 1: CanonicalNewsItem Field Validation in Test Harness
- **Observation:** Preliminary end-to-end fixtures constructed `CanonicalNewsItem` with abbreviated fields (`ticker`, `summary`), triggering Pydantic schema validation rejections due to missing required attributes (`ticker_association`, `retrieved_at_utc`, `provider_identification`).
- **Resolution:** Updated test fixtures to supply fully compliant `CanonicalNewsItem` objects matching the strict production schema.

### Issue 2: Role Decoupling for Retrospective Sentiment vs Prospective Outlook
- **Observation:** Test assertions initially checked for `bullish` in `current_news_sentiment`, which violated the architectural separation of retrospective news sentiment (`positive`, `negative`, `neutral`, `mixed`) from forward scenario outlooks (`bullish`, `bearish`, `neutral`, `mixed`).
- **Resolution:** Updated test assertions to validate against the correct respective enums, preserving strict financial compliance and preventing look-ahead conflation.

### Issue 3: Access Token Column Mapping
- **Observation:** SQL queries in test assertions attempted to query `access_tokens.user_id`, which caused an `OperationalError` because the database schema designates this column as `issued_to_user_id`.
- **Resolution:** Aligned query assertions with the normalized database schema column `issued_to_user_id`.

