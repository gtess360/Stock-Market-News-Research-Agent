# System Architecture

## Logical layers
1. Streamlit UI: navigation, ticker chips, date filters, research tabs, progress, report viewer, usage badge.
2. Authentication and authorization service: account identity, server-side entitlement check, token redemption, admin roles.
3. Research service: validates input, starts idempotent research job, invokes LangGraph workflow, saves output.
4. Agent orchestration: LLM plans bounded research and selects approved read-only tools; state tracks stocks, dates, evidence, steps, costs, errors.
5. Tool adapters: ticker resolver, licensed news provider, market-price provider, optional events/calendar provider.
6. Deterministic validation: timestamps, URLs, duplicates, provenance, coverage, stale-data flags, citation integrity.
7. Storage: SQLite initially for users, jobs, entitlements, sources, results, token requests, audit records; encrypted secrets in environment/secret manager.
8. Export: Markdown/HTML/PDF optional later; first release Markdown and CSV/JSON as needed.

## Flow
User -> Streamlit -> auth/access check -> research job -> LangGraph -> external read-only APIs -> evidence validator -> report -> database -> UI.

## Constraints
- No trading or brokerage orders.
- No invented prices, news articles, URLs, or confidence scores.
- News and price sources must disclose publication time, retrieval time, and market data delay.
- Background jobs and concurrency limits are deployment-dependent; use bounded workers and avoid blocking the entire app.
- Maintain an explicit provider abstraction so sources can be swapped without rewriting the agent.
