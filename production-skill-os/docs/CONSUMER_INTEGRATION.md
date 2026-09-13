# Consumer integration contract

Production Skill OS is a read-mostly evidence and selection layer. It is not a second
orchestrator, does not execute a capability merely because it is registered, and never
promotes LIN canon automatically.

## Mandatory selection call

Every consumer that selects a registered capability must call:

```bash
python production-skill-os/adapters/authorize_capability.py   --capability-id <ID>   --version <PINNED_VERSION_OR_COMMIT>   --scope <GENERIC_PRODUCTION|LIN_3D_VALIDATION|LIN_3D_FINAL>   --lin-authority-head <CURRENT_LIN_HEAD>
```

The executable source of truth is:

- `tool-intake/TOOL_CAPABILITY_REGISTRY.json`
- `tool-intake/SELECTION_CONTRACT.json`
- `router/capability_guard.py`

Do not infer permission from this prose, a PR description, green CI, provider documentation,
or an earlier chat.

## Scope behavior

`GENERIC_PRODUCTION` allows only exact-version `ABSORBED_GENERIC` or
`VERIFIED_FOR_LIN_3D` records explicitly authorized for that scope.

`LIN_3D_VALIDATION` is non-production. It permits explicitly scoped `REVIEWED`,
`TEST_REQUIRED`, `ISOLATED_PASS`, or `LIN_3D_TEST_REQUIRED` records only when all three
flags are supplied:

```text
--isolated-workspace
--no-production-mutation
--no-canon-mutation
```

`LIN_3D_FINAL` permits only `VERIFIED_FOR_LIN_3D` with exact version, L8 same-path PASS,
artifact IDs, regression PASS, rollback evidence, and the current reconciled LIN authority
head. At initial integration `VERIFIED_FOR_LIN_3D=0`, so the final external capability path
correctly denies all requests.

## Current LIN binding

Current reconciled project authority:

```text
repo=Kyuha927/lastline-echoes
branch=lin-aster-tripo-r01-20260913
head=e1b02b1773366677a543d764bd68638e13da1a27
SSOT_BLOB=612fd6347f7d203f9b6d8a3737a72bbaf7a6f0fe
LIVE_STATE_BLOB=f44c283bd5c02a1a8e8b3adf7785c867d78b0c2f
POLICY=LIN_ASTER_3D_PRODUCTION_CONTROL_V1_2
```

If the branch advances, reconcile the new authority and update the registry in a reviewed
candidate change before further LIN authorization.

The current R04 path is:

```text
locked canon
→ lineage-tracked non-canon component references
→ H3.1 Ultra head
→ H3.1 Ultra hair
→ H3.1 Ultra body/outfit
→ H3.1 Ultra coat/garment
→ part QA and raw export
→ supervised Blender assembly
→ controlled/manual retopology and reconstruction
→ deterministic state/pixel/save/reopen/rollback evidence
→ user review
```

`P2_FULL_BODY_PRIMARY_HERO_BASE=false`. Do not route the superseded P2 full-body hero
capability. R03 A remains scaffold evidence; R03 B remains a provisional detail donor.

## Model and tool boundaries

- Tripo H3.1 is a candidate component source, not acceptance authority.
- Astra Computer Use is the visual/spatial supervised assembly lane after authorization.
- Sol Pro is the default analysis, specification, and delta-QA layer.
- Blender Bridge/MCP is the exact deterministic state-critical and receipt lane after authorization.
- Reviewed bpy/headless execution is bounded deterministic support after authorization.
- Human correction is allowed only when recorded and independently verified.
- USER is final lock authority.

No provider/API/tool call receipt is production proof. No silent fallback is allowed.

## Required handoff packet

The consumer must preserve capability ID, exact version/commit, requested scope, guard
decision/code, current authority SHA, inputs and hashes, environment, execution path, output
artifact IDs, costs, failures, recovery, rollback, regression result, visible defects, next
gate, and user-review state.

A validation result may update evidence and propose a status change. It must not mutate the
registry to `VERIFIED_FOR_LIN_3D` without reviewed L8 evidence, and must not mutate production
assets or canon.

## Merge-omission rejection

Reject any merge/integration that omits any of these:

- registry structural validation and unique capability IDs;
- exact-version authorization;
- stale LIN authority rejection;
- validation isolation flags;
- `VERIFIED_FOR_LIN_3D`-only final gate;
- same-path, artifact, regression, and rollback requirements;
- R04 H3.1 component route and P2 full-body supersession;
- immutable canon versus lineage-tracked non-canon reference distinction;
- geometry-before-texture;
- supervised non-one-shot Blender loop;
- deterministic checkpoint/render/fresh-process reopen/rollback;
- explicit user review and no automatic canon or merge.

## Existing failure-knowledge binding

The existing `skill_router.py`, failure catalog, evidence events, and promotion engine remain
available for bounded failure knowledge. They do not bypass capability authorization. A
canonical failure repair record is not automatically a `VERIFIED_FOR_LIN_3D` tool capability.
