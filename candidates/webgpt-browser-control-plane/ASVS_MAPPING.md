# Preliminary OWASP ASVS 5.0 Mapping

**Status:** `CANDIDATE_SELF_ASSESSMENT_NOT_INDEPENDENT_CERTIFICATION`

This map records where the candidate has evidence and where it does not. Requirement identifiers must be rechecked against the final ASVS 5.0.0 release document by the independent security lane before production promotion.

| Control area | Candidate mechanism | Evidence | Current gap |
|---|---|---|---|
| Architecture and threat model | Explicit trust boundaries, R0-R5 policy, fail-closed release gates | `THREAT_MODEL.md`, policy tests | Independent architecture review not run |
| Authentication | Mandatory HTTP bearer token; operator process boundary for stdio | HTTP negative tests | OAuth, workload identity, rotation, revocation, MFA/admin controls not deployed |
| Session management | Explicit browser session IDs, exact job-session binding, isolated contexts | MCP session tests, restart test | Real account/workspace attestation and multi-tenant isolation not run |
| Access control | Exact tool catalog, finite permits, risk ceiling, host/action/cost binding | permit and MCP tests | Production RBAC and tenant policy not deployed |
| Validation and encoding | JSON Schema tool validation, canonical Base64url tokens, duplicate-key rejection, URL normalization, exact-host allowlist | schema, token, HTTP, stdio, URL guard tests | Full parser differential and fuzz campaign not run |
| Stored cryptography | HMAC ledger and Ed25519 checkpoints | evidence/checkpoint tests | Managed KMS/HSM custody and external anchor not deployed |
| Error handling and logging | Structured failure codes, secret redaction, hash-chained evidence | redaction/evidence tests | OTel exporter, retention, privacy and legal review not run |
| Data protection | Secret-shaped input block, credentials entered directly by user, bounded evidence | policy/security tests | Real screenshots/traces under authenticated accounts not reviewed |
| Communications | HTTPS-only target policy, bearer-authenticated local MCP HTTP | HTTP and URL tests | Secure MCP Tunnel and production TLS termination not deployed |
| Malicious input | Prompt-injection boundary, no web-content authority, no generic eval/click | security regressions, tool catalog | Hostile real-site and penetration campaign not run |
| Business logic | One-shot approvals, dual control, exact cost/currency, idempotency | permit/orchestrator tests | Real provider reconciliation and uncertain-response tests not run |
| Files and resources | Upload root restriction, normalized download filename, payload caps | adapter contract tests | Archive bomb, quota exhaustion, malware scanning not fully tested |
| API and web service | JSON-RPC validation, protocol version, Origin/Host/CORS checks, per-principal tool allowlist, rate/capacity limits, streaming request cap, batch cap | MCP HTTP and real-process tests | OAuth/workload identity, distributed abuse controls and external WAF not deployed |
| Configuration | Explicit encoded keys, wildcard rejection, fail-closed env loading | settings tests | Production secret store, config signing and drift monitor not deployed |

No row above may be interpreted as ASVS certification. The independent Astra security lane must produce a requirement-by-requirement verdict and reproduce the evidence.
