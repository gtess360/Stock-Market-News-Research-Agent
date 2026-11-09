# Phase 2 Architecture Review & Approval
Status: Awaiting user approval.

## Review checklist
- [ ] Architecture uses one bounded research orchestrator and specialized read-only tools.
- [ ] Two-tab decorative dashboard matches approved concept.
- [ ] Shared tickers and historical research filters persist across tabs.
- [ ] Sentiment tab has independent 1/7/30/90-day forward horizon.
- [ ] Three successful free jobs; unlimited valid-token jobs; server-side enforcement.
- [ ] Admin token request, issue, revoke, expiry and audit workflows defined.
- [ ] News/market provider coverage, costs and licensing evaluated before implementation.
- [ ] Source timestamps, citations, uncertainty, historical integrity and no-trading rules included.
- [ ] Testing, monitoring, prompt injection protection and API cost controls included.

## Open decisions for approval
1. Authentication provider (recommended: managed OAuth sign-in).
2. Token expiration policy (recommended: optional administrator-configured expiration, user-bound token).
3. Maximum tickers per research job (recommended initial cap: 5 to control provider costs; adjust after testing).
4. News/market data provider after evaluating historical access, redistribution rights and pricing.
5. Deployment target and whether SQLite should be replaced by PostgreSQL at launch.

Approval recorded by user after review. No Phase 3 code implementation before approval.
