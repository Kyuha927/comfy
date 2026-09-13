# ONE-SHOT: Implement and Integrate the WebGPT Browser Control Plane

You are the implementation owner for the reviewed `WebGPT Browser Control Plane 0.1.0a2` candidate. Work only on a candidate branch. Do not merge, release, enable production writes, weaken policy, bypass managed browser controls, reuse a personal profile, or modify the Blender bridge outside an explicitly required adapter boundary.

## Inputs

Read `00_READ_FIRST_WEBGPT_BROWSER_CONTROL_PLANE.md` and every canonical candidate document it names. Obtain the source archive from the originating conversation and require SHA-256 `30d29628edbdba943841fd7e7958972d393924fb57f59ec96a580e500a351d51` before extraction. Stop with `BLOCKED_SOURCE_IDENTITY_MISMATCH` on any mismatch.

## Required work

1. Preserve the R0-R5 risk model, unknown-to-R4 default, exact egress rules, finite HMAC permits, one-shot approvals, dual-control separation, durable idempotent jobs, tamper-evident evidence, rollback, and quarantine.
2. Implement a live MCP transport only through the currently documented OpenAI route. For local/private endpoints use the official Secure MCP Tunnel path. Do not invent a hidden browser-control API.
3. Add production-grade key separation and rotation, RBAC, environment isolation, secret storage, audit export, and externally anchored evidence checkpoints.
4. Keep Playwright-owned isolated contexts as the default. Treat existing signed-in Chrome/CDP access as an explicitly elevated mode with a narrower allowlist and stronger approval.
5. Implement bounded upload/download handling, redirect re-authorization, provider receipt adapters, visual-state checks, console/network capture, and deterministic terminal receipts.
6. Add an operator approval surface that displays exact host, action, payload digest, risk tier, cost ceiling, expiration, side effects, rollback limits, and evidence requirements.
7. Add migration, backup, restore, crash-recovery, and rollback procedures without changing an existing authoritative revision silently.

## Mandatory validation

- Run the full existing suite and preserve `73 PASS` or increase it.
- Add negative tests for permit replay, approval replay, concurrent double-consume, stale revision, duplicate delivery, redirect escape, DNS rebinding, private/link-local targets, prompt-injection authority escalation, forged receipts, corrupted evidence chain, secret leakage, and rollback failure.
- Run isolated real Chromium DOM, pixel, trace, download, upload, and recovery fixtures.
- Run live-network tests only in an authorized disposable test tenant. R3/R4 actions require provider/network receipt evidence and must quarantine when it is absent.
- Produce exact commands, exit codes, artifact hashes, screenshots or traces, and failure codes.

## Output

Commit code, tests, migration notes, operational runbook, updated threat model, updated release gates, and a machine-readable status report to the candidate branch. Open or update a Draft PR. Report `IMPLEMENTATION_COMPLETE_FOR_REVIEW`, `PARTIAL_WITH_BLOCKERS`, or a precise `BLOCKED_*` result. Never report production readiness; release authority belongs exclusively to the independent release lane.
