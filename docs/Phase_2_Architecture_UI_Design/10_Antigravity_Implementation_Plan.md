# Antigravity Implementation Plan (Phase 3 Preview — No Coding Yet)

## Implementation sequence
1. Create Python project, separate .venv, lint/test tooling, .env.example, safe secret loading.
2. Implement DB schema, migrations, user identity, authorization and admin roles.
3. Implement three-free-jobs quota, idempotency, secure unlimited token lifecycle, request/approval screens.
4. Add provider interfaces and mocked fixtures; select providers only after licensing/cost review.
5. Implement LangGraph bounded research workflow, source normalization, citation verification, and report schema.
6. Implement Stock News tab with shared multi-stock and historical filters.
7. Implement Sentiment Research tab with independent future horizon and scenario reports.
8. Apply approved decorative UI design, responsive behavior, access badges and loading/error states.
9. Add persistence, research history, export, observability, tests and security hardening.
10. Run acceptance tests; provide test evidence, unresolved risks and documentation updates.

## Prompt policy
ChatGPT supplies copy-ready Antigravity prompts per milestone after Phase 2 approval. Antigravity generates code; ChatGPT does not supply source code. Do not implement unapproved changes or claim success without logs/tests.
