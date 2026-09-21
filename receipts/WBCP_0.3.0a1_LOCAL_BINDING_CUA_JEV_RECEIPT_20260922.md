# WBCP 0.3.0a1 local binding, CUA update, and Jev isolation receipt

Date: 2026-09-22 (Asia/Seoul)
Status: `PARTIAL_WITH_BLOCKERS`
Scope: source-bound local candidate validation, one official CUA Driver update, and isolated Jev preparation. This is **not** an active WBCP deployment or production acceptance.

## 1. Remote candidate binding

| Field | Value |
| --- | --- |
| Candidate branch | `candidate/webgpt-browser-control-plane-jev-cua-0.3.0a1-20260921` |
| Candidate source commit | `313926dd54018c7bc74d78dc3101c85636c99b84` |
| Candidate source tree | `e50635bca7d2f66218743dd780aac20674861a54` |
| Candidate source manifest SHA-256 | `9214011050eacfefe441b9b0c049f5481e00166844e2b615584789d942200f38` |
| Source archive SHA-256 | `84cea8b47e19966f924b3442a87da8f912e6b6d6c34f7d490d834febde20f5ca` |
| Source ZIP SHA-256 | `b06b842316d97bd2e1ac60f73d0e9fba289fc381f34619d756cc22da4b6ec087` |
| Integration base | `work-handoffs-v4-20260912 @ 7f9c5701a77d341bd7ca680b06242980600000dd` |
| Remote branch head before this receipt | `bde04f9e31776ac9064c09bb30fc36b0a85502ba` |

The current local candidate was a newly materialized detached checkout of the exact source commit above. The incomplete branch `candidate/webgpt-browser-control-plane-jev-cua-20260921 @ d3aa0ba287ba244a4e03cb2f3f4f1171d72b0957` was not used as source authority.

## 2. Candidate-local verification

| Check | Command class | Exit | Observed result |
| --- | --- | ---: | --- |
| Source-manifest verification | candidate verifier | `0` | 87 source entries; SHA-256 matches the bound source manifest |
| Engine source verification | `scripts/verify_engine_sources.py --jev-source <verified-source>` | `0` | `PASS_SOURCE_VERIFIED` |
| Compile | Python `compileall` | `0` | PASS |
| Full candidate suite | Python unittest discovery | `0` | **125 tests**, PASS |
| Jev/CUA boundary subset | `test_engine_boundaries.py` | `0` | **10 tests**, PASS |

The boundary subset executed and passed the following relevant contracts: Playwright remains the AUTO primary route; Jev authenticated/sensitive/personal-profile defaults fail closed; external-model egress defaults fail closed; Jev `DONE` requires the independent WBCP verifier; potential mutation requires reconciliation and blocks duplicate fallback; CUA exact binding and two independent existing-profile grants are enforced; and the public catalog exposes no shell, eval, unrestricted filesystem, or self-grant operation.

## 3. Isolated Jev environment

| Field | Value |
| --- | --- |
| Python | `3.12.13` (dedicated virtual environment) |
| Jev source commit | `1231850a0bf1a0c0341fe408ef1668dbbfdfac46` |
| Jev source tree | `987b481ed8ef400911ca471bce38c7adfdabc45c` |
| Installed `jev-ultrafast` | `0.1.0` |
| Installed `browser-harness` | `0.1.13` |
| Verified browser-harness wheel SHA-256 | `2491459e4bfc0ee8aea22dc6c4680fc0f791b7ba553446323c50d2883449d769` |
| Dependency consistency | `pip check` exit `0` |
| Chrome profile | new WBCP-owned task-local directory; not a default or existing personal profile |
| Debugging endpoint | temporary `127.0.0.1` endpoint; `about:blank` only; verified and then cleanly stopped |

No Jev model execution, paid TypeSafe/text-model call, authenticated page, sensitive page, existing personal profile attachment, or external-model egress was attempted. `JEV_LIVE_PAID_SMOKE=BLOCKED_PAID_API_NOT_AUTHORIZED` remains true.

## 4. CUA Driver update

