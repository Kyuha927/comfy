# Production Skill OS — 2D × Blender × Unity

Purpose: turn repeated production failures into compact, evidence-gated skills so later runs spend tokens on novelty, not rediscovering known traps.

This is a **cross-cutting substrate**, not a new orchestration lane. It is intended to be consumed by the existing Blender Bridge, Unity Agent, Game Development Core, visual-production, and tech-intake lanes.

## Non-negotiable rule

**Failure → bounded diagnosis → verified repair → regression proof → skill promotion.**

A successful tool/API receipt is never enough. A skill becomes `canonical` only after the target project reproduces the failure and proves the repair through the same execution path used in production.

External tips, including useful patterns extracted from `psmon/pencil-creator`, start as `external_advisory`. Newly observed local failures start as `candidate`. Neither status permits automatic repair.

## Why this saves tokens

1. **Compress before reasoning.** Video/reference analysis uses coarse-to-fine summaries/contact sheets instead of pushing every frame into the model.
2. **Route by fingerprints.** Exact failure codes and small stable fingerprints select a bounded skill instead of rereading project history.
3. **Push repetition into scripts.** Repeated transforms, validation, capture, import checks, and catalog lookup should be deterministic code.
4. **Carry delta-only state.** Reuse revision/build/package/version receipts rather than restating the whole scene/project.
5. **Escalate only novelty.** Known canonical failure → deterministic path. Ambiguous known problem → normal reasoning. New architectural/visual failure → strongest reviewer.

## Layout

```text
production-skill-os/
├── README.md
├── router/
│   ├── skill_router.py
│   └── failure_catalog.jsonl
├── skills/
│   ├── 2d-motion-compression/SKILL.md
│   ├── blender-transactional-verify/SKILL.md
│   ├── unity-playmode-verify/SKILL.md
│   └── failure-to-skill-promotion/SKILL.md
└── tests/test_skill_router.py
```

## Router contract

The router **does not execute repairs**. It only returns one bounded record.

```bash
python production-skill-os/router/skill_router.py validate
python production-skill-os/router/skill_router.py lookup \
  --domain unity \
  --text "skinned mesh frozen using AnimationMode SampleAnimationClip offscreen"
```

Default lookup considers `canonical` records only. To inspect external/candidate knowledge:

```bash
python production-skill-os/router/skill_router.py lookup \
  --include-advisory \
  --domain unity \
  --text "skinned mesh frozen using AnimationMode SampleAnimationClip offscreen"
```

Advisory matches return `auto_execute_allowed: false` and `escalate: true`.

## Promotion states

| State | Meaning | Automatic repair? |
|---|---|---:|
| `external_advisory` | useful elsewhere, not reproduced here | No |
| `candidate` | observed locally, repair not yet proven enough | No |
| `canonical` | local reproduction + repair + regression evidence | Yes, within its bounded contract |
| `deprecated` | superseded or invalidated | No |

Minimum promotion evidence:

- stable fingerprint or exact error code;
- smallest discriminating diagnosis probe;
- verified repair with version/context constraints;
- same-path verification, including visual/runtime evidence where relevant;
- rollback/recovery path;
- at least one regression test or reproducible smoke;
- source receipt (revision/build hash/screenshot/render/job id/log excerpt).

## Blender integration

The current Blender bridge already has the right primitives for low-token operation: exact `expected_revision`, idempotent `request_id`, durable jobs, preview pixel receipts, cancellation, restore-as-new-revision, typed edits, and garment audits.

A Blender canonical skill should therefore be a **small typed-operation recipe plus evidence contract**, not free-form Python. On an uncertain response, reuse the same request id; never invent a new mutation merely to see whether the old one worked.

Recommended execution skeleton:

```text
scene_info/head revision
→ skill lookup
→ bounded read probes
→ submit typed edit(expected_revision, stable request_id)
→ poll terminal job state
→ inspect committed revision
→ submit preview/audit when visual or deformation correctness matters
→ verify pixels/hash/scene state
→ otherwise restore previous revision as a new revision
```

## Unity integration

The final evidence path must be the production runtime path:

```text
change/create
→ compile
→ collect compile errors
→ enter Play Mode
→ interact / advance deterministic journey
→ capture runtime screenshot/frames/logs
→ assert behavior + visual state
→ record package/editor versions
```

Do not promote an editor-only workaround to canonical when the final failure occurs in Play Mode, import, build, or capture.

Initial Unity records in `failure_catalog.jsonl` are deliberately `external_advisory`: they come from a useful external production skill set and must be reproduced locally before automation.

## 2D integration

Use a coarse-to-fine visual compression ladder:

```text
source video/reference
→ low-cost overview/contact sheet
→ select only motion-rich/important windows
→ dense montage for those windows
→ extract motion grammar / key poses
→ deterministic sprite packing + alpha/palette/frame checks
→ engine/import verification
```

Do not analyze a full video at maximum temporal density from frame zero. Spend visual tokens only where the overview says motion changes.

## Model escalation policy

```text
canonical fingerprint + deterministic recipe  → script/tool path first
known skill but ambiguous parameters          → normal reasoning worker
new failure or cross-system conflict           → architecture/root-cause worker
visual/spatial disagreement after evidence     → strongest visual reviewer
```

The point is not to use weaker models everywhere. The point is to stop paying frontier-model tokens for questions the pipeline already answered yesterday.

## Current observed blocker

On 2026-09-12 the connected local Blender bridge health probe returned an MCP SSE HTTP 429 from the tunnel/gateway. No scene mutation was attempted. The catalog keeps this as `candidate` until bounded recovery is actually verified.

## Absorption decision for pencil-creator

**ADAPT, not clone.** Keep the transferable production ideas:

- skill source-of-truth + deterministic scripts;
- progressive visual compression for video/motion;
- explicit environment-specific trap notes;
- install/load/use/unload lifecycle knowledge for heavy 3D models;
- knowledge → evaluator/agent → workflow/engine self-improvement loop;
- decision logs so the same technology/failure is not re-evaluated from zero.

Reject direct transplantation of project-specific Pencil/WPF/UI context or hardware-specific assumptions into canonical Blender/Unity behavior.
