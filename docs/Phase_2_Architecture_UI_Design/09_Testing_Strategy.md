# Architecture and Test Strategy

## Unit tests
Ticker validation; date window logic; deduplication; sentiment output schema; citation validation; token state machine; entitlement counter; idempotent job submission.

## Integration tests
Mock news/price APIs; LangGraph tool routing; database transactions; user/admin authorization; token redemption and revocation; report persistence and export.

## End-to-end tests
Multi-select ticker flow; both tabs retain filters; custom date range; free request counter 3->2->1->0; blocked fourth job; valid token unlimited; expired/revoked blocked; research history and citations; provider outage/partial results.

## Evaluation
Create a fixed set of stock research questions with dated source fixtures. Score citation accuracy, claim grounding, time-window compliance, sentiment rationale, error handling, latency, and token cost. Backtest only with point-in-time evidence; no look-ahead leakage.

## Release gates
No critical security issues; no invented source URLs; authorization enforced server-side; quota races tested; representative UI accessible; providers comply with license terms; all mandatory tests pass. Record actual test results, not anticipated ones.
