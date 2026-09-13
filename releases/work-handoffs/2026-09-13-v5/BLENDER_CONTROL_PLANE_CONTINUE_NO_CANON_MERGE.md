# ONE-SHOT HANDOFF - CONTINUE BLENDER CONTROL-PLANE WORK WITHOUT DISTURBING ACTIVE ACCEPTANCE TESTS

## Routing

- Preserve the receiving chat's **currently active main model and reasoning level**. Do not reroute merely because of this handoff.
- Do not create additional subagents unless the receiving chat already had an explicitly approved bounded worker lane.
- Record the actually observed model/profile/effort in the final receipt. No silent fallback.

## Mission

Continue the currently active Blender control-plane integration work, but do **not** disturb the existing Blender Pro Bridge `0.5.0a2 LOCAL_ACCEPTANCE` validation lane and do **not** promote the new control-plane to production canon yet.

The target candidate architecture is:

```text
approved character references
-> character-specific source and route preflight
-> Tripo-first character generation
-> geometry acceptance before texture commitment
-> Blender import
-> GPT-6 Astra Computer Use as the primary visual / interactive Blender operator
-> optional recorded human manual correction when faster or safer
-> Blender Bridge / MCP as the deterministic inspection / exact-operation / QA / checkpoint / rollback / recovery / receipt plane
-> bounded headless or scripted workers only for repetitive, deterministic, non-visual work
```

This architecture is a **candidate migration**, not yet production canon.

## Immediate merge-omission guard

Do not report this reconciliation as complete merely because a high-level phrase such as `Tripo -> Astra -> Bridge` appears in one document.

The receiving work must re-read the current HEAD of all three candidate files and preserve their combined contract:

```text
production-skill-os/skills/blender-character-tripo-astra/SKILL.md
production-skill-os/docs/CONSUMER_INTEGRATION.md
production-skill-os/tests/test_blender_character_route.py
```

A merge or integration candidate is incomplete if any of the following is absent from the resulting files and regression coverage:

1. Tripo-first when an authorized usable Tripo route exists.
2. No silent Astra zero-base character-mesh fallback.
3. Source-gated choice between `DEDICATED_PART_REFERENCES` and `FULL_BODY_MULTIVIEW_PART_AWARE`.
4. Dedicated production hair requires front, left, right, and back references; single-view hair remains provisional.
5. Head soft-start target near 2,000 to 5,000 polygons unless justified otherwise.
6. Actual recessed orbital structure plus independently addressable eyes and pupils/irises.
7. Candidate regeneration and geometry inspection before texture commitment; preserve rejected Tripo job IDs and reasons.
8. Astra Computer Use is primary for supervised visual, spatial, interactive Blender work.
9. Bridge/MCP remains first-class for deterministic, repeated, state-sensitive, auditable, recoverable operations.
10. No one-shot or fully unattended character build; use visible stage checkpoints and bounded correction turns.
11. Character-specific preflight and route decision because the flow varies by design and generated structure.
12. Human manual placement or cleanup is permitted when faster or safer, but must be recorded and independently verified.
13. Do not force destructive neck welding; separate aligned meshes may pass when camera, shading, and deformation evidence passes.
14. Discrete expression-head mesh/state switching is the stable fallback when shape-key correspondence is not proven.
15. Rigging and secondary-motion helper apps, add-ons, scripts, and templates must be declared with exact version and artifact identity.
16. Fixed-camera pixels, checkpoint, fresh-process reopen, rollback, and user review remain separate mandatory gates.

A green CI run that does not test these contracts is not sufficient evidence of successful reconciliation.

## Current verified state to preserve

### A. Blender Pro Bridge 0.5.0a2 acceptance candidate

Authoritative reference:

`https://github.com/Kyuha927/angrydino-visual-handoff/blob/e8095fea25cb2f8a1eb56dcb2b7be442d5ffa854/validation/blender-unified/START_HERE.md`

Known published state:

- packaged source regression: 340 tests PASS;
- packaged-source re-test: 340 tests PASS;
- launcher/package integrity checks PASS;
- actual Blender on the user's Mac: `NOT_RUN` in the published acceptance record;
- actual Web ChatGPT path: `NOT_RUN` in the published acceptance record;
- published verdict: `OFFLINE_TESTED_NATIVE_AND_WEB_NOT_VERIFIED`;
- production replacement is **not approved**.

If a separate local Mac acceptance run has already started outside this chat, treat its exact source/build/workspace/test conditions as frozen evidence. Do not inject this new routing policy or any new code into that running acceptance environment.

### B. Production Skill OS candidate

Draft PR:

`https://github.com/Kyuha927/comfy/pull/1`

Current candidate branch:

`production-skill-os-clean-20260913`

Required candidate files:

