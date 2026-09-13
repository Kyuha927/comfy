# Scoped Agent Rule — Production Skill OS / LIN ASTER 3D

Before any LIN ASTER 3D, Tripo, Blender, Bridge, reconstruction, ART_MASTER,
MOBILE_HERO_MASTER, capability-adoption, or promotion action under this tree:

1. Re-read the current project authority:
   `Kyuha927/lastline-echoes@lin-aster-tripo-r01-20260913/work/handovers/2026-09-13/00_READ_FIRST_LIN_ASTER_3D_ROUTE.md`.
2. Re-read `LIN_ASTER_3D_LIVE_STATE.json` and reject a stale authority SHA.
3. Read `tool-intake/TOOL_STACK_SSOT.md`, `TOOL_CAPABILITY_REGISTRY.json`, and `SELECTION_CONTRACT.json`.
4. Call `adapters/authorize_capability.py` before selecting a registered capability.

Hard rules:

- `LIN_3D_FINAL` is fail-closed and accepts only `VERIFIED_FOR_LIN_3D` at the exact pinned version with L8 same-path, regression, and rollback evidence.
- `LIN_3D_VALIDATION` requires an isolated workspace plus explicit no-production/no-canon mutation flags.
- Unknown, stale, blocked, failed, watch, rejected, or superseded capabilities do not enter a production path.
- Provider documentation, repository tests, isolated tests, and green CI are not LIN same-path proof.
- The R04 maximum-quality component route is current. P2 full-body is not the LIN hero authority.
- Production Skill OS is a selection/evidence layer, not a second orchestrator.
- Do not mutate the frozen Blender Bridge acceptance workspace or a current LIN production asset while validating this gate.
- Do not auto-merge, auto-promote canon, or convert user review into an automatic gate.
- Final lock authority remains `USER_ONLY`.
