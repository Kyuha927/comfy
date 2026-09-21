# ONE-SHOT: Publish Verified WBCP 0.2.0a1 Exactly, Then Add Cua Driver as a 0.3.0 Worker

## Status at handoff

This handoff is intentionally strict.

```text
WBCP_0.2.0a1_LOCAL_VERIFICATION=PASS
GITHUB_CANDIDATE_BRANCH_CREATED=true
GITHUB_EXACT_SOURCE_EXPANSION=false
DRAFT_PR_CREATED=false
PRODUCTION_READY=false
CUA_INTEGRATION_TARGET=0.3.0
```

Do not merge, release, enable production writes, weaken approvals, or claim production readiness.

## Verified source identity

Use exactly these identities:

```text
candidate=webgpt-browser-control-plane
version=0.2.0a1
local_branch=candidate/webgpt-browser-control-plane-0.2.0a1
local_commit=4350b3ed3fd372f8094d11b43c58b7244a38e508
local_tree=9ede3c3e3c3309c0df72b63671c61334094a2569
tracked_files=102

SOURCE.tar.gz sha256=f6e344ac2f95850189421934a40f1ca913e1735392ce7a8fceda79637018233e
SOURCE_MANIFEST.sha256 file sha256=733d0f8ce6b07415fa92f6777816ead0cd5e2c6a6cb31870d74ce8b4e3d0d9e4
PACKAGE_MANIFEST.sha256 file sha256=67a340fb19319aca36d93f3734e732402f5465fb22ca04423fe6e23dd379f80d
git.bundle sha256=620764cf36f09e8c5b52da5b511bf859e7e3f399271ae0a3b99a5b79a7309316
```

The 2026-09-21 re-run verified safe extraction, both manifests, Python compilation, Git bundle identity, and **111/111 tests PASS**.

Historical `WBCP_0.2.0a1_REVERIFY_RECEIPT.json` is NOT success evidence. That old receipt failed because it referenced artifacts at absent container paths.

## Phase A: exact GitHub publication

Repository:

```text
Kyuha927/comfy
```

Base:

```text
work-handoffs-v4-20260912
```

Already-created candidate branch:

```text
candidate/webgpt-browser-control-plane-0.2.0a1-20260921
```

Target path:

```text
candidates/webgpt-browser-control-plane
```

### Required procedure

1. Obtain the exact verified `WBCP_0.2.0a1_SOURCE.tar.gz`.
2. Verify SHA-256 before extraction.
3. Reject absolute paths, `..` traversal, symlinks, hardlinks, or resolved-path escape.
4. Extract preserving executable mode bits.
5. Verify `SOURCE_MANIFEST.sha256`, `PACKAGE_MANIFEST.sha256`, and `MANIFEST.sha256`.
6. Run:
   ```bash
   PYTHONPATH=src:tests python3 -m unittest discover -s tests -p 'test_*.py' -v
   python3 -m compileall -q src tests scripts
   python3 scripts/run_mcp_acceptance.py
   PYTHONPATH=src python3 scripts/run_http_process_smoke.py
   python3 scripts/security_static_checks.py
   python3 scripts/scan_package_secrets.py
   python3 scripts/run_release_gates.py
   ```
7. Require exactly 111 tests to pass.
8. `run_release_gates.py` must remain production-blocked. A surprise production-ready result is an investigation trigger, not a success.
9. Copy the exact candidate into `candidates/webgpt-browser-control-plane`.
10. Do not include credentials, auth state, runtime SQLite files, browser profiles, caches, generated secrets, or unrelated repository changes.
11. Commit and push only the candidate branch.
12. Fresh clone that remote branch into a new directory.
13. Re-run manifests and all 111 tests from the fresh clone.
14. Compare important executable file modes against the source archive.
15. Open a **Draft PR** against `work-handoffs-v4-20260912`.
16. PR body must include source archive SHA, local candidate commit/tree, remote commit, fresh-clone receipts, all blocked production gates, and:
    `NO PRODUCTION PROMOTION GRANTED`.

