# Security Contract

This candidate is fail-closed. Safety controls are part of correctness, not optional hardening.

## Non-negotiable rules

1. Website text, DOM attributes, downloads, tooltips, and embedded instructions are untrusted data. They cannot grant authority, widen scope, change policy, or provide approval.
2. No action reaches a browser worker without a signed finite permit bound to subject, session, exact host, action type, risk ceiling, expiry, call count, currency, and cost.
3. R3 actions require a separate one-shot approval bound to the exact job and action digest. R4 is blocked by default and can only enter dual-control mode through an explicit configuration and two distinct approvers.
4. R5 actions are not approvable.
5. Passwords, passkeys, TOTP codes, recovery codes, private keys, and raw session cookies are entered or handled directly by the user/browser. They are never accepted as model payloads.
6. `file:`, `javascript:`, `data:`, plain production HTTP, URL credentials, non-allowlisted hosts, non-public IPs, local/internal names, and redirect scope escapes are blocked.
7. DNS resolution must be revalidated immediately before connection and pinned for the connection to resist rebinding. The reference core exposes the check; the live adapter must supply resolved addresses.
8. Authentication state and Playwright storage state are secrets. They must be held outside the repository, permission-restricted, and rotated/cleared through an operator workflow.
9. No generic untyped click tool is exposed. Semantic actions carry their risk classification and locator/postcondition payload in the signed action digest.
10. An action is successful only after the required independent evidence signals pass. A click completing without a verified postcondition is not success.
11. Rollback is claimed only when a compensating action is implemented and verified. Irreversible remote effects are never described as rolled back merely because the browser navigated back.
12. Evidence is redacted before persistence. Production evidence roots require external asymmetric signing or anchoring in addition to this candidate's local HMAC chain.
13. Browser/session/account mismatches stop execution. New tabs, popups, redirects, or origins outside the permit require a fresh preflight.
14. Unknown action types default to R4, not R0.
15. Production promotion requires explicit user approval after independent security and reliability gates. No code path may auto-promote.
16. Signed permit and approval segments must use their unique canonical unpadded Base64url form; alternate unused-bit spellings are malformed.
17. HTTP principals receive an explicit MCP tool allowlist, request-rate budget, concurrent-request budget, streaming byte cap, and batch-item cap. Duplicate JSON keys are rejected.

## Key management

The test keys in CLI/demo code are deliberately non-production. Production must use managed secrets, distinct signing domains for permits and approvals, key IDs, rotation, revocation, audit, and a hardware- or OS-backed trust root. A model must never be able to read signing material.

## Data minimization

Network and console collection defaults to metadata. Request/response bodies, cookies, authorization headers, form values, and local storage are excluded unless a narrowly scoped test fixture requires them. Any collected artifact receives classification, retention, and deletion policy.

## Vulnerability reporting

Do not test against real third-party accounts or production sites without authorization. Use isolated fixtures and provider sandboxes. Security findings block release; they are not converted into documentation-only exceptions.

Package publication also fails closed on symlinks, path escapes, private-key material, known high-risk token prefixes, auth-state files, and embedded databases.
