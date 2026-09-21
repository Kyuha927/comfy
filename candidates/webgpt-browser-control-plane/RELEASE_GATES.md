# Commercial Release Gates

**Candidate:** `webgpt-browser-control-plane 0.3.0a1`
**Rule:** every production gate is fail-closed. A missing artifact is a failure, not an implied pass.
**Current verdict:** `CONDITIONAL_OFFLINE_AND_LOCAL_TRANSPORT_PASS_PRODUCTION_BLOCKED`

> The detailed status statements below describe the inherited `0.2.0a1` baseline unless replaced by a current `0.3.0a1` generated receipt. They are gate definitions and historical context, not proof that this reconstructed candidate has passed the same checks.

No critical gate may be waived by adding a warning to documentation. A gate may be reopened only by new evidence tied to an exact source commit, build identity, environment identity, and run receipt.

## Status vocabulary

- `PASS`: required evidence exists on the intended production path.
- `PASS_OFFLINE_ONLY`: useful candidate evidence, but not production evidence.
- `BLOCKED`: the environment or platform prevented a required proof.
- `NOT_RUN`: no acceptable evidence exists.
- `FAIL`: a discriminating test ran and the candidate violated the gate.
- `NOT_GRANTED`: a required human or administrative promotion did not occur.

Only `PASS` satisfies a production gate. `PASS_DESIGN_ONLY` and `PASS_OFFLINE_ONLY` never count as release approval.

## G0. Official route and objective reconciliation

**Objective:** WebGPT/ChatGPT can inspect and operate an approved browser session with commercial-grade authorization, auditability, failure recovery, and explicit control of consequential actions.

Required evidence:

1. Current official OpenAI browser, app/MCP, plan, and Secure MCP Tunnel routes were checked.
2. Current Playwright isolation, locator, trace, authentication-state, and CDP guidance were checked.
3. `OFFICIAL_RECOMMENDED_ROUTE` versus `PROPOSED_ROUTE` is recorded.
4. Any deviation is tied to an explicit constraint and does not omit a known higher-ceiling route.
5. The exact ChatGPT plan/workspace and execution surface are identified before write capability is enabled.

Failure codes:

- `BLOCKED_OFFICIAL_ROUTE_NOT_RECONCILED`
- `BLOCKED_PLAN_OR_CHATGPT_TIER_NOT_WRITE_CAPABLE`
- `BLOCKED_SECURE_TUNNEL_NOT_AVAILABLE`

Current status: `PASS_DESIGN_ONLY`. See `OFFICIAL_ROUTE_RECONCILIATION.md`. The real target plan and surface still require live confirmation.

## G1. Architecture and threat-model closure

Required evidence:

- Explicit trust boundaries for model, transport, identity, browser worker, website, filesystem, evidence store, and release pipeline.
- No generic untyped click/write primitive exposed to the model.
- Unknown actions fail at `R4`, not `R0` or `R1`.
- Page content is data, never authority.
- Exact-host egress and SSRF controls apply to every navigation/redirect hop.
- Reversibility claims map to tested compensating operations; otherwise quarantine is mandatory.

Current status: `PASS_OFFLINE_ONLY`.

## G2. Identity, session, and account correctness

Required evidence on the intended deployment:

- User, workspace, host model, browser context, target account, and selected tab are independently attested.
- Permit subject and session cannot be rebound.
- Account/workspace identity is displayed immediately before every `R3` or `R4` commit.
- Contexts are isolated by account and purpose; no silent auth-state reuse.
- Credentials, passkeys, OTPs, recovery codes, and CAPTCHA are completed directly by the user in the browser and never passed through chat or evidence.
- Production signing keys live in managed key storage, rotate, and are not shared with the browser worker.

Current status: `NOT_RUN`.

## G3. Authorization and economic safety

Required evidence:

- Finite permits bind subject, session, exact host, action set, risk ceiling, expiry, call count, currency, and maximum cost.
- Permit and one-shot approval consumption are one atomic transaction.
- `R3` requires one-shot human approval bound to the exact action digest and fresh page revision.
- `R4` is blocked by default. Enabling it requires explicit product policy plus two distinct approvers.
- Cost-bearing actions block when exact cost/currency is unavailable or exceeds either policy or permit limits.
- Retries use idempotency and provider-side reconciliation; no double spend.

Current status: `PASS_OFFLINE_ONLY`.

## G4. Transport and ChatGPT integration

Required evidence:

