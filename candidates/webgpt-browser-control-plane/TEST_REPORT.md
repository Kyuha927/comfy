# Test Report

**Candidate:** `0.1.0a2`  
**Environment:** isolated Linux validation container, Python 3.13, system Chromium 144.0.7559.96  
**Verdict:** `CONDITIONAL_OFFLINE_PASS_PRODUCTION_BLOCKED`

## Passing evidence

- Full Python unit/integration discovery passes: **73 tests**.
- Python source compilation passes.
- JSON contracts and policy files parse.
- Deterministic offline action journey passes.
- Real system Chromium launches in an isolated Playwright context.
- Real Chromium form fill produces passing DOM and pixel evidence plus a Playwright trace.
- A consequential click that produces DOM and pixel changes but no network/provider evidence is correctly rejected and quarantined.
- Concurrent finite-permit use never exceeds the call cap.
- Concurrent one-shot approval use has exactly one winner.
- Concurrent evidence appends preserve a continuous valid chain.
- Failed high-impact approval does not consume the finite permit; permit + approval consumption is atomic.
- Public hashes/revisions remain visible in evidence while credentials and bearer/cookie material are redacted.

## Environment blocker discovered by discriminating test

The managed system Chromium policy contains `URLBlocklist: ["*"]`. Every HTTP(S) navigation returns `net::ERR_BLOCKED_BY_ADMINISTRATOR`. The test environment therefore cannot honestly prove a live network journey. The policy was not bypassed or edited.

Consequences:

- Live browser network gate: `BLOCKED`.
- Redirect interception is covered by URL-guard and route-callback tests, not a real network redirect in this container.
- Real-site provider receipts, authentication, paid actions, and ChatGPT roundtrip remain `NOT_RUN`.

## Explicitly not proven

- ChatGPT web/desktop invoking the candidate.
- MCP transport or Secure MCP Tunnel.
- Target Mac browser behavior.
- Existing Chrome profile/account/tab selection.
- Real provider writes or cost reconciliation.
- Production key custody, RBAC, external root anchoring, OTel, retention enforcement.
- Crash/reboot/network-partition/disk-full/24-hour soak.
- Full ASVS mapping, authorized penetration test, SBOM/signing/provenance.

## Commands

```bash
python3 scripts/run_offline_acceptance.py
python3 scripts/probe_system_chromium.py
python3 scripts/run_release_gates.py
```

The final release-gate command is expected to return a non-zero exit code while production gates remain blocked. Treating that non-zero result as a nuisance and suppressing it is prohibited.
