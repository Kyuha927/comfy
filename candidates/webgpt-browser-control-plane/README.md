# WebGPT Browser Control Plane

**Status:** `ISOLATED_CANDIDATE_NOT_DEPLOYED`
**Version:** `0.3.0a1`
**Production promotion:** **NOT GRANTED**

This candidate adds a bounded policy, authorization, durable-job, rollback, and tamper-evident evidence layer in front of browser automation. It is designed to let ChatGPT/WebGPT propose and inspect work without silently converting page text into authority or turning a generic click primitive into an unbounded write channel. The active OneClick `0.2.0a1` runtime, personal Chrome profile, and TCC permissions are not modified by this isolated candidate.

It does **not** claim that live ChatGPT browser control is complete. The policy core, executable MCP stdio and authenticated HTTP transports, durable restart recovery, deterministic mock journeys, signed evidence checkpoints, and real-Chromium no-network DOM/pixel/trace paths are implemented and tested. Live network browsing in this validation container is blocked by managed Chromium policy; official ChatGPT app/plugin transport, Secure MCP Tunnel, signed production identity, and real-site write journeys remain separate hard gates.

## Official route first

The build deliberately does not pretend that a new browser engine is always necessary.

1. **ChatGPT desktop Work/Codex:** use OpenAI's built-in browser for isolated browsing, or the Codex Chrome extension when an existing Chrome profile, signed-in session, open tabs, or installed extensions are required.
2. **ChatGPT web custom app:** use an MCP-based app. As of the 2026-09-14 research pass, full custom MCP writes are documented for Business and Enterprise/Edu. Pro custom MCP access is read/fetch only. A Pro-only write path must therefore block instead of routing around the platform gate.
3. **Private/local control plane:** connect through the official Secure MCP Tunnel rather than exposing the local service directly.
4. **Browser worker:** prefer Playwright-owned isolated contexts or the official Playwright MCP route. `connect_over_cdp` is a compatibility lane, not the default production route.
5. **Existing Blender bridge:** remains unchanged. This candidate is a sibling worker/control-plane design, not a replacement or silent canon merge.

See [`OFFICIAL_ROUTE_RECONCILIATION.md`](OFFICIAL_ROUTE_RECONCILIATION.md).

## Architecture

```text
ChatGPT / WebGPT
  |
  | official app/plugin or approved local Work/Codex route
  v
Browser Control Plane
  |- host/user/workspace identity gate
  |- exact-host URL and SSRF gate
  |- risk classifier R0..R5
  |- finite HMAC-signed permit authority
  |- one-shot high-impact approval authority
  |- durable idempotent job state machine
  |- budget and currency gate
  |- prompt-injection boundary
  |- redacted hash-chained evidence ledger
  |- rollback / quarantine controller
  v
Browser Worker
  |- Primary: Playwright-owned isolated context / Playwright MCP
  |- Guarded fast path: explicitly authorized Jev in its WBCP-owned profile
  |    |- exact `jev-ultrafast 0.1.0` source lock and browser-harness 0.1.13
  |    |- authenticated, sensitive, personal-profile, unsupported, and egress contexts deny
  |    `- DONE requires an independent WBCP verifier before success
  |- Exceptional native boundary: exact-bound typed CUA operations only
  |    `- session/PID/window/target/tab/URL/profile binding; CUA >= 0.28.2
  v
Allowed website
```

### Jev and CUA boundary contract

- `AUTO` and known deterministic flows select Playwright. An engine preference is never authority.
- Jev is disabled unless explicitly selected for an isolated local profile, an exact public host, and an authorized runtime path. It defaults to deny for authenticated or sensitive pages, existing personal Chrome profiles, iframe/shadow/canvas/upload/popup/nested-scroll/arbitrary-keyboard features, and all external-model egress. Loopback fixtures cannot use an egress allowance.
- The Jev source pin is [`ENGINE_SOURCES.lock.json`](ENGINE_SOURCES.lock.json): `browser-use/jev-ultrafast` `0.1.0` at `1231850a0bf1a0c0341fe408ef1668dbbfdfac46`, plus `browser-harness==0.1.13`. Install it only in a WBCP-owned Python `>=3.12` environment after source verification; [`requirements-jev.lock`](requirements-jev.lock) records the exact source and wheel digest.
- Jev `DONE` is an adapter observation, not WBCP success. A trusted independent verifier must pass. If a mutation may have occurred, fallback is blocked until side-effect reconciliation has completed; identical retries cannot create a duplicate effect.
- CUA is limited to `SNAPSHOT`, `NAVIGATE`, `CLICK`, `TYPE_TEXT`, `SELECT`, `SCROLL`, and `WAIT`. The operation cannot override its WBCP binding or authorized URL. Existing-profile attachment requires independently issued external and WBCP grants and cannot self-grant.
- The public MCP catalog contains no raw shell, `eval`, generic tool dispatch, unrestricted filesystem capability, binding mutation, or profile-grant tool.

## Implemented and verified in this candidate