- One supported route is selected and proven end to end:
  - approved ChatGPT desktop Work/Codex browser route, or
  - eligible ChatGPT custom app with full MCP write support and admin publication.
- Private/local MCP uses the official Secure MCP Tunnel or another explicitly approved equivalent. No unauthenticated public bridge.
- Tool schemas, annotations, and action snapshots match the reviewed version.
- Tool-schema changes trigger a diff review and re-publication gate.
- The same path ChatGPT uses performs health, inspect, preflight, authorization, commit, job polling, cancellation, and receipt retrieval.

Current status: local stdio, actual loopback uvicorn HTTP, principal tool filtering, rate/capacity limits, strict duplicate-key parsing, bounded request/batch handling, and allowlisted CORS are `PASS_OFFLINE_ONLY`; real ChatGPT invocation, Secure MCP Tunnel, workspace publication, and target deployment remain `NOT_RUN`.

## G5. Browser-worker integrity

Required evidence:

- Playwright-owned isolated context is the primary custom worker path.
- Existing-profile Chrome control is a separate compatibility route with explicit user approval.
- Full CDP is exceptional, explicitly approved, and restricted to the smallest capability set.
- Browser and context identity, version, executable hash, launch flags, extensions, and policy state are recorded.
- Every HTTP(S) request, including redirect hops and subresources, is checked against exact egress policy.
- DNS/rebinding control is demonstrated on the target network.
- Authentication state is excluded from source control, traces, and general evidence.
- Trace includes DOM snapshots, screenshots, console, and network data, all retention-classified.

Current status:

- Real Chromium DOM/pixel/trace: `PASS_OFFLINE_ONLY`.
- Live network navigation in this validation container: `BLOCKED_BY_BROWSER_ADMIN_POLICY` because managed Chromium policy blocks all URLs.
- Target Mac browser: `NOT_RUN`.

## G6. Postcondition and false-success resistance

Required evidence:

- `R0` through `R2`: at least two independent signals.
- `R3` and `R4`: DOM/accessibility + pixel + network/provider receipt, all required.
- Expected account, recipient, content, amount, currency, resource ID, and terminal provider state are checked after commit.
- A successful click/API return is never treated as success by itself.
- Missing evidence produces `FAILED`, `ROLLED_BACK`, or `QUARANTINED`, never `SUCCEEDED`.

Current status: `PASS_OFFLINE_ONLY`, including real Chromium proof that DOM+pixel cannot satisfy an `R3` action without network/provider evidence and a regression proving that a boolean network flag cannot replace a non-empty provider receipt digest.

## G7. Reliability, recovery, and concurrency

Required evidence:

- Durable job state survives process restart.
- Compare-and-swap revisions prevent stale concurrent transitions.
- Permit call/cost limits and one-shot approvals remain correct under race.
- Cancellation works during long actions and releases browser resources.
- Crash injection at every state transition proves safe replay or quarantine.
- Browser crash, tunnel disconnect, network partition, provider timeout, and machine reboot are tested.
- Queue bounds, backpressure, circuit breakers, and disk-full behavior are tested.
- Save/reopen or fresh-process verification is used where browser/provider state persists.

Current status: core concurrency and full runtime close/reopen continuation are `PASS_OFFLINE_ONLY`; browser/tunnel crash, machine reboot, partition, disk-full, and mandatory 24-hour soak remain `NOT_RUN`.

## G8. Security verification

Required evidence:

- OWASP ASVS 5.0 control mapping for applicable sections.
- NIST SSDF-aligned build, review, dependency, vulnerability, and release process.
- Independent tests for SSRF, DNS rebinding, prompt injection, confused deputy, origin/message forgery, path traversal, malicious downloads, secret leakage, approval substitution, replay, and supply-chain compromise.
- Authorized penetration test of the deployed control plane and tunnel.
- No unresolved critical/high findings. Medium findings require explicit owner, containment, and deadline.

Current status: focused regression tests, canonical token-encoding enforcement, strict transport parsing, a limited static source scan, and a whole-package sensitive-file/token-pattern scan are `PASS_OFFLINE_ONLY`; full parser fuzzing, dependency vulnerability analysis, independent ASVS mapping, and penetration testing remain `NOT_RUN`.

## G9. Evidence, privacy, and observability

Required evidence:

- Redaction happens before append/export.
- Public hashes and revisions remain visible for verification; secrets do not.
- Ledger sequence, hash chain, and signature verification fail closed.
- Production roots are signed asymmetrically or anchored outside the host.
- Trace/log/screenshot/network retention and deletion policies are enforced.
- OpenTelemetry traces, metrics, and logs correlate by job ID without exporting secrets.
- Evidence restore/readback and legal/privacy review pass.

