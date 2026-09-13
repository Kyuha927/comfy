# ONE-SHOT HANDOFF — CONTINUE BLENDER CONTROL-PLANE WORK WITHOUT DISTURBING ACTIVE ACCEPTANCE TESTS

## Routing

- Preserve the receiving chat's **currently active main model and reasoning level**. Do not reroute merely because of this handoff.
- Do not create additional subagents unless the receiving chat already had an explicitly approved bounded worker lane.
- Record the actually observed model/profile/effort in the final receipt. No silent fallback.

## Mission

Continue the currently active Blender control-plane integration work, but do **not** disturb the existing Blender Pro Bridge `0.5.0a2 LOCAL_ACCEPTANCE` validation lane and do **not** promote the new control-plane to production canon yet.

The target candidate architecture is:

```text
approved character references
-> Tripo-first character generation
-> Blender import
-> GPT-6 Astra Computer Use as the primary visual / interactive Blender operator
-> Blender Bridge / MCP as the deterministic inspection / exact-operation / QA / checkpoint / rollback / receipt plane
-> bounded headless or scripted workers only for repetitive, deterministic, non-visual work
```

This architecture is a **candidate migration**, not yet production canon.

## Current verified state to preserve

### A. Blender Pro Bridge 0.5.0a2 acceptance candidate

Authoritative reference:

`https://github.com/Kyuha927/angrydino-visual-handoff/blob/e8095fea25cb2f8a1eb56dcb2b7be442d5ffa854/validation/blender-unified/START_HERE.md`

Known state:

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

It already contains a candidate skill named:

`production-skill-os/skills/blender-character-tripo-astra/SKILL.md`

That candidate captures the intended direction:

- Tripo before Blender for character generation;
- do not use Astra for zero-base character mesh creation when a usable Tripo route exists;
- Astra Computer Use as the primary interactive Blender lane;
- Bridge/MCP as the deterministic verification and state-critical lane;
- visible checkpoint / inspect / bounded-correction loops;
- user approval before canon/final lock.

However this PR is still a **draft candidate**. It is not production canon and must not be merged merely because its CI passes.

### C. LIN ASTER Tripo generation candidate

Latest Tripo execution handoff:

`https://github.com/Kyuha927/lastline-echoes/blob/lin-aster-tripo-r01-20260913/work/handovers/2026-09-13/LIN_ASTER_TRIPO_GENERATION_ONE_SHOT_LATEST.md`

Canonical four-view authority remains separate and must not be rewritten by this task.

The current LIN input situation includes a valid locked full-body four-view set. Do not invent missing part-specific multiview references. A HEAD / HAIR / BODY_CLOTHING route may be developed as the target production strategy, but execution must remain source-gated when complete approved part packets do not yet exist.

## Non-negotiable execution boundaries

### 1. CONTINUE development

Do continue:

- control-plane code and routing integration on an isolated candidate branch/worktree;
- Tripo-first policy wiring;
- Astra Computer Use primary-interaction policy;
- Bridge deterministic-boundary policy;
- merge-omission guards;
- tests that prevent regression to MCP-primary creative interaction;
- tests that prevent Astra zero-base character modeling when Tripo is available;
- tests that preserve exact Bridge inspection/checkpoint/rollback responsibilities;
- tests for source-gated HEAD / HAIR / BODY_CLOTHING routing;
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
- mark the Production Skill OS PR ready or merged solely from unit/CI success;
- claim the Bridge is native/Web verified before actual evidence exists;
- claim the Tripo -> Astra Computer Use -> Bridge pipeline is production-complete before an end-to-end character run exists;
- delete or rewrite the old production route while the new route is still candidate.

### 4. Do not use fixed percentages such as "Computer Use 99%" as the architecture contract

Use role boundaries instead:

- **Computer Use primary** for visual, spatial, interactive, supervised Blender work;
- **Bridge/MCP primary** for deterministic inspection, exact repeated/state-sensitive edits, typed operations, durable jobs, renders/pixel evidence, checkpoint/save, cancellation, rollback, recovery, and receipts;
- **headless/scripts** for repetitive deterministic non-visual work when justified.

The routing decision must depend on operation type and evidence, not an arbitrary percentage.

## Required reconciliation work

Inspect the current candidate code, current handoffs, and current acceptance evidence. Then reconcile the following without weakening safety:

1. Ensure Tripo-first character generation is represented as the candidate default when authoritative inputs support it.
2. Ensure Astra zero-base character mesh creation is not a silent fallback.
3. Ensure Astra Computer Use is the primary interactive Blender lane in the candidate architecture.
4. Ensure Bridge/MCP remains available and first-class for deterministic/state-critical operations rather than being removed.
5. Ensure the existing Bridge acceptance candidate can finish independently under its frozen test conditions.
6. Resolve the current policy conflict between:
   - mandatory `HEAD / HAIR / BODY_CLOTHING` split in the candidate Skill OS; and
   - the presently available LIN ASTER full-body canonical four-view pack.

The safe rule is:

```text
IF complete approved part-specific source packets exist:
    use the part-split production route.
ELSE IF a complete approved full-body multiview packet exists:
    allow the full-body Tripo candidate lane,
    keep part-split as the preferred future production strategy,
    and do not fabricate part multiview references.
ELSE:
    block generation with an exact missing-source reason.
```

7. Preserve user approval as the final gate for canon or production-route promotion.

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
-> Tripo candidate generated
-> actual exported artifact verified
-> Blender import
-> Astra Computer Use performs visible assembly/correction
-> Bridge inspects the same scene and revision
-> exact deterministic operation succeeds where required
-> fixed-camera real render/pixels verified
-> checkpoint/save succeeds
-> fresh-process reopen succeeds
-> rollback/restore succeeds
-> no silent-success or wrong-scene behavior
-> receipts tie every stage to exact artifacts/revisions
-> user review remains separate from automatic pass
```

The existing `0.5.0a2` Mac acceptance result may satisfy part of the Bridge evidence, but it does not by itself prove the entire new control-plane.

## Validation requirements for this continuation

Before reporting completion of this task:

- run the candidate branch's deterministic/unit/regression tests;
- verify that no current acceptance workspace was modified;
- inspect diffs against the exact base branch;
- confirm no unrelated branch content was accidentally pulled in;
- confirm no production `main` or canon migration occurred;
- record exact HEAD SHA(s);
- record CI/local test results separately;
- label anything not actually run as `NOT_RUN` or `UNKNOWN` rather than inferring success.

If CI cannot start, do not equate that with code failure. Record the CI execution failure separately and use local deterministic validation where possible. Do not claim native Blender validation from test doubles.

## Completion state for THIS handoff

This handoff is complete when the receiving chat has:

1. continued implementation safely in an isolated candidate workspace;
2. preserved the current Bridge acceptance run unchanged;
3. reconciled the Tripo-first / Computer-Use-primary / Bridge-verification candidate architecture;
4. added or updated regression guards for the control-plane priority;
5. emitted a candidate checkpoint suitable for later Production Skill OS ingestion;
6. reported the exact remaining gates before production promotion.

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