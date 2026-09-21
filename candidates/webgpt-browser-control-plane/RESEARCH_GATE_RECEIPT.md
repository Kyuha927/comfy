# WBCP 0.3.0a1 — Research Gate Receipt

## Binding

- Task: WBCP + Jev + CUA candidate reconstruction and local acceptance
- Candidate branch: `candidate/webgpt-browser-control-plane-jev-cua-0.3.0a1-20260921`
- Verified integration base: `work-handoffs-v4-20260912` at `7f9c5701a77d341bd7ca680b06242980600000dd`
- Baseline: locally installed, manifest-verified WBCP `0.2.0a1`; it is an archive-bound runtime source rather than a Git checkout.
- Baseline source manifest: `733d0f8ce6b07415fa92f6777816ead0cd5e2c6a6cb31870d74ce8b4e3d0d9e4`
- Baseline package manifest: `67a340fb19319aca36d93f3734e732402f5465fb22ca04423fe6e23dd379f80d`

The former discovery and handoff refs named by historical records no longer resolve on the remote. They are not used as source authority. The current scoped user request and the verified integration base bind this reconstruction; the incomplete `d3aa0ba287ba244a4e03cb2f3f4f1171d72b0957` branch remains explicitly rejected.

## Problem redefinition

The task is not to make a browser agent choose the fastest available engine. It is to build a bounded control plane that keeps deterministic Playwright as the primary route for known flows, admits Jev only for explicitly eligible isolated public fixtures, and admits CUA only through host-owned typed bindings. Every route must preserve explicit authority, profile isolation, independently verified outcomes, and a durable reconciliation boundary before fallback after a possible mutation.

## Unknown-unknown sweep

| Area | Question tested | Result used by the candidate |
| --- | --- | --- |
| Existing candidate provenance | Is a verified complete `0.3.0a1` archive, bundle, release, PR, or reachable commit available? | No. The asserted commit and source artifacts do not resolve; reconstruction from the verified `0.2.0a1` baseline is required. |
| Jev provenance | Is the exact upstream implementation and dependency contract available? | Yes: `browser-use/jev-ultrafast` `0.1.0`, commit `1231850a0bf1a0c0341fe408ef1668dbbfdfac46`, with `browser-harness==0.1.13` and Python `>=3.12`. |
| Jev operational risk | Can upstream Jev safely own an everyday Chrome profile or treat `DONE` as a completion verdict? | No. The WBCP wrapper must own a non-default profile and debugging endpoint; `DONE` is only a candidate signal for an independent verifier. |
| External-model egress | Can Jev call a model provider by default? | No. The candidate defaults to deny and has no paid API smoke in its acceptance path. |
| CUA runtime | Is the installed driver already at the validated reference? | No. Installed `0.21.0`; the official stable-channel check currently selects `0.28.2`. Upgrade is a separate reversible local gate. |
| CUA permissions | Can an update be treated as TCC success? | No. A version change must be followed by daemon-owned permission and direct-capture verification; any interactive prompt remains user-controlled. |
| Fallback after mutation | Is an engine switch safe after a timeout or ambiguous mutation? | No. The originating scope stays pending until trusted reconciliation records a terminal-safe result. |

## Sources and independent evidence

1. Local WBCP `0.2.0a1` source and package manifests were independently verified with its own verifier before reconstruction.
2. The exact Jev source was read from commit `1231850a0bf1a0c0341fe408ef1668dbbfdfac46`; its `pyproject.toml` declares `jev-ultrafast==0.1.0`, Python `>=3.12`, and `browser-harness==0.1.13`.
3. The `browser-harness` package index exposes `0.1.13`; no package is installed into the candidate at this stage.
4. The official CUA CLI, on the stable channel, reports `0.21.0 -> 0.28.2` through `cua-driver check-update --json` and names the supported `cua-driver update --apply` path. The exact release is `cua-driver-rs-v0.28.2`.
5. The official CUA installer documents an atomic release-directory/current-link layout and preserves the `com.trycua.driver` bundle identity; this informs, but does not replace, the local backup and post-update health gate.