Current status: local HMAC hash-chain and Ed25519 checkpoint sign/verify are `PASS_OFFLINE_ONLY`; managed key custody, external anchoring, OTel export, retention enforcement, and privacy review remain `NOT_RUN`.

## G10. Performance and service-level objectives

Required production SLOs must be set before testing. Minimum candidate targets:

- Control-plane preflight p95 <= 250 ms excluding external identity provider latency.
- Authorization commit p95 <= 500 ms excluding human approval time.
- No more than one unbounded queue; all payload, trace, screenshot, and download sizes capped.
- Worker leak test: zero surviving contexts/processes after terminal jobs.
- 24-hour mixed read/write soak with no silent success, permit overrun, or evidence corruption.
- Recovery point and recovery time objectives proven by restore drill.

Current status: 30-second accelerated burn-in `PASS_OFFLINE_ONLY` with 448 iterations, zero failures, zero leaked sessions, a valid 3,136-event evidence chain, and p95 126.474 ms. Mandatory 24-hour soak and production SLO proof remain `NOT_RUN`.

## G11. Supply chain, packaging, and upgrade safety

Required evidence:

- Reproducible locked dependencies and browser revision.
- SBOM, license inventory, vulnerability scan, provenance, and signed release artifact.
- Candidate and production secrets excluded from package and repository.
- Staged upgrade, rollback, schema migration, and old/new client compatibility tests.
- Browser/extension/MCP schema drift blocks deployment until reviewed.

Current status: direct dependencies are pinned; candidate CycloneDX SBOM, dependency/license inventory, source manifest, unsigned local provenance, and static source check are generated. Complete transitive hash locking, vulnerability scan, legal license adjudication, trusted-builder provenance, external signature, migration, and rollback proof remain `NOT_RUN`.

## G12. Representative real journeys

At minimum, run all of the following in provider sandboxes or authorized test accounts:

1. Read-only inspection.
2. Navigation with allowed and denied redirect chains.
3. Reversible form fill with verified rollback.
4. Draft creation and recovery after worker restart.
5. Consequential free action with all three evidence channels.
6. Paid-generation action with exact cost cap and provider reconciliation.
7. Wrong-account/workspace negative test.
8. Prompt-injection page negative test.
9. Browser crash during commit.
10. Duplicate request/retry after uncertain provider response.

Each journey must produce an exact receipt and independent evidence review.

Current status: offline mock and real-Chromium no-network fixtures only; production journeys `NOT_RUN`.

## G13. Independent GPT-6 Pro / Astra release decision

Required evidence:

- Implementation owner cannot be the sole security or release approver.
- Security red team, reliability/E2E owner, and release reviewer issue separate signed/committed verdicts.
- Every non-pass gate is listed. No `UNKNOWN` is converted to `PASS`.
- Candidate commit/build/environment identities are frozen.
- A fresh release authority independently verifies architecture, hostile security, target-Mac visual/account E2E, reliability, supply-chain, privacy, and operational evidence.
- Merge, app publication, permission expansion, and production enablement remain separate explicit actions.

Current status: independent Astra architecture, security, visual E2E, and release verdicts are `NOT_RUN`.

## G14. Explicit user production promotion

Required evidence:

- The user reviews the frozen final evidence packet and explicitly approves production promotion.
- Approval binds the exact candidate commit, package digest, deployment target, permissions, and rollback package.
- Merge, app publication, permission expansion, and production enablement remain separate explicit actions.

Current status: user production promotion `NOT_GRANTED`.

## Automated commands

```bash
python3 scripts/run_offline_acceptance.py
python3 scripts/run_mcp_acceptance.py
PYTHONPATH=src python3 scripts/run_http_process_smoke.py
python3 scripts/security_static_checks.py
python3 scripts/scan_package_secrets.py
python3 scripts/generate_sbom.py
python3 scripts/generate_supply_chain.py
python3 scripts/run_exit_stability.py --runs 10
python3 scripts/generate_package_manifest.py
python3 scripts/verify_source_manifest.py --manifest PACKAGE_MANIFEST.sha256
python3 scripts/probe_system_chromium.py
python3 scripts/run_release_gates.py
```

`run_release_gates.py` intentionally exits non-zero until every production gate has actual evidence. Changing that behavior to make CI green is a release-blocking defect.
