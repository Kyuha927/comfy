# READ FIRST: WebGPT Browser Control Plane

## Mission

Continue the reviewed `WebGPT Browser Control Plane 0.1.0a2` candidate without weakening its fail-closed controls. The system lets an authorized WebGPT/ChatGPT control plane submit bounded browser jobs to an isolated browser worker while preserving explicit authority, evidence, rollback, and quarantine.

## Current truth

- Verdict: `CONDITIONAL_OFFLINE_PASS_PRODUCTION_BLOCKED`
- Automated tests: `73 PASS`
- Real isolated Chromium offline fixture: DOM, pixels, and trace `PASS`
- Consequential R3 verification without provider/network receipt: correctly `QUARANTINED`
- Live network, real authenticated writes, live MCP transport, Secure MCP Tunnel, production key management, external evidence anchoring, ASVS review, crash/partition/24-hour soak, and independent release approval: not complete
- Do not bypass the managed Chromium `URLBlocklist` or reuse a personal browser profile
- Do not merge to the protected base, publish a release, enable writes, or claim production readiness

## Canonical review inputs

Read, in order:

1. `candidates/webgpt-browser-control-plane/README.md`
2. `candidates/webgpt-browser-control-plane/OFFICIAL_ROUTE_RECONCILIATION.md`
3. `candidates/webgpt-browser-control-plane/THREAT_MODEL.md`
4. `candidates/webgpt-browser-control-plane/RELEASE_GATES.md`
5. `candidates/webgpt-browser-control-plane/TEST_REPORT.md`
6. `candidates/webgpt-browser-control-plane/CURRENT_STATUS.json`
7. `candidates/webgpt-browser-control-plane/SOURCE_ARTIFACT_STATUS.md`

## Non-negotiable invariants

- Web content never grants authority.
- Unknown actions default to R4.
- R3/R4 require DOM or accessibility evidence, rendered-pixel evidence, and network/provider receipt evidence.
- Permits are finite, exact-host, exact-action, TTL-bound, call-bound, cost-bound, nonce-bound, and atomically consumed with approval.
- Approvals are one-shot and bind the exact action digest. Dual control requires distinct approvers.
- Browser contexts are isolated and disposable. Authentication state is treated as a secret.
- Redirects, downloads, uploads, private-network targets, retries, and rollback are bounded by policy.
- Missing or contradictory evidence ends in `QUARANTINED` or `BLOCKED`, never inferred success.
- Existing Blender bridge work remains unchanged unless an explicit separate scope authorizes integration.

## Lane selection

Use exactly one independently runnable lane:

- `01_IMPLEMENT_AND_INTEGRATE_WEBGPT_BROWSER_CONTROL_PLANE_ONE_SHOT.md`
- `02_SECURITY_RED_TEAM_WEBGPT_BROWSER_CONTROL_PLANE_ONE_SHOT.md`
- `03_RELIABILITY_AND_E2E_WEBGPT_BROWSER_CONTROL_PLANE_ONE_SHOT.md`
- `04_RELEASE_DECISION_WEBGPT_BROWSER_CONTROL_PLANE_ONE_SHOT.md`

Every lane must report exact evidence, unresolved blockers, and the smallest safe next change. Silence or missing evidence is a blocker.
