# Production Skill OS — 2D × Blender × Unity

Purpose: turn repeated production failures into compact, evidence-gated skills so later runs spend tokens on novelty, not rediscovering known traps.

This is a **cross-cutting substrate**, not a new orchestration lane. It is intended to be consumed by the existing Blender Bridge, Unity Agent, Game Development Core, visual-production, and tech-intake lanes.

## Non-negotiable rule

**Failure → bounded diagnosis → verified repair → same-path regression proof → skill promotion.**

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
├── adapters/
│   └── route_packet.py
├── docs/
│   └── CONSUMER_INTEGRATION.md
├── router/
│   ├── skill_router.py
│   ├── promotion_engine.py
│   ├── evidence_event.schema.json
│   └── failure_catalog.jsonl
├── skills/
│   ├── 2d-motion-compression/SKILL.md
│   ├── blender-transactional-verify/SKILL.md
│   ├── unity-playmode-verify/SKILL.md
│   └── failure-to-skill-promotion/SKILL.md
└── tests/
    ├── test_skill_router.py
    ├── test_promotion_engine.py
    └── test_route_packet.py
```

## Low-token event contract

Consumers should emit one small failure event instead of forwarding a full transcript/log bundle:

```json
{
  "domain": "blender_bridge",
  "error_code": "HTTP_429",
  "message": "MCP SSE probe returned 429",
  "environment": "blender-pro-bridge-local",
  "execution_path": "webgpt->bridge->blender"
}
```

Then call:

```bash
python production-skill-os/adapters/route_packet.py --event failure.json
```

A known canonical match returns only its bounded diagnosis, repair, verification, rollback, and scope. A novel failure returns a compact novelty packet for escalation.

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

The router also rejects duplicate active fingerprints. A canonical record is invalid unless it contains an explicit non-empty `scope`.

## Promotion states

| State | Meaning | Automatic repair? |
|---|---|---:|
| `external_advisory` | useful elsewhere, not reproduced here | No |
| `candidate` | observed locally, repair not yet proven enough | No |
| `canonical` | local reproduction + repair + same-path regression evidence | Yes, only within its scope |
| `deprecated` | superseded or invalidated | No |

## Mechanical promotion gate

Promotion is no longer a prose-only judgment. Record evidence events for exactly six gates:

1. `reproduction`
2. `repair`
3. `same_path_verification`
4. `rollback`
5. `regression`
6. `receipt`

Each event needs `environment`, `execution_path`, `observed_at`, and a non-empty receipt. The latest event for every gate must be PASS, and all PASS gates must share one environment and one execution path.

```bash
python production-skill-os/router/promotion_engine.py validate --evidence evidence.jsonl
python production-skill-os/router/promotion_engine.py assess \
  --evidence evidence.jsonl \
  --record-id UNITY_EXAMPLE
```

The promotion engine returns a deterministic proposal plus evidence SHA-256. It **never modifies the catalog**. This prevents a noisy successful run from silently teaching the system a permanent workaround.

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

Receipts should prefer revision numbers, durable job IDs, preview SHA-256 values, audit receipts, exact error codes, and restore revisions.

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
canonical fingerprint + in-scope deterministic recipe → script/tool path first
known skill but ambiguous parameters                  → normal reasoning worker
new failure or cross-system conflict                  → architecture/root-cause worker
visual/spatial disagreement after evidence            → strongest visual reviewer
```

The point is not to use weaker models everywhere. The point is to stop paying frontier-model tokens for questions the pipeline already answered yesterday.

## Tests

The core uses only the Python standard library.

```bash
python -m unittest discover -s production-skill-os/tests -v
```

Current local validation for this revision: **15 tests PASS**, covering catalog validation, advisory isolation, exact-code routing, duplicate IDs/fingerprints, canonical scope, six-gate promotion, latest-failure precedence, path/environment mismatch rejection, and compact consumer packets.

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
