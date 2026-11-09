# Database Design

## Entities (proposed)
- users: id, auth_provider_subject(unique), role, created_at, status.
- usage_accounts: user_id(unique), free_success_count(0..3), updated_at, version.
- access_tokens: id, token_hash(unique), issued_to_user_id(nullable), status, created_at, expires_at(nullable), revoked_at, issued_by_admin_id, redeemed_at.
- token_requests: id, user_id, status(pending/approved/rejected), reason, requested_at, reviewed_at, reviewer_id.
- research_jobs: id, user_id, idempotency_key(unique per user), tab, ticker_list_json, start_at, end_at, horizon_days(nullable), status, created_at, completed_at, error_code, credit_debited.
- source_records: id, job_id, ticker, source_url, publisher, published_at, retrieved_at, evidence_type, normalized_metadata_json.
- research_reports: id, job_id, report_json, markdown, generated_at, model_version, prompt_version, limitations_json.
- audit_events: id, actor_user_id, action, subject_id, created_at, metadata_json (redacted).

## Rules
Use foreign keys and unique indexes; transactionally enforce free quota and idempotency to prevent concurrent double spending. Access tokens are high-entropy random secrets; store only keyed/slow hashes as appropriate, never plaintext. Do not store payment card information. Apply retention/deletion policies to user and research data. SQLite works for a local single-instance prototype; move to PostgreSQL for multi-instance deployment and reliable concurrent writes.
