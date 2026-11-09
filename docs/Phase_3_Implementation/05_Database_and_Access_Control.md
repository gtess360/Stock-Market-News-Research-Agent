# Step 3.2 — Database, Authentication & Access Control (Security Verified)

**Document:** 05_Database_and_Access_Control.md  
**Phase:** 3.2 Database & Access Control  
**Date:** 2026-11-07  
**Status:** Security Hardened & Verified  

---

## 1. Executive Summary & Verification Scope
This document provides the technical specification and security verification audit of the database, authentication, quota state machine, and access control subsystems of the **Stock Market News Research Agent**.

Following an exhaustive security audit across 7 critical domains, defenses were verified and strengthened to eliminate privilege escalation, brute-force attacks, concurrent submission quota bypasses, token hijacking, and transaction lock contention.

---

## 2. Seven Core Security Domains & Verification Findings

### Domain 1: Login Rate Limiting, Password Security, Session Expiration & Account Recovery
- **Password Complexity:** Enforces NIST-aligned strength rules: minimum 8 characters, at least one letter, at least one number or symbol, and explicit rejection of dictionary/common passwords (`password123`, `admin123`, etc.).
- **Scrypt Key Derivation:** Uses `hashlib.scrypt` with parameters $N=16384, r=8, p=1$ and 16-byte random salts. Verification employs constant-time comparison `hmac.compare_digest`.
- **Brute-Force Rate Limiting:** Backed by the `login_attempts` table. Tracks failed login attempts per email. If 5 failed attempts occur within a rolling 15-minute window, the account is locked for the remainder of the window, rejecting subsequent attempts with `PermissionError` and explicit cooldown feedback.
- **Session Lifecycle & Invalidation:** Server-side sessions in `user_sessions` feature a 24-hour expiration window. Calling `revoke_session` permanently revokes the bearer token hash.
- **Account Recovery (Password Reset):** A secure password reset flow (`request_password_reset`, `reset_password_with_token`) uses single-use SHA-256 hashed tokens with a 30-minute expiration window. When a password is reset, all existing active sessions for that user are immediately revoked in the database.

### Domain 2: Concurrent Job Submission & Quota Bypass Prevention
- **The Vulnerability Checked:** In a naive implementation, a user with 1 remaining free credit could submit 10 concurrent requests at the exact same millisecond before any complete.
- **Strengthened Defense (Two-Tier Enforcement):**
  1. **Submission-Time Concurrency Cap:** In `create_research_job`, the system queries the count of active uncompleted jobs (`requested`, `validating`, `authorized`, `collecting`, etc.). If `(free_success_count + active_count) >= 3`, the submission is blocked immediately with `PermissionError`.
  2. **Completion-Time Atomic Conditional Debit:** When completing a job, debiting executes via conditional SQL:
     ```sql
     UPDATE usage_accounts
     SET free_success_count = free_success_count + 1,
         updated_at = ?,
         version = version + 1
     WHERE user_id = ? AND free_success_count < 3;
     ```
     If another thread claimed the final slot, `cursor.rowcount == 0`, immediately failing the job with error code `'QUOTA_EXCEEDED'` and preventing counter overflow.

### Domain 3: Access Token Ownership, Expiration, Revocation & Leakage Defense
- **Entropy & Prefixes:** High-entropy random tokens (`sk_res_...`, 256 bits of entropy) are generated via `secrets.token_urlsafe(32)`.
- **Digest-Only Storage:** Plaintext tokens are returned exactly once upon creation. Only SHA-256 digests are stored in `access_tokens`.
- **Ownership Isolation:** Tokens can be pre-assigned to a specific user or bound upon redemption. If User B attempts to redeem a token bound to User A, the transaction is rejected.
- **Expiration & Immediate Revocation:** Both `redeem_token` and `check_entitlement` verify that `revoked_at IS NULL` and `(expires_at IS NULL OR expires_at > now)`. Revoking a token takes immediate effect.
- **Credential Leakage Prevention:** `audit_service.sanitize_metadata` automatically redacts keys containing `password`, `token`, `secret`, `raw_token`, and `key` to `[REDACTED]`.

### Domain 4: Administrator Authorization & Privilege Escalation Defense
- **The Vulnerability Checked:** Web registration must never allow users to self-assign the `admin` role.
- **Strengthened Defense:**
  - `register_user` strictly defaults to `role = "user"`. Attempting to register as `admin` raises `PermissionError`.
  - Administrator creation requires the explicit `bootstrap_admin_user` utility or elevation by an existing authenticated administrator via `promote_user_to_admin`.
  - Administrative endpoints (token issuance, revocation, and request review) enforce server-side role verification (`SELECT role FROM users WHERE id = ?`).

### Domain 5: SQLite Transaction Safety & Repeatable Migrations
- **Transaction Safety:** Managed via `src/database/connection.py` using `get_connection()` and `@contextmanager get_db_cursor()`.
- **Pragmas:** Every connection automatically enforces:
  - `PRAGMA foreign_keys = ON;`
  - `PRAGMA journal_mode = WAL;`
  - `PRAGMA synchronous = NORMAL;`
  - `timeout = 30.0` seconds to handle concurrent readers and writers without busy lock errors.
- **Repeatable Migrations:** The `schema_migrations` table tracks schema versions (`version = 2: Phase 3.2 Security Hardened Schema`). All table and index creation statements use `IF NOT EXISTS` and are verified to be fully idempotent.

