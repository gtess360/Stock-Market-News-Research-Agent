# Step 3.1 — Project Setup Specification & Implementation

**Document:** 01_Project_Setup.md  
**Phase:** 3.1 Project Setup  
**Date:** 2026-11-07  
**Status:** Completed  

---

## 1. Objectives
Step 3.1 establishes the physical file structure, runtime environment, version controls, configuration templates, and entrypoint foundation for the **Stock Market News Research Agent**.

---

## 2. Directory Architecture
The project structure conforms to modern Python engineering standards and cleanly isolates source code, test suites, local storage, configurations, and phase documentation:

```
Stock_Market_News_Research_Agent/
├── .gitignore                      # Git exclusion rules (secrets, venvs, cache, DBs)
├── .env.example                    # Template for required environment variables
├── requirements.txt                # Pinned / bounded production and testing dependencies
├── app.py                          # Root convenience entrypoint for Streamlit execution
├── .vscode/
│   └── settings.json               # IDE & Antigravity Python interpreter and test configuration
├── src/
│   ├── __init__.py                 # Application root package marker
│   └── app.py                      # Streamlit application foundation shell
├── tests/
│   ├── __init__.py                 # Test suite package marker
│   └── test_basic.py               # Initial automated sanity and verification tests
├── data/
│   └── .gitkeep                    # Storage directory for local SQLite database and mock fixtures
├── config/
│   └── .gitkeep                    # Storage directory for YAML/JSON provider configurations
└── docs/
    ├── Phase_1_Requirements_Planning/  # Preserved Phase 1 requirements
    ├── Phase_2_Architecture_UI_Design/ # Preserved Phase 2 design specifications
    └── Phase_3_Implementation/        # Phase 3 engineering logs and documentation
        ├── 00_Implementation_Overview.md
        ├── 01_Project_Setup.md
        ├── 02_Environment_and_Dependencies.md
        ├── 03_Implementation_Progress.md
        └── 04_Issues_and_Resolutions.md
```

---

## 3. Environment & Security Configuration
1. **Virtual Environment Isolation:** An isolated Python 3.12 virtual environment is configured at `.venv/`.
2. **Interpreter Configuration:** `.vscode/settings.json` points directly to `${workspaceFolder}/.venv/Scripts/python.exe`, activates pytest, and configures `src` on the analysis path.
3. **Secret Protection (`.gitignore`):** Strictly excludes `.env`, `*.db`, `*.sqlite3`, local caches, virtual environments, and credential files.
4. **Credential Template (`.env.example`):** Defines clear placeholder keys for OpenAI, SQLite database URLs, application environment flags, logging levels, and future provider keys.

---

## 4. Application Foundation
A minimal Streamlit application foundation is deployed at `src/app.py` with an entrypoint alias at `app.py`.
- **Page Configuration:** Sets broad layout (`layout="wide"`), custom title, and favicon.
- **Sidebar Navigation:** Renders primary navigation markers (Dashboard, Research History, Saved Reports, Settings).
- **Tab Containers:** Renders preview shells for **Stock News** and **Sentiment Research**, validating UI lifecycle without invoking paid or external services.

---

## 5. Automated Verification Test Suite
Initial automated tests located at `tests/test_basic.py` assert:
- Installation and importability of core frameworks (`streamlit`, `langgraph`, `plotly`, `openai`, `pydantic`, `sqlite3`, `pytest`).
- Integrity of required root directories (`src`, `tests`, `data`, `config`, `docs`).
- Existence of required repository configuration files (`.gitignore`, `.env.example`, `requirements.txt`).
- Initialization of `src` package metadata.
- Executability of `src.app.main`.