```text
production-skill-os/skills/blender-character-tripo-astra/SKILL.md
production-skill-os/docs/CONSUMER_INTEGRATION.md
production-skill-os/tests/test_blender_character_route.py
```

The receiving chat must read the current branch HEAD rather than relying on an older copied prompt, PR description, or cached file. Concurrent updates have already occurred on this branch.

The candidate direction is:

- Tripo before Blender for character generation;
- do not use Astra for zero-base character mesh creation when a usable Tripo route exists;
- Astra Computer Use as the primary interactive Blender lane;
- Bridge/MCP as the deterministic verification and state-critical lane;
- visible checkpoint, inspect, bounded-correction loops;
- user approval before canon/final lock.

However this PR remains a **draft candidate**. It is not production canon and must not be merged merely because CI passes.

### C. LIN ASTER Tripo generation candidate

Latest Tripo execution handoff:

`https://github.com/Kyuha927/lastline-echoes/blob/lin-aster-tripo-r01-20260913/work/handovers/2026-09-13/LIN_ASTER_TRIPO_GENERATION_ONE_SHOT_LATEST.md`

Canonical four-view authority remains separate and must not be rewritten by this task.

The current LIN input situation includes a valid locked full-body four-view set. Do not invent missing part-specific multiview references. A `HEAD / HAIR / BODY_CLOTHING` route may be developed as the preferred target production strategy, but execution must remain source-gated when complete approved part packets do not yet exist.

## Non-negotiable execution boundaries

### 1. CONTINUE development

Do continue:

- control-plane code and routing integration on an isolated candidate branch/worktree;
- Tripo-first policy wiring;
- Astra Computer Use primary-interaction policy;
- Bridge deterministic-boundary policy;
- character-specific route preflight;
- merge-omission guards;
- tests that prevent regression to MCP-primary creative interaction;
- tests that prevent Astra zero-base character modeling when Tripo is available;
- tests that preserve exact Bridge inspection/checkpoint/rollback responsibilities;
- tests for source-gated `HEAD / HAIR / BODY_CLOTHING` versus full-body-part-aware routing;
- tests for geometry-before-texture, hair multiview, head eye-geometry, non-destructive neck seam, expression mesh switching, helper dependency declarations, and supervised non-one-shot operation;
- candidate documentation and receipts;
- local deterministic tests that do not mutate the active acceptance workspace.

### 2. FREEZE the active 0.5.0a2 acceptance conditions

Do not modify, replace, rebase, rewrite, or hot-patch any checkout/workspace/build currently being used for the existing `0.5.0a2 LOCAL_ACCEPTANCE` Mac test.

If this chat is operating in the **same checkout or same writable workspace** as that acceptance run:

- stop write operations in that workspace immediately;
- preserve all current files and logs;
- create or switch to an isolated branch/worktree before continuing implementation;
- do not restart or invalidate the acceptance run.

If the acceptance test is running in a separate workspace, let it continue untouched.

### 3. NO production promotion yet

Do not:

- merge the new control-plane into `main`;
- rewrite the current production canon as already migrated;
- mark Production Skill OS PR #1 ready or merged solely from unit/CI success;
- claim the Bridge is native/Web verified before actual evidence exists;
- claim the Tripo -> Astra Computer Use -> Bridge pipeline is production-complete before an end-to-end character run exists;
- delete or rewrite the old production route while the new route remains candidate;
- convert user approval into an automatic gate.

### 4. Do not use a fixed percentage as the architecture contract

Do not use a number such as `Computer Use 99%` as a testable architecture requirement. Preserve the intent through role boundaries:

- **Computer Use primary** for visual, spatial, interactive, supervised Blender work;
- **Bridge/MCP primary** for deterministic inspection, exact repeated/state-sensitive edits, typed operations, durable jobs, renders/pixel evidence, checkpoint/save, cancellation, rollback, recovery, and receipts;
- **human manual Blender work** when faster or safer, with exact before/after evidence;
- **headless/scripts** for repetitive deterministic non-visual work when justified.

The routing decision must depend on operation type, evidence, and current environment.

## Candidate operational contract

### 1. Character-specific preflight

Before spending Tripo quota or Astra tokens, record:

- authoritative references and hashes;
- image-edit permissions and locked-source restrictions;
- availability of complete `HEAD`, `HAIR`, and `BODY_CLOTHING` packets;
- full-body front, left, right, and back coverage;
- hair silhouette and unseen-side risk;
- garment, accessory, and segmentation complexity;
- polygon and deformation targets;
- required expression set;
- secondary-motion requirements;
- available Tripo, Computer Use, Bridge, Blender, and human-manual lanes;
- custom helper dependencies;
- selected route, rejected alternatives, blockers, and next gate.