## Methods considered

| Method | Decision | Reason |
| --- | --- | --- |
| Promote or patch the incomplete remote `d3aa0ba…` branch | Rejected | It lacks the full source root, package metadata, and a complete binary-safe delivery. |
| Reconstruct from prose alone | Rejected | Prose is insufficient source authority when a manifest-verified local baseline exists. |
| Reconstruct in place in the active OneClick runtime | Rejected | It would risk the known-good `0.2.0a1` runtime before candidate verification. |
| Directly attach upstream Jev to a personal Chrome profile | Rejected | It violates default-deny profile isolation and existing-profile approval requirements. |
| Use CUA `0.21.0` as a validated candidate dependency | Rejected | It is below the exact validated stable reference. |
| Reconstruct from the verified baseline in a clean `comfy` worktree, with local fixtures and fail-closed adapters | Selected | It is reproducible, reversible, has zero paid API cost, and preserves the active runtime until all candidate gates pass. |

## Selected execution path

1. Complete the source-level `0.3.0a1` candidate in the isolated worktree only.
2. Add tests that prove deterministic Playwright precedence, Jev default-deny conditions, Jev independent-verifier semantics, CUA binding rejection, and side-effect reconciliation.
3. Regenerate manifests and deterministic package artifacts only after source and tests stabilize.
4. Verify the candidate from a fresh extraction and then publish one new complete branch and a Draft PR without merging.
5. Bind a new local candidate environment to that exact remote commit, archive, and manifest set.
6. Re-check the official CUA stable channel immediately before a reversible update; back up only CUA app/config state, never browser or personal-profile data. If the update or direct-capture verification requests interactive permission, stop for the exact user-controlled UI action.
7. Install Jev/browser-harness only into the candidate's isolated Python environment, use fixtures/mocks for acceptance, and keep `JEV_LIVE_PAID_SMOKE=BLOCKED_PAID_API_NOT_AUTHORIZED`.
8. Deploy atomically only after every preceding gate passes; perform an actual rollback-health test before any optional reapply.

## Cost, rollback, and stop conditions

- Planned paid spend: `0` credits and `0` paid API calls.
- No default Chrome profile, authentication state, TCC database, payment setting, or existing-profile grant may be modified by this path.
- Stop immediately on a manifest mismatch, a non-deterministic package rebuild, failed fresh-extraction tests, an unexpected production-ready release-gate verdict, a CUA interactive permission prompt, a source identity mismatch, or a pending possible-mutation scope without trusted reconciliation.
- Rollback boundaries: the active WBCP `0.2.0a1` backup remains untouched; the CUA update must retain a recoverable previous application/config state; candidate deployment must restore the pre-deployment WBCP runtime and then verify `wbcp_browser` health.

## Success and failure criteria

`RESEARCH_PASS=true` applies only to the zero-cost, isolated candidate reconstruction and its Draft-PR publication path. It does not authorize production promotion, paid Jev traffic, use of a personal profile, a CUA permission grant, or deployment before their separate gates are satisfied.

- Success: full manifests, compile, actual-count test suite, MCP stdio and HTTP smoke, security/sensitive-file scans, reproducible archive rebuild, fresh extraction tests, and an explicitly production-blocked release-gate verdict all pass; the remote branch and Draft PR contain the complete source tree and exact receipts.
- Failure: any missing source artifact, stale/fabricated test count, mutable fallback without reconciliation, unsupported Jev feature, CUA binding override, paid external request, or production-ready verdict blocks advancement.

## Gate verdict

```text
RESEARCH_PASS=true
AUTHORIZED_NEXT_EXECUTION=isolated_candidate_source_completion_and_zero_cost_verification
NOT_AUTHORIZED=paid_Jev_smoke, personal_profile_attachment, production_promotion, merge, CUA_permission_grant, candidate_deployment
```