The app-owned signed updater reported the stable-channel target `0.28.2`; the official `cua-driver update --apply --json` path completed with exit `0`. No manual archive extraction, sideload, downgrade, TCC grant, default-profile change, or telemetry-preference change was performed.

| Field | Before | After |
| --- | --- | --- |
| Bundle ID | `com.trycua.driver` | `com.trycua.driver` |
| CUA Driver version | `0.21.0` | `0.28.2` |
| App binary SHA-256 | `997f52111f6e2ba02e42829877dface5e783921ef1c178c0b45ec60f54b0e74e` | `9a7731f7e961a57963f0deb132878367fdf7354e7327a4d558fe4a68e4686b81` |
| Signing identity | `Developer ID Application: Cua AI, Inc. (YCK386LBJ7)` | same identity; notarization ticket present |
| App-owned daemon | prior healthy daemon | running from `/Applications/CuaDriver.app`, PID observed after update |
| Permission mode | standard trusted startup configuration | `standard (trusted_startup_configuration)` |
| Accessibility | true | true |
| Screen Recording | true | true |
| LaunchAgent SHA-256 | `eb72d4da62496cd7216ad07406d59d18478120cc88a99ad0fe001f452c47e170` | unchanged |

Post-update `status --json`, `permissions status --json`, and `doctor --json` each exited `0`. The daemon reported `direct_capture_status=not_checked` and `screen_recording_capturable=null`. The official direct-capture check requires the user-controlled permission-grant flow, so it was intentionally **not** invoked. This receipt therefore does not claim live direct-capture success.

## 5. Secret-safe backup and recovery boundary

The pre-update backup contains only the CuaDriver application bundle and its app-owned LaunchAgent. Its manifest SHA-256 is `052a6cde11c63fc9514ef5cbeb04e92477eea2c489822e05a37a4e09bfa79f87`.

Excluded by construction: browser profiles, cookies, recordings, history, TCC databases, API keys, account state, and personal page content.

Conditional recovery procedure: restore the exact backed-up CuaDriver app and LaunchAgent, reload only that app-owned LaunchAgent, then use the driver’s read-only status and permissions-status checks. This recovery procedure does not authorize a TCC, browser-profile, account, security, payment, or unrelated-system setting change. A CUA downgrade/rollback was **not run** because the official upgrade is healthy and a reversal is outside this acceptance scope.

## 6. Deliberately unrun deployment and production gates

| Gate | State | Reason |
| --- | --- | --- |
| Active WBCP `0.2.0a1` replacement | `NOT_RUN` | Candidate remains isolated; baseline was preserved unchanged. |
| Candidate plugin deployment / host reload | `NOT_RUN` | Requires completion of prerequisite local acceptance and a separate deployment gate. |
| Active `wbcp_browser` candidate health | `NOT_RUN` | Candidate is not installed as the active MCP runtime. |
| CUA direct-capture/capturability | `NOT_RUN_USER_CONTROLLED_TCC_GATE` | Official check can open a macOS permission path; no TCC action was authorized. |
| Existing-profile positive case | `NOT_RUN_NO_DUAL_APPROVAL` | No independent host/profile grants and no disposable authorized account. |
| Paid Jev smoke | `BLOCKED_PAID_API_NOT_AUTHORIZED` | No paid service authorization was supplied. |
| Production release | `BLOCKED_BY_RELEASE_GATES` | Candidate release verdict remains production blocked by design. |

## 7. Source of truth

- Candidate branch: <https://github.com/Kyuha927/comfy/tree/candidate/webgpt-browser-control-plane-jev-cua-0.3.0a1-20260921>
- Draft PR: <https://github.com/Kyuha927/comfy/pull/4>
- Remote candidate receipt: `receipts/WBCP_0.3.0a1_REMOTE_CANDIDATE_RECEIPT.md`
- CUA research gate: `receipts/CUA_DRIVER_UPGRADE_RESEARCH_GATE_20260922.md`

This receipt is evidence for the bounded candidate and local preparation only. It is not evidence of a production deployment, active MCP replacement, live direct capture, paid Jev execution, default-profile access, or user acceptance.