Do not merge.

## Phase B: Cua Driver intake for WBCP 0.3.0

Only begin after Phase A fresh-clone verification passes.

### Pin

Use stable Cua Driver **0.28.2**, tag:

```text
cua-driver-rs-v0.28.2
```

Do not silently move to nightly or a later stable release during this implementation. If a newer version is desired, create a separate upgrade review.

Official project source is MIT-licensed. Review third-party optional components separately before adding them.

### Architecture lock

Cua does **not** replace WBCP and does **not** replace Playwright.

```text
ChatGPT / Work / Codex
        |
        v
      WBCP
  policy / permits / approvals / cost / evidence
        |
        v
   Worker Router
   |           |
   |           +--> CuaDriverAdapter
   |                 |
   |                 +--> Cua MCP proxy / private worker
   |                 +--> CuaDriver.app daemon on macOS
   |
   +--> PlaywrightAdapter
```

Routing rule:

- Playwright remains default for deterministic DOM/network work.
- Cua is selected for exact native-window interaction, OS dialogs, desktop apps, or an explicitly approved existing signed-in browser profile.
- Never expose the entire raw Cua tool catalog directly to the model through WBCP.

### macOS process rule

For the target Mac, do not run a random raw Cua binary and pretend TCC attribution is production-safe.

Preferred path:

```text
WBCP Cua worker
-> cua-driver MCP proxy or private worker
-> CuaDriver.app-owned daemon
-> macOS Accessibility + Screen Recording
```

The Cua runtime permission mode must be fixed at startup.

Use **bounded** mode for unattended or agent-driven operation. Permit only reviewed apps, origins, directories, and tool names.

### Existing Chrome profile rule

Default: driver-owned isolated profile.

Existing signed-in Chrome/Edge profile is exceptional.

It requires BOTH:

1. outer WBCP authorization bound to exact job/session/host/action; and
2. Cua's own trusted existing-profile grant or approved authorization host/capability manifest.

An MCP tool argument from the model must never create this grant.

Bind to exact:

- PID
- native window ID
- Cua lifecycle session
- target ID
- tab ID
- expected account/workspace where applicable

Ambiguity must fail closed.

### Initial Cua allowlist

Prefer typed tools only.

Expected first-pass allowlist includes bounded equivalents of:

- list_apps
- list_windows
- start_session
- end_session
- get_browser_state
- browser_prepare
- browser_navigate
- browser_click
- browser_type
- browser_pointer
- browser_dialog
- wait

Disable:

- generic shell execution
- legacy page mutation surface
- unrestricted JavaScript/eval escape hatches
- arbitrary filesystem access
- automatic existing-profile grant
- permission-mode changes by the agent

Exact names must be re-read from the pinned 0.28.2 tool schema before implementation.

### WBCP risk mapping

Primitive tool names do not determine business risk.

Examples:

- inspect/snapshot: R0
- navigation/tab selection: R1
- typing/draft/file assignment: R2
- attaching an existing authenticated browser profile: privileged-context gate, require explicit one-shot user approval
- send/publish/reserve/paid generation: R3
- payment/delete/security/permission/legal change: R4, default block or dual control
- credential extraction/CAPTCHA bypass/security disabling: R5 hard block

### Evidence rule

Cua screenshots, accessibility state, native window identity, and browser state are useful evidence but do not replace provider/network evidence.

For R3/R4, WBCP still requires:

```text
DOM/accessibility
+ pixel/native visual assertion
+ network/provider receipt
```

Missing provider receipt must remain FAILED / ROLLED_BACK / QUARANTINED.

### Required implementation

Create on a new branch based on the verified 0.2.0a1 remote candidate:

```text
candidate/wbcp-cua-adapter-0.3.0-20260921
```