- Exact-host HTTPS allowlisting, redirect-hop revalidation, non-public IP blocking, unsafe-scheme blocking, URL credential blocking, and runtime resolved-IP checks.
- Risk classification from `R0_READ_ONLY` through `R5_PROHIBITED`, with unknown actions failing high rather than low.
- Page content treated as untrusted data. `WEB_CONTENT` cannot authorize actions.
- Finite signed permits bound to subject, session, exact host, action, risk ceiling, expiry, call count, currency, and cost; every Base64url segment must use its unique canonical spelling.
- One-shot approvals bound to exact job and action digest, including optional two-person control.
- Durable SQLite state machine with compare-and-swap revision transitions and idempotency conflict detection.
- Consequential actions require DOM/accessibility, pixel assertion, network success, and a non-empty provider/network receipt digest. A boolean network flag alone cannot pass R3/R4.
- Failed postconditions roll back when a verified compensating path exists; otherwise the job is quarantined.
- Evidence is redacted before append, hash-chained, HMAC-authenticated, and synchronously committed; public hashes/revisions remain available for verification.
- Playwright-owned adapter with semantic locators, exact egress guard, redirect-hop interception, explicit pixel/network assertions, isolated context, trace capture, bounded uploads/downloads, and fail-closed startup.
- Deterministic offline browser simulator.
- Full test count is generated by `scripts/run_offline_acceptance.py` and must be recorded from the exact current run rather than copied from a historical report. The suite covers concurrent permit exhaustion, one-shot approval races, atomic permit+approval consumption, concurrent evidence append, SSRF, prompt injection, secret redaction, real Chromium DOM/pixel/trace, stale page revision, idempotency, rollback, Jev/CUA default-deny, binding, verifier, reconciliation, and package-safety contracts.

## Executable MCP transport

The candidate now serves typed JSON-RPC tools through:

- newline-delimited stdio via `wbcp serve-stdio`;
- authenticated Streamable HTTP POST `/mcp` via `wbcp serve-http`;
- legacy `initialize` compatibility and 2026 `server/discover`;
- exact Host and Origin policy, allowlisted response CORS, mandatory HTTP bearer authentication, per-principal tool filtering, rate/capacity limits, bounded streaming request bodies, batch-item caps, duplicate-key rejection, protocol-version checks, and notification semantics;
- operator-only permit and approval issuance commands that are deliberately absent from the MCP tool list.

A transport process being healthy does not prove ChatGPT integration. Secure MCP Tunnel, workspace publication, target-Mac browser execution, authenticated account identity, and real provider receipts remain separate gates.

## Local start shape

```bash
cp deploy/env.example /secure/path/wbcp.env
chmod 600 /secure/path/wbcp.env
set -a; source /secure/path/wbcp.env; set +a
wbcp issue-permit --session-id demo --actions session_create inspect --hosts example.com --risk-ceiling 1 --max-calls 2
wbcp serve-http --bind 127.0.0.1 --port 8765
```

Never put real keys in shell history, a repository, chat, screenshots, traces, or evidence. Production deployment still requires managed secret storage and key rotation.

## Not yet proven

- A real ChatGPT web or desktop tool call reaching this candidate.
- Secure MCP Tunnel deployment and OAuth/RBAC behavior.
- Live network Playwright journeys on the target Mac. The validation container launches real Chromium but its managed `URLBlocklist=["*"]` blocks all HTTP(S) navigation.
- Chrome existing-profile/extension lane.
- Correct account, tab, and workspace selection under real authentication.
- Real paid generation, send, publish, reserve, or purchase workflows.
- External anchoring of evidence roots. Local Ed25519 checkpoint signing is tested, but the private key is not yet managed by production KMS.
- ASVS 5.0 requirement-by-requirement evidence and penetration test.
- Availability, latency, soak, crash recovery, and upgrade SLOs on the target deployment.

Any report that calls this package production-ready before those gates pass is invalid.

## Risk and authorization table

| Tier | Examples | Gate | Verification |
|---|---|---|---|
| R0 | inspect, query, screenshot | finite session permit | any 2 of DOM/pixel/network |
| R1 | navigate, scroll, tab state | finite session permit | any 2 of 3 |
| R2 | type, select, staged upload, draft | exact finite write permit | any 2 of 3 plus rollback where claimed |
| R3 | send, publish, reserve, paid generation | finite permit + one-shot human approval | all 3 signals |
| R4 | payment, transfer, delete, security/permission/legal change | default block; explicit dual control only | all 3 plus provider receipt, no rollback fiction |
| R5 | credential extraction, CAPTCHA bypass, security disabling, malware | hard block | not approvable |

## Run the verified offline gates

```bash
cd candidates/webgpt-browser-control-plane
PYTHONPATH=src:tests python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/run_mcp_acceptance.py
PYTHONPATH=src python3 scripts/run_http_process_smoke.py
python3 scripts/security_static_checks.py
python3 scripts/scan_package_secrets.py
python3 scripts/generate_sbom.py
python3 scripts/generate_supply_chain.py
python3 scripts/run_exit_stability.py --runs 10
PYTHONPATH=src python3 scripts/run_burn_in.py --seconds 30
python3 scripts/generate_package_manifest.py
python3 scripts/verify_source_manifest.py --manifest PACKAGE_MANIFEST.sha256
python3 -m compileall -q src
python3 scripts/verify_engine_sources.py --jev-source /absolute/path/to/jev-ultrafast-1231850
PYTHONPATH=src python3 -m wbcp.cli doctor
PYTHONPATH=src python3 -m wbcp.cli simulate --action inspect
```

The live-browser lane additionally requires the current pinned Playwright package and matching browser binaries. Do not reuse committed authentication state.

## Release rule

A GitHub commit, passing mock tests, or a successful single-site demo is not production approval. Promotion requires all gates in [`RELEASE_GATES.md`](RELEASE_GATES.md), an independent release-decision packet, and explicit user approval. No auto-merge or silent production enablement is allowed.