The flow may vary per character. Variation must produce an explicit route decision, not an improvised fallback.

### 2. Source-gated Tripo route

Use this rule:

```text
IF complete approved part-specific source packets exist:
    use DEDICATED_PART_REFERENCES.
ELSE IF a complete approved full-body multiview packet exists:
    use FULL_BODY_MULTIVIEW_PART_AWARE,
    preserve source-image bytes,
    use Generate in Parts or copied-candidate 3D segmentation,
    keep part-split as the preferred future strategy,
    and do not fabricate part multiview references.
ELSE:
    block generation with an exact missing-source reason.
```

Prefer Tripo Smart Mesh P2.0 when available and validated. Record provider model/version, job IDs, input/output hashes, topology mode, polygon budget, texture state, segmentation strategy, export/licensing data, and rejected-candidate reasons.

### 3. Candidate and texture gate

Do not cross into texturing merely because a provider preview looks acceptable.

- Generate or regenerate candidates while geometry remains cheaply replaceable.
- Inspect the actual exported mesh.
- Reject weak geometry before texturing when possible.
- Record whether the exact Tripo version disables, limits, or complicates regeneration after texturing.
- Preserve rejected job IDs and reasons.
- Texture only after the relevant geometry gates pass or an explicit provisional exception is recorded.

Head acceptance includes a soft starting range near 2,000 to 5,000 polygons, recessed orbital structure, independently addressable eyes and pupils/irises, usable eyelids/mouth/jaw/ears/neck opening, and no fused or duplicate facial shells.

Dedicated production hair requires front, left, right, and back references. Reject fused ears/collar/neck, helmet-shell volume, floating parts, repeated strand noise, and major unseen-side invention.

### 4. Supervised Blender assembly

Use this loop rather than one unattended prompt:

```text
act
-> inspect real geometry or pixels
-> compare against approved references
-> record the smallest visible defect
-> issue one bounded correction
-> verify again
```

Astra Computer Use owns visual placement, scale, orientation, part assembly, viewport correction, and supervised setup. A skilled human may perform simple placement or cleanup when faster or safer. Record the edited objects and before/after revisions. Exact repeated or state-sensitive mutations belong to Bridge/MCP or another validated deterministic operation.

### 5. Neck seam policy

Do not force destructive welding as the default.

- First align scale, rotation, centerline, neck openings, materials, normals, and shading.
- Separate meshes may pass when required cameras and deformation checks show no functional defect.
- If joining is required, duplicate the candidate, checkpoint first, inspect both border loops, and use a reversible tested operation.
- Reject joins that damage identity, topology, weights, UVs, normals, materials, expression switching, or save/reopen stability.
- Record `SEPARATE_ALIGNED`, `JOINED_LOOP_BRIDGE`, or another justified strategy.

### 6. Expression strategy

Do not force shape keys when topology correspondence is unreliable.

- Discrete expression-head meshes and explicit mesh/state switching are the first stable fallback.
- Preserve neutral identity, scale, origin, neck alignment, eye placement, and materials across heads.
- Verify each expression in fixed cameras and after save/reopen.
- Promote to shape keys or a facial rig only after topology, correspondence, interpolation, persistence, and regression evidence pass.
- Do not create new 2D expression references without explicit authorization.

### 7. Rigging and secondary motion

Astra Computer Use may perform the supervised first pass when the imported structure is suitable. Acceptance still requires armature/bone inventory, parent/modifier audit, neutral and extreme-pose tests, collision/clipping checks, fixed-camera renders, save/reopen, rollback, and known limitations.

Any custom app, Blender add-on, helper script, or rig template must be recorded with name, version, configuration, artifact hash or commit, license, and availability. Do not claim reproducibility without it. If absent, return an exact blocker or use a separately validated standard Blender route. No silent substitution.

### 8. Bridge boundary

Bridge/MCP remains responsible for:

- `bridge_health`, scene and object inventory;
- exact revision and stable request ID;
- typed transforms and bounded property edits;
- durable jobs and terminal polling;
- render/preview hashes and deformation or garment audits;
- checkpoint/save and restore-as-new-revision;
- cancellation, recovery, exact error codes, and compact receipts.

Do not turn Bridge/MCP into the default full creative GUI operator. Do not expose arbitrary remote Python merely to imitate Computer Use.

## Required reconciliation work

Inspect the current candidate code, current handoffs, and current acceptance evidence. Then reconcile without weakening safety:

