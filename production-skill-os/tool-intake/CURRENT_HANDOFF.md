# Current Handoff — Global Capability Gate to LIN 3D

```text
HANDOFF_ID=GLOBAL_TOOL_CAPABILITY_TO_LIN_3D_VALIDATION_IMPLEMENTED_20260914
STATUS=CANDIDATE_GITHUB_ACTIONS_TESTED_READY_FOR_REVIEW
COMFY_BRANCH=candidate/tool-capability-lin3d-gate-v2-20260914
COMFY_BASE_HEAD=7f9c5701a77d341bd7ca680b06242980600000dd
LIN_AUTHORITY_HEAD=e1b02b1773366677a543d764bd68638e13da1a27
REGISTRY_RECORDS=40
VERIFIED_FOR_LIN_3D=0
ABSORBED_GENERIC=2
AUTO_MERGE=false
AUTO_CANON_PROMOTION=false
FINAL_LOCK_AUTHORITY=USER_ONLY
```

## Start here

1. Local registry/contract validation and the capability suite are PASS.
2. GitHub Actions branch-wide regression is PASS: https://github.com/Kyuha927/comfy/actions/runs/34771461244.
3. Inspect the isolated candidate; do not merge or promote canon automatically.
4. Use only the capability adapter for selection.
5. For the first real LIN evidence, authorize one exact R04 component capability under isolated
   `LIN_3D_VALIDATION`; do not use `LIN_3D_FINAL` until a reviewed L8 record exists.

## Current blockers

- no R04 selected component set;
- no external `VERIFIED_FOR_LIN_3D` record;
- live Blender Bridge tunnel probe returned 404;
- no selected-LIN same-scene edit/render/save/reopen/rollback evidence;
- no ART_MASTER, Mobile Hero, or real-device evidence.

This handoff does not authorize a merge, canon change, paid generation, or production scene mutation.
