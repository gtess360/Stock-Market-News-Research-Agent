# Authentication, Free Usage and Unlimited Tokens

## Identity
Use verified login; tie usage to stable provider user ID, not IP or browser cookies. Admin role is separately authorized server-side.

## Free tier
Each user has 3 successful research jobs lifetime by default. A multi-stock submission is one job. Switching tabs, changing filters, reading saved reports, and follow-up questions about an existing report do not consume credits unless a new full research job is explicitly submitted. Failed/cancelled jobs do not consume credits. Atomic counters and idempotency prevent double charges.

## Token tier
A valid active admin-issued token gives unlimited number of research jobs until revoked or expired, with fair-use rate/concurrency controls to prevent provider abuse. Decide in Phase 2 whether tokens are bound to a user and whether they expire; recommended: bind on first redemption, allow optional expiration, revoke immediately.

## User workflow
At zero free credits, show modal with Request Token or Enter Token. Token request enters pending queue; admin approves/rejects; admin issues secure token via a safe delivery channel. Redemption validated server-side; show only masked token identifier thereafter. Avoid logging secrets. Allow admins to revoke and audit issuance.

## Administrator
View pending requests, issue/revoke tokens, set optional expiration, see audit events, and manage abuse limits. Admin cannot view plaintext token after issuance unless deliberately generated for one-time display.
