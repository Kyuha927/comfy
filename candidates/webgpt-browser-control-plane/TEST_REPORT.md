# Test Report

**Candidate:** `0.3.0a1`
**Current environment:** isolated local reconstruction; use current generated receipts for exact runtime, command, test-count, and hash facts.
**Verdict:** `ISOLATED_CANDIDATE_VALIDATION_IN_PROGRESS_NOT_PRODUCTION`

## Current isolated candidate evidence

- Compilation of `src`, `tests`, and `scripts`: `PASS`.
- Jev/CUA boundary suite: `PASS`, 10 tests.
- Packaging-safety suite: `PASS`, 6 tests.
- Full unit/integration discovery: `PASS`, 125 tests in the current Phase-A
  verification run. The release-gate evidence also records 10 independent
  passing runs, 125 tests each (1,250 total), bound to the current source
  manifest.

The exact test count must be read from every current run receipt. It must not be
copied from the historical baseline evidence below. The current local
release-gate receipt additionally records MCP stdio and HTTP-process
acceptance, scoped static and secret scanning, a bounded 30-second burn-in,
and the source-bound repeated-suite check as `PASS_OFFLINE_ONLY`. Packaging,
safe fresh extraction, fresh extracted-source verification, remote-clone
verification, and local deployment acceptance remain pending until their
respective observed receipts are generated.

## Historical WBCP 0.2.0a1 baseline evidence — not current-candidate evidence

- Full Python unit/integration discovery: **111 tests PASS (historical baseline only)**.
- Python source compilation and JSON parsing: PASS.
- Legacy MCP `initialize`, 2026 `server/discover`, filtered `tools/list`, and typed `tools/call`: PASS.
- Newline-delimited MCP stdio roundtrip through a real child process: PASS.
- Authenticated Streamable HTTP POST `/mcp` through an actual loopback uvicorn child process: PASS.
- HTTP bearer authentication, exact Host allowlist, exact Origin allowlist, allowlisted CORS response, protocol-version rejection, bounded streaming request body, batch-item cap, notification 202 behavior, and batch handling: PASS.
- Authenticated principal tool allowlist, request-rate cap, and concurrent-request capacity guard: PASS.
- Duplicate JSON object keys are rejected on HTTP and stdio: PASS.
- Token issuance is not exposed as an MCP model tool: PASS.
- Session creation requires a finite permit and jobs remain bound to the exact browser session: PASS.
- Permit and approval Base64url segments must use one unique canonical encoding; alternate unused-bit spellings are rejected: PASS, including 50 repeated tamper runs.
- Consequential R3 authorization without a one-shot approval: correctly blocked.
- Consequential R3 execution requires DOM/accessibility, pixels, network success, and a non-empty provider receipt digest: PASS.
- Authorized durable job survives full runtime close/reopen and commits once; terminal replay returns the prior result: PASS.
- Ed25519 evidence-root checkpoint signing and tamper detection: PASS.
- Real Chromium offline DOM, rendered-pixel, and trace evidence: PASS.
- Consequential Chromium action without provider/network evidence: correctly quarantined.
- 30-second accelerated burn-in: **448 iterations, 0 failures, 0 leaked sessions, 3,136 valid evidence events**.
- Burn-in latency: p50 66.443 ms, p95 126.474 ms, p99 139.712 ms, max 198.628 ms.
- Static source security check: 0 findings for embedded secret shapes and dynamic `eval`/`exec` use.
- Whole-package secret/sensitive-file scan: PASS; no private-key material, known token prefixes, auth-state files, databases, or symlinks detected.
- CycloneDX 1.5 candidate SBOM, direct dependency/license inventory, candidate source manifest, and unsigned local provenance generated.

## Defects discovered and fixed during this pass

