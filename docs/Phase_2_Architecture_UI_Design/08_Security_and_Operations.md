# Security and Operations Design

## Controls
- Authentication, least-privilege roles, backend authorization for every research and admin endpoint.
- Server-side quotas and entitlement checks; secure token hashing, optional expiry and revocation.
- API keys in environment/secret manager, never committed or rendered to users.
- Prompt-injection defense: news article content is untrusted data; never follow embedded instructions.
- Allowlisted provider endpoints, validated ticker inputs, bounded dates, no arbitrary URL fetching.
- HTTPS, secure session cookies, CSRF protection where applicable, log redaction, audit trails.
- Per-user/provider rate limits, cost ceilings, request timeout, bounded retries, caching, and queue/concurrency caps.
- Data minimization, configurable retention and deletion, no brokerage credentials or trade execution.

## Monitoring
Track job status, latency, external API errors, token validation failures, tool calls, provider coverage, approximate model costs, citation failures, and quota events. Do not log access tokens or full personal information.
