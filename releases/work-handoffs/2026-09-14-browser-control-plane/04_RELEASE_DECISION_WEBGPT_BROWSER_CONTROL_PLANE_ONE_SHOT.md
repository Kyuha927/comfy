# ONE-SHOT: Independent Release Decision

Act as the final independent release authority. Make no implementation changes. Do not rely on author claims, test counts alone, Draft PR labels, or reconstruction success. Verify evidence directly and fail closed.

## Inputs

Read `00_READ_FIRST_WEBGPT_BROWSER_CONTROL_PLANE.md`, all candidate documents, source identity, implementation evidence, security report, reliability report, operational runbook, migration and rollback proof, live-tenant receipts, and external evidence anchor proof.

## Mandatory release gates

Require all of the following:

- Source and dependency identity reproducible from a clean environment.
- Official OpenAI integration route and Secure MCP Tunnel requirements reconciled with the actual deployed transport.
- Production RBAC, key separation, secret storage, rotation, revocation, tenant isolation, and least privilege demonstrated.
- R0-R5 policy, exact-host egress, private-network denial, permits, approvals, dual control, idempotency, revision authority, rollback, quarantine, and evidence chain tested adversarially.
- R3/R4 evidence includes DOM/accessibility, rendered pixels, and provider/network receipt.
- OWASP ASVS-oriented review has no unresolved Critical or High issue.
- Crash, reboot, disk-full, partition, duplicate delivery, backup/restore, migration/rollback, and at least 24-hour soak gates pass.
- Independent operators can diagnose and recover without editing the database or weakening policy.
- Release artifact, SBOM, provenance, signatures, checksums, change log, support policy, incident response, and rollback package are complete.
- The candidate runs in a disposable production-like tenant before any real-account enablement.

## Decision rules

- Any missing, stale, contradictory, unverifiable, or author-only evidence is a failed gate.
- A blocked environment is not a pass.
- Offline fixture success is not live integration success.
- An MCP schema is not a working MCP transport.
- A Draft PR is not a release.
- Do not downgrade a blocker merely because exploitation was not demonstrated.

## Output

Produce a signed release decision matrix with one verdict only:

- `PRODUCTION_RELEASE_APPROVED`, only when every mandatory gate passes with independent evidence; or
- `PRODUCTION_RELEASE_BLOCKED`, listing exact failed gates, evidence required, and the smallest safe next validation.

Do not merge, publish, or enable writes as part of this lane. Execution of an approved release requires a separate explicit owner action.