1. `PlaywrightBrowserAdapter._route_request` continued one allowed request twice. This could produce a route-already-handled failure in a real browser. It now continues exactly once and has a dedicated regression test.
2. Structural redaction interpreted long uppercase failure codes as token-shaped secrets. Public `code`, `failure_code`, `error_code`, `state`, and `status` values are now preserved while bearer, cookie, and credential material remains redacted.
3. The earlier MCP file was a contract only. The candidate now has executable stdio and authenticated HTTP JSON-RPC transports with protocol and tool-schema validation.
4. Process restart behavior was not discriminatingly tested. The suite now proves an authorized job can be reopened and committed without duplicate execution.
5. R3/R4 could previously accept `network_ok=true` without a non-empty provider receipt digest. The all-three gate now requires an actual receipt digest.
6. A noncanonical final Base64url character could sometimes decode to the same signature bytes because of unused padding bits. Signed-token decoding now rejects every noncanonical segment before signature validation.
7. The HTTP transport lacked principal-level tool filtering, rate/capacity limits, duplicate-key rejection, batch caps, and response CORS. These controls are now enforced and regression-tested.
8. Repeated full-suite runs could intermittently finish all assertions but leave TestClient or Playwright lifecycle resources alive. TestClient now uses explicit context entry/exit, and Playwright cleanup is idempotent and attempts every owned layer even after an earlier close error. Ten independent full-suite processes now exit normally.
9. Candidate packaging previously relied on a clean tree assumption. Source/archive and package-manifest builders now reject symlinks and resolved path escapes, with dedicated regressions.
10. The release gate could read a repeated-suite artifact generated for an older
    source manifest. Each stability report now carries the SHA-256 of the
    current `MANIFEST.sha256`, and the release gate rejects a stale binding.

## Environment blocker confirmed

Managed system Chromium still has `URLBlocklist: ["*"]`; HTTP(S) navigation returns `net::ERR_BLOCKED_BY_ADMINISTRATOR`. The policy was not changed or bypassed. Therefore this environment cannot prove a real external-site journey, authenticated account selection, provider receipt, or paid action.

## Explicitly not proven

- ChatGPT web or desktop invoking this candidate over the official production route.
- Secure MCP Tunnel deployment and workspace publication.
- Target Mac live browser behavior and correct authenticated account/tab/workspace selection.
- Real provider writes, exact paid-cost reconciliation, or idempotency after an uncertain provider response.
- Production OAuth/workload identity, KMS, RBAC, tenant isolation, rotation, revocation, and externally anchored evidence.
- Complete ASVS mapping, dependency vulnerability scan, authorized penetration test, and legal/privacy review.
- Kill-at-every-transition, browser/tunnel crash, network partition, disk-full, partial-fsync, machine reboot, migration rollback, and mandatory 24-hour soak.
- Independent GPT-6 Pro/Astra architecture, security, visual E2E, and final release verdicts.

## Commands

```bash
python3 scripts/run_offline_acceptance.py
python3 scripts/run_mcp_acceptance.py
PYTHONPATH=src python3 scripts/run_http_process_smoke.py
python3 scripts/security_static_checks.py
python3 scripts/scan_package_secrets.py
python3 scripts/generate_sbom.py
python3 scripts/generate_supply_chain.py
PYTHONPATH=src python3 scripts/run_burn_in.py --seconds 30
python3 scripts/probe_system_chromium.py
python3 scripts/run_release_gates.py
```

`run_release_gates.py` must remain non-zero while any production gate is blocked. Suppressing that failure is a release-blocking defect.

## Process-exit stability regression

- Root cause: TestClient portal lifecycle and Playwright owner cleanup were not deterministic under repeated full-suite execution.
- Correction: TestClient is now entered and exited as a context; Playwright cleanup detaches all owners first and attempts trace, context, browser, and driver closure independently and idempotently.
- Historical regression evidence: 10 consecutive baseline full-suite runs, 111 tests per run, 1,110 tests total, all exited normally within the external timeout. This does not verify the `0.3.0a1` candidate.
