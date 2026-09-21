# CUA Driver 0.21.0 to 0.28.2 — Research Gate Receipt

## Binding

- Task: WBCP + Jev + CUA local candidate continuation, Phase C only.
- Candidate source: `313926dd54018c7bc74d78dc3101c85636c99b84` / subtree `e50635bca7d2f66218743dd780aac20674861a54`.
- Installed application before activation: `/Applications/CuaDriver.app`, bundle ID `com.trycua.driver`, version `0.21.0`.
- Installed application signer: `Developer ID Application: Cua AI, Inc. (YCK386LBJ7)`; notarization ticket present.
- Selected official release: `trycua/cua` tag `cua-driver-rs-v0.28.2`, target `fc188250b4ca8549b8e61f937fdb1fb560770e86`.
- Release manifest SHA-256: `fce29f1135000b206aa682d3171114d7261499ee76105b8fa551bb61050bcbd1`.
- Required rollback backup path: `/Users/macpro/.codex/backups/wbcp-jev-cua-cua-driver-0.21.0-preupgrade-20260922T014233+0900`.

## Problem redefinition and unknown-unknown sweep

This is not an arbitrary binary replacement. It is a narrow, reversible update of the app-owned CUA Driver while preserving its daemon identity, existing permission state, standard/trusted startup mode, and the WBCP candidate's bounded-driver requirement. The sweep checks the official selected channel, exact release identity and manifest, code-signing provenance, installer route, TCC boundary, rollback material, and the possibility that a release is labeled differently by separate official surfaces.

| Question | Evidence and decision |
| --- | --- |
| Which stable release does the installed official driver select now? | `cua-driver check-update --json --no-cache` on the signed `0.21.0` app reports selected/current channel `stable`, latest `0.28.2`, and `update_available=true`. |
| Is the exact release independently identifiable? | The official GitHub release object and its `release-manifest.json` bind `cua-driver-rs-v0.28.2`, target `fc188250b4ca8549b8e61f937fdb1fb560770e86`, and the manifest SHA above. |
| Is the update mechanism official and bounded? | The signed app's own help identifies `cua-driver update --apply` as its canonical installer path. Manual release-asset installation, Homebrew, and arbitrary installer scripts are rejected. |
| Is there a release-label discrepancy? | Yes. GitHub currently marks the tag `prerelease=true`, while the signed driver explicitly selects it from its `stable` channel. The updater's own stable-channel result is the product-level selector for this bounded attempt; no channel change is permitted. Any resolved version other than `0.28.2` is a stop condition. |
| Can an update substitute for TCC verification? | No. Post-update checks must be daemon-owned `permissions status`, direct-capture/capturability where supported, and `status`/`doctor`; no permission prompt may be accepted or bypassed. |
| Is rollback practical without copying private browser data? | Yes. Back up only the signed app bundle and its exact CUA launch-agent configuration. Do not copy browser profiles, cookies, recordings, history, TCC databases, or personal page data. |

## Methods considered

| Method | Decision | Reason |
| --- | --- | --- |
| `cua-driver update --apply` from the signed app while the selected channel remains `stable` | Selected | It is the app's documented canonical installer and is bound to the just-checked exact target. |
| Download and unpack a GitHub asset manually | Rejected | It bypasses the app's supported updater and expands installation risk. |
| Change to nightly or use the GitHub prerelease flag to select a different build | Rejected | The user requested the current supported stable path; no channel mutation is authorized. |
| Treat existing TCC grants as a successful post-update capture test | Rejected | The daemon must report its own post-update state; any interactive grant remains user-controlled. |

## Cost, stop conditions, and recovery

- Paid cost: none. No API call, paid model, browser profile, account, or default Chrome setting is in scope.
- Precondition: the required app/LaunchAgent backup must verify before invoking the updater.
- Stop immediately if the official updater asks for an interactive permission/security prompt, resolves another version/channel, breaks code-signing/bundle identity, produces an unhealthy daemon, loses Accessibility or Screen Recording status, or fails bounded/standard mode verification.
- Recovery: stop the new daemon if it is app-owned, restore the backed-up `/Applications/CuaDriver.app` and exact CUA LaunchAgent, reload only that agent, then verify the restored `0.21.0` daemon health. Do not touch TCC or user browser state.

## Gate verdict

```text
RESEARCH_PASS=true
AUTHORIZED_NEXT_EXECUTION=one official CUA Driver stable-channel update attempt to exactly 0.28.2 after verified app/LaunchAgent backup
NOT_AUTHORIZED=nightly selection, manual binary installation, TCC grant, default/personal-profile access, paid Jev smoke, WBCP candidate deployment, production promotion, merge
```