1. Ensure Tripo-first character generation is the candidate default when authoritative inputs support it.
2. Ensure Astra zero-base character mesh creation is not a silent fallback.
3. Ensure Astra Computer Use is the primary interactive Blender lane.
4. Ensure Bridge/MCP remains first-class for deterministic and state-critical operations.
5. Ensure the existing Bridge acceptance candidate can finish independently under frozen conditions.
6. Preserve the source-gated dedicated-part versus full-body-part-aware rule.
7. Preserve the complete operational gates listed in `Immediate merge-omission guard`.
8. Preserve user approval as the final gate for canon or production-route promotion.
9. Reconcile concurrent branch updates rather than overwriting newer work. Use current blob SHAs and inspect the final diff.

## Required regression coverage

At minimum, regression checks must fail if the merged result drops:

- Tripo Smart Mesh P2.0 route discovery;
- Astra Computer Use primary-interaction wording or behavior;
- Bridge deterministic/state-critical responsibility;
- no zero-base Astra fallback;
- both source route modes;
- locked-source image-edit restrictions;
- dedicated hair four-view requirement;
- head polygon, orbital, and independent-eye requirements;
- geometry-before-texture and rejected-job receipt requirements;
- supervised non-one-shot loop;
- human manual lane with verification;
- neck non-destructive strategy;
- expression mesh switching fallback;
- declared helper dependency requirements;
- fresh-process reopen, rollback, and user-review separation;
- consumer discovery and merge-omission rejection.

Run the full candidate suite, not only the new test file. Record local and CI results separately.

## Real-time convergence requirement

This chat must not behave as an isolated authority.

For every meaningful checkpoint, produce a small machine-readable candidate update containing at least:

```text
capability_id
source_repo
source_branch_or_ref
source_commit
status = candidate | tested_candidate | blocked | superseded
summary
changed_paths
execution_environment
execution_path
validation_run_ids_or_receipts
known_failures
conflicts
supersedes
next_gate
```

Do not directly mutate a canonical registry from a candidate checkpoint.

If Production Skill OS already has a compatible event/route-packet schema, use it. Otherwise create the smallest candidate-compatible event artifact on the isolated work branch and document the schema gap. Do not create a second orchestration system.

## Required end-to-end acceptance before production migration

The new control-plane cannot become production canon until one representative character path proves all of the following on the intended environment:

```text
approved refs resolved and hashed
-> character-specific route decision recorded
-> Tripo candidate generated
-> rejected candidates and texture state recorded
-> actual exported artifact verified
-> Blender import
-> Astra Computer Use performs visible assembly/correction
-> any human manual intervention recorded
-> Bridge inspects the same scene and revision
-> exact deterministic operation succeeds where required
-> neck and expression strategies verified
-> rig/deformation/secondary-motion evidence captured
-> fixed-camera real render/pixels verified
-> checkpoint/save succeeds
-> fresh-process reopen succeeds
-> rollback/restore succeeds
-> no silent-success or wrong-scene behavior
-> helper dependencies tied to exact versions/artifacts
-> receipts tie every stage to exact artifacts/revisions
-> user review remains separate from automatic pass
```

The existing `0.5.0a2` Mac acceptance result may satisfy part of the Bridge evidence, but it does not by itself prove the entire new control-plane.

## Validation requirements for this continuation

Before reporting completion:

- run the candidate branch's complete deterministic/unit/regression suite;
- verify that no current acceptance workspace was modified;
- inspect diffs against the exact base branch;
- confirm no unrelated branch content was accidentally pulled in;
- confirm no production `main` or canon migration occurred;
- re-fetch and verify the three required candidate files from current HEAD;
- record exact HEAD SHA(s);
- record CI/local test results separately;
- label anything not actually run as `NOT_RUN` or `UNKNOWN` rather than inferring success.

If CI cannot start, do not equate that with code failure. Record CI execution failure separately and use local deterministic validation where possible. Do not claim native Blender validation from test doubles.

## Completion state for THIS handoff

This handoff is complete only when the receiving chat has:

1. continued implementation safely in an isolated candidate workspace;
2. preserved the current Bridge acceptance run unchanged;
3. reconciled the Tripo-first / Computer-Use-primary / Bridge-verification candidate architecture;
4. preserved every operational rule in the merge-omission guard;
5. added or updated regression guards that actually fail when those rules disappear;
6. emitted a candidate checkpoint suitable for later Production Skill OS ingestion;
7. reported exact remaining gates before production promotion.

Do **not** merge to main or declare production-canon migration as part of this handoff.

## Final response format

Return only these sections:

1. `STATUS`
2. `WORKSPACE_ISOLATION`
3. `CURRENT_HEADS`
4. `CONTROL_PLANE_CHANGES`
5. `ACCEPTANCE_TEST_PRESERVATION`
6. `TESTS_AND_CI`
7. `CHECKPOINT_EVENT`
8. `CONFLICTS_OR_BLOCKERS`
9. `REMAINING_PRODUCTION_GATES`

Be explicit about what was actually executed versus only configured or documented.