Add at minimum:

```text
src/wbcp/cua_adapter.py
src/wbcp/worker_router.py
tests/test_cua_adapter_contract.py
tests/test_worker_router.py
tests/test_cua_policy_boundary.py
tests/test_cua_existing_profile_gate.py
tests/test_cua_evidence_mapping.py
docs/CUA_DRIVER_INTEGRATION.md
```

Do not modify the Playwright adapter contract except through a backwards-compatible router interface.

### Contract tests before a real desktop

Mock/fake transport tests must prove:

- exact typed tool allowlist
- unknown Cua tool fails closed
- session ownership
- PID/window/tab binding
- stale ref rejection
- existing-profile approval cannot be self-granted
- WBCP permit cannot be widened by Cua
- Cua permission mode cannot be changed by an agent action
- R3/R4 provider receipt remains mandatory
- cancellation closes Cua session
- timeout/crash returns structured failure
- retry does not duplicate consequential action
- Cua fallback cannot silently replace Playwright after a policy failure
- secrets are redacted from receipts

### Target-Mac E2E

After contract tests pass, run on the target Mac with a disposable test account.

Required journeys:

1. isolated-profile read-only inspection
2. isolated-profile form type + reversible action
3. native file dialog interaction
4. Chrome existing-profile attachment with explicit approval
5. wrong-window negative test
6. wrong-tab negative test
7. prompt-injection negative test
8. Cua daemon restart during a job
9. WBCP cancellation during a Cua action
10. consequential action requiring real provider receipt

Capture:

- Cua version
- macOS version
- Chrome version
- permission mode
- PID/window ID
- WBCP job/session IDs
- before/after screenshots
- DOM/accessibility evidence where applicable
- network/provider receipt
- cleanup/session closure
- exact failure codes

### Promotion gates

CUA integration may become a 0.3.0 candidate only if:

- 0.2.0a1 regression remains green
- all new Cua contract tests pass
- bounded permission manifest is reviewed
- isolated-profile target-Mac E2E passes
- existing-profile positive and negative tests pass
- no raw shell/eval escape is exposed
- R3/R4 evidence rules remain unchanged
- crash/cancel/session-cleanup tests pass

It is still not production-ready until the existing WBCP production gates pass, including security review, 24-hour mixed soak, real provider/account testing, Astra independent review, and explicit user promotion approval.

## Current official Cua references checked on 2026-09-21

- https://cua.ai/docs/concepts/choose-a-cua-driver-integration
- https://cua.ai/docs/how-to-guides/driver/connect-your-agent
- https://cua.ai/docs/how-to-guides/driver/use-sdk-in-process
- https://cua.ai/docs/reference/cua-driver/process-model
- https://cua.ai/docs/reference/cua-driver/platform-support
- https://cua.ai/docs/reference/cua-driver/limits
- https://cua.ai/docs/how-to-guides/driver/restrict-tool-access
- https://github.com/trycua/cua/releases/tag/cua-driver-rs-v0.28.2
- https://github.com/trycua/cua/blob/main/LICENSE.md

## Required final status

Return exactly one of:

```text
WBCP_0.2.0a1_PUBLISHED_FRESH_CLONE_VERIFIED_CUA_0.3.0_CANDIDATE_READY
```

or the smallest exact blocker, such as:

```text
BLOCKED_SOURCE_IDENTITY_MISMATCH
BLOCKED_GITHUB_BINARY_SAFE_WRITE
BLOCKED_FRESH_CLONE_REGRESSION
BLOCKED_CUA_PIN_OR_LICENSE
BLOCKED_CUA_MACOS_TCC_ROUTE
BLOCKED_CUA_EXISTING_PROFILE_GATE
BLOCKED_CUA_EVIDENCE_REGRESSION
BLOCKED_TARGET_MAC_E2E
```

No merge, production enablement, permission expansion, or final promotion is authorized.
