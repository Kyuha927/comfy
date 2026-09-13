---
name: blender-transactional-verify
description: Low-token Blender editing through typed operations, durable jobs, revision authority, pixel/state verification, and safe restore. Use for any non-trivial Blender mutation through the local bridge.
---

# Blender Transactional Verify

## Invariants
- Read the committed head revision before mutation.
- Use typed operations; do not replace a bounded operation with arbitrary code.
- Every mutation has an exact expected revision and stable request id.
- `queued` or `running` is not success.
- Lost/uncertain response does not authorize a fresh request id for the same logical edit.
- API success does not prove scene or visual correctness.

## Execution
1. `bridge_health` and `scene_info`.
2. Look up a canonical failure/operation skill if one matches.
3. Read only the geometry/state needed to discriminate the edit.
4. Submit a bounded transaction.
5. Poll to a terminal job state.
6. Confirm committed revision/state.
7. For visible output, render preview and inspect the actual pixels/receipt.
8. For garments/deformation, use bounded audit plus representative poses; audit success is not a blanket quality certificate.
9. If acceptance fails, restore the last accepted snapshot as a **new revision** and preserve history.

## Failure capture
A new failure record needs: stable fingerprint, pre-edit revision, request id/job id, operation summary, terminal state, post-state or lack thereof, preview/audit receipt when relevant, smallest discriminating probe, verified repair, rollback result.
