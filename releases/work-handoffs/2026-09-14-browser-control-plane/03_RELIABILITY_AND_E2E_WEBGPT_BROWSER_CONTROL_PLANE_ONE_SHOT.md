# ONE-SHOT: Reliability and End-to-End Validation

Act as the independent reliability and browser-E2E owner for `WebGPT Browser Control Plane 0.1.0a2`. Use disposable test infrastructure only. Do not bypass managed network policy, touch personal profiles, perform paid or externally visible actions, or reinterpret missing evidence as success.

## Inputs

Read `00_READ_FIRST_WEBGPT_BROWSER_CONTROL_PLANE.md` and all referenced candidate documents. Verify the source archive identity before execution.

## Required campaigns

1. Deterministic fixtures for R0 through R4, including expected success, rollback, block, and quarantine paths.
2. Real isolated Chromium journeys covering DOM/accessibility state, rendered pixels, console, network, tracing, redirects, upload, download, dialogs, popups, and browser crashes.
3. Concurrency and delivery tests: duplicate submission, duplicate worker pickup, retry after uncertain completion, permit exhaustion, approval race, stale revision, cancel/execute race, and evidence append contention.
4. Fault injection: process kill at every state transition, database lock, disk-full, partial fsync, corrupted evidence tail, clock jump, key rotation, browser crash, tunnel loss, provider timeout, network partition, reboot, and restore from backup.
5. Recovery proof: no silent re-execution, no skipped approval, deterministic terminal status, authoritative revision preserved, rollback receipts retained, and unresolved ambiguity quarantined.
6. Authorized live test-tenant validation for provider receipts. R3/R4 cannot pass on DOM plus pixels alone.
7. A bounded soak of at least 24 hours after functional gates pass, with latency percentiles, queue depth, retry counts, memory/handle growth, evidence throughput, and error taxonomy.

## Acceptance thresholds

- Zero unauthorized side effects.
- Zero duplicate consequential executions.
- Zero permit or approval replay successes.
- Zero private-network or redirect egress escapes.
- Every completed R3/R4 job has all three evidence classes and a valid chain.
- Every uncertain consequential result ends quarantined.
- Backup restore and reboot recovery preserve job and evidence authority.
- Observability identifies each job, transition, permit, approval, worker, browser context, evidence entry, rollback, and terminal receipt without exposing secrets.

## Output

Publish commands, environment identity, versions, exit codes, traces, screenshots, hashes, metrics, failure injections, and a gate matrix. Report `RELIABILITY_CANDIDATE_PASS`, `PARTIAL_WITH_BLOCKERS`, or precise `BLOCKED_*` codes. A reliability pass does not authorize release.
