# Test and CI Evidence — 2026-09-14

## Local deterministic gate tests

- Registry/contract validation: **PASS**, 40 records, 0 errors.
- New capability/route unit suite: **15/15 PASS**.
- Unverified H3.1 request to `LIN_3D_FINAL`: expected **DENY**, observed `BLOCKED_CAPABILITY_NOT_VERIFIED_FOR_LIN_3D`, exit 2.
- Exact H3.1 request to isolated `LIN_3D_VALIDATION` with all three isolation flags: expected **ALLOW**, observed `CAPABILITY_AUTHORIZED`; production mutation remains false.
- Exact generic fail-closed guard request: expected **ALLOW**, observed `CAPABILITY_AUTHORIZED`; canon promotion remains false.
- Python compilation for guard, adapter, and new tests: **PASS**.

Machine-readable receipt: `LOCAL_TEST_RECEIPT_2026-09-14.json`.

## GitHub Actions

Candidate-branch bootstrap and branch-wide regression: **PASS**. Run: `https://github.com/Kyuha927/comfy/actions/runs/34771461244`. The run verified payload hashes, current-base reconciliation, the hash-checked private LIN authority preflight receipt, the existing failure catalog, capability registry/contract validation, explicit final-path denial, isolated-validation authorization, generic guard authorization, Python compilation, and the complete `unittest` discovery suite (30 tests).

## Evidence boundary

These results prove the implementation's fail-closed behavior. They do **not** prove Tripo geometry quality, live Bridge transport, selected-LIN same-scene execution, fresh-process Blender reopen/rollback, ART_MASTER, Mobile Hero, or real-device readiness. No Tripo credit, Blender production scene, canon, or merge was mutated.