### Domain 6: Streamlit Authentication State Across Refreshes & Restarts
- **Session Persistence:** Streamlit runs each user script sequentially in a browser session. When a user authenticates, a server-side session token is issued and stored in `st.session_state["session_token"]`.
- **Browser Refresh (F5):** Restores authentication by querying the database for the active unexpired bearer token.
- **Application Restart:** Because session records reside in SQLite (`user_sessions`), server restarts do not disconnect active users whose session tokens remain unexpired.
- **Multi-Tab Isolation:** Each browser tab maintains independent session state while sharing the central user database.
- **Explicit Logout:** Revokes the session record in the database, invalidating the session across all active browser windows.

### Domain 7: Production Deployment Limitations & Required Security Controls
1. **Database Scalability:** SQLite is limited to a single active writer. For horizontal multi-container deployments (e.g. Kubernetes, AWS ECS), the connection layer should migrate to PostgreSQL with a connection pooler (PgBouncer).
2. **Network Encryption:** Production environments must enforce TLS 1.3 / HTTPS. Session cookies must be marked `Secure; HttpOnly; SameSite=Strict`.
3. **Secret Vaults:** Production deployments should inject `OPENAI_API_KEY` and administrative signing secrets from a managed secret manager (AWS Secrets Manager, GCP Secret Manager, Vault) rather than `.env` files.
4. **Edge Rate Limiting:** In addition to application-level login throttling, an edge reverse proxy (Cloudflare, AWS WAF, Nginx) should enforce IP-level rate limits to defend against volumetric DDoS attacks.

---

## 3. Relational Schema Summary (12 Core Entities)

```
1. schema_migrations (version, applied_at, description)
2. users (id, auth_provider_subject, role, created_at, status)
3. user_credentials (user_id, password_hash, salt, algorithm, created_at, updated_at)
4. user_sessions (id, user_id, session_token_hash, created_at, expires_at, revoked_at)
5. login_attempts (id, subject, ip_address, attempted_at, success)
6. password_resets (id, user_id, reset_token_hash, created_at, expires_at, used_at)
7. usage_accounts (user_id, free_success_count, updated_at, version)
8. access_tokens (id, token_hash, token_prefix, issued_to_user_id, status, created_at, expires_at, revoked_at, issued_by_admin_id, redeemed_at)
9. token_requests (id, user_id, status, reason, requested_at, reviewed_at, reviewer_id)
10. research_jobs (id, user_id, idempotency_key, tab, ticker_list_json, start_at, end_at, horizon_days, status, created_at, completed_at, error_code, credit_debited)
11. source_records & research_reports (citations, reports, metadata)
12. audit_events (id, actor_user_id, action, subject_id, created_at, metadata_json)
```

---

## 4. Verification Test Evidence (28/28 Tests Passing)

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- .venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Tesse\Desktop\Data Science Portfolio_Nov2026\Stock_Market_News_Research_Agent
plugins: anyio-4.16.0, langsmith-0.14.17
collecting ... collected 28 items

tests/test_access_control.py::test_initial_free_quota PASSED             [  3%]
tests/test_access_control.py::test_free_quota_consumption PASSED         [  7%]
tests/test_access_control.py::test_concurrent_job_submission_cap PASSED  [ 10%]
tests/test_access_control.py::test_token_ownership_isolation PASSED      [ 14%]
tests/test_access_control.py::test_failed_and_duplicate_jobs_do_not_debit_credit PASSED [ 17%]
tests/test_access_control.py::test_token_request_and_admin_approval_flow PASSED [ 21%]
tests/test_access_control.py::test_token_revocation PASSED               [ 25%]
tests/test_access_control.py::test_token_expiration PASSED               [ 28%]
tests/test_access_control.py::test_unauthorized_admin_actions PASSED     [ 32%]
tests/test_access_control.py::test_audit_log_redaction PASSED            [ 35%]
tests/test_auth.py::test_password_hashing_and_verification PASSED        [ 39%]
tests/test_auth.py::test_password_complexity_rules PASSED                [ 42%]
tests/test_auth.py::test_privilege_escalation_prevention PASSED          [ 46%]
tests/test_auth.py::test_login_rate_limiting_defense PASSED              [ 50%]
tests/test_auth.py::test_password_recovery_and_session_invalidation PASSED [ 53%]
tests/test_auth.py::test_session_lifecycle PASSED                        [ 57%]
tests/test_basic.py::test_core_dependencies_importable PASSED            [ 60%]
tests/test_basic.py::test_project_structure_exists PASSED                [ 64%]
tests/test_basic.py::test_required_configuration_files_exist PASSED      [ 67%]
tests/test_basic.py::test_src_package_version PASSED                     [ 71%]
tests/test_basic.py::test_app_entrypoint_callable PASSED                 [ 75%]
tests/test_basic.py::test_streamlit_app_runtime_execution PASSED         [ 78%]
tests/test_concurrency.py::test_concurrent_quota_debiting_race_condition PASSED [ 82%]
tests/test_database.py::test_schema_initialization PASSED                [ 85%]
tests/test_database.py::test_repeatable_idempotent_migrations PASSED     [ 89%]
tests/test_database.py::test_foreign_key_enforcement PASSED              [ 92%]
tests/test_database.py::test_quota_check_constraint PASSED               [ 96%]
tests/test_database.py::test_cascade_delete_user PASSED                  [100%]

============================= 28 passed in 7.74s =============================
```
