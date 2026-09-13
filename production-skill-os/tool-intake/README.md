# Global Tool Capability Intake and LIN 3D Gate

This directory is the durable, executable intake boundary between discovered tools and the
final LIN ASTER 3D production path.

Read in this order:

1. `TOOL_STACK_SSOT.md`
2. `TOOL_CAPABILITY_REGISTRY.json`
3. `SELECTION_CONTRACT.json`
4. `PORTFOLIO_RECONCILIATION_2026-09-14.md`
5. `ADOPTION_GAP_REPORT_2026-09-14.md`
6. `VERIFIED_FOR_LIN_3D.md`
7. `LIN_3D_TEST_REQUIRED.md`
8. `WATCH_REJECTED_SUPERSEDED.md`
9. `TEST_AND_CI_EVIDENCE.md`
10. `CURRENT_HANDOFF.md`

The registry records a capability; it does not authorize execution by itself. Authorization
comes only from `router/capability_guard.py` using one exact capability ID, version/commit,
scope, and current LIN authority head.

Current candidate invariant: **zero external capabilities are verified for the final LIN 3D
path**. This is intentional fail-closed behavior, not permission to fall back silently.

No file in this directory changes a Blender scene, consumes Tripo credits, merges a branch,
or promotes canon. Final lock authority remains the user.
