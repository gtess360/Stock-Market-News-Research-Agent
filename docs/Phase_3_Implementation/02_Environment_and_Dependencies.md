# Environment and Dependencies

**Document:** 02_Environment_and_Dependencies.md  
**Phase:** 3.1 Project Setup  
**Date:** 2026-11-07  
**Status:** Completed  

---

## 1. Environment Baseline
- **Operating System:** Microsoft Windows
- **Python Runtime:** Python 3.12.10 (64-bit)
- **Virtual Environment Directory:** `.venv/`
- **Package Manager:** `pip` (v26.3+)
- **IDE / Environment Integration:** `.vscode/settings.json` configured for Antigravity and VS Code with pytest integration.

---

## 2. Dependency Specification (`requirements.txt`)

The core dependency stack has been selected to ensure mutual compatibility under Python 3.12 without bloat:

```text
# Web Dashboard & Visualizations
streamlit>=1.40.0
plotly>=5.24.0

# Agent Orchestration & LLM Provider
langgraph>=0.2.0
langchain-openai>=0.2.0
openai>=1.50.0

# Schemas & Validation
pydantic>=2.9.0

# Configuration & Utilities
python-dotenv>=1.0.0

# Testing
pytest>=8.3.0
```

### Dependency Roles & Rationales
1. **`streamlit` (>=1.40.0):** Powers the responsive financial research dashboard, tab navigation, custom CSS styling, and reactive state management.
2. **`plotly` (>=5.24.0):** Provides interactive candlestick, line, and volume charts with hover cards and date window brushing.
3. **`langgraph` (>=0.2.0):** Manages the stateful, bounded research workflow (graph orchestration, step transitions, deterministic validation gates, error recovery).
4. **`langchain-openai` & `openai` (>=1.50.0):** Provides typed interfaces to OpenAI models with structured output capabilities.
5. **`pydantic` (>=2.9.0):** Enforces strict runtime data contract validation across news items, price bars, scenario outputs, and database models.
6. **`python-dotenv` (>=1.0.0):** Securely parses local `.env` configuration during development without exposing secrets.
7. **`pytest` (>=8.3.0):** Drives unit, integration, and end-to-end automated testing.
8. **`sqlite3`:** Native to Python 3.12 standard library; requires no third-party installation for the initial prototype.

---

## 3. Environment Activation and Verification
To activate the environment and execute commands:

### Windows PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
```

### Command Prompt
```cmd
.\.venv\Scripts\activate.bat
```

### Verification Commands
```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m streamlit run app.py
```

