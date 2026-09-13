# ONE-SHOT HANDOFF — GLOBAL TOOL/CAPABILITY VALIDATION → LIN ASTER FINAL 3D PRODUCTION

## Routing

- **Main model:** GPT-6 Astra
- **Reasoning:** XHigh
- **Primary role:** production-system architect, adoption judge, hostile red-team reviewer
- **GPT-5.6 Sol Pro / High:** evidence synthesis, capability decomposition, executable integration specs, first-pass delta QA
- **GPT-5.6 Terra High:** independent technical/regression verification when available
- **GPT-5.6 Luna Medium:** bounded inventory, source/commit/version/hash bookkeeping when available
- **Deterministic tools/scripts:** exact comparisons, registry validation, CI/regression checks, hashes
- Do not spend Astra on mechanical file listing, log summarization, batch checks, or repetitive edits.
- Preserve the receiving chat's actually available model/tool route in the receipt. No silent fallback.

## Global process authority

Follow:

`https://github.com/Kyuha927/noin-webgpt-system-audit/blob/main/GLOBAL_PROMPT_HANDOFF_POLICY.md`

## Mission

The user has repeatedly reviewed many tools, repositories, systems, plugins, model routes, and production techniques across game development, Blender/3D, Unity/UE, WebGPT, local AI, design, music/video, coding, orchestration, QA, and automation.

The required result is **not another review list**.

Build an evidence-gated global Tool/Capability Intake and Adoption layer that guarantees:

```text
previously reviewed tools + new tools
→ source/version/licensing verification
→ capability-level decomposition
→ isolated testing
→ measurable comparison against current stack
→ failure/recovery/rollback validation
→ representative LIN ASTER 3D SAME-PATH validation when relevant
→ regression protection
→ only then ABSORBED / VERIFIED_FOR_LIN_3D
→ available to the final LIN 3D production pipeline
```

Anything that was merely discussed, reviewed, marketed, or tested outside the relevant path must **not** be treated as adopted.

The job is to recover the user's existing work, stop repeated rediscovery, safely absorb genuinely useful capabilities, and prevent unstable or unverified tooling from entering the final 3D path.

---

# 0. NON-NEGOTIABLE CURRENT LIN 3D AUTHORITY

Before doing anything, read the current LIN ASTER 3D authority:

`https://github.com/Kyuha927/lastline-echoes/blob/lin-aster-tripo-r01-20260913/work/handovers/2026-09-13/00_READ_FIRST_LIN_ASTER_3D_ROUTE.md`

Also read:

`https://github.com/Kyuha927/lastline-echoes/blob/lin-aster-tripo-r01-20260913/work/handovers/2026-09-13/LIN_ASTER_3D_LIVE_STATE.json`

`https://github.com/Kyuha927/lastline-echoes/blob/lin-aster-tripo-r01-20260913/work/handovers/2026-09-13/LIN_ASTER_3D_PRODUCTION_CONTROL_CURRENT.md`

Do not overwrite newer state from an older chat or stale SHA.

Preserve these active facts unless the current SSOT says otherwise:

```text
TRIPO_FIRST=REQUIRED_WHEN_USABLE
TRIPO_OUTPUT=BASE_MESH_DRAFT_OR_DONOR_ONLY
ZERO_BASE_ASTRA_CHARACTER_MODELING=FORBIDDEN
ASTRA_COMPUTER_USE=PRIMARY_VISUAL_INTERACTIVE_ROUTE
BLENDER_BRIDGE_MCP=PRIMARY_STATE_CRITICAL_ROUTE
HEADLESS_SCRIPTED_WORK=BOUNDED_DETERMINISTIC_SCOPE
AUTO_CANON_PROMOTION=false
AUTO_FINAL_LOCK=false
USER_FINAL_APPROVAL_REQUIRED=true
```

Do not change the four locked LIN turnaround masters.
Do not regenerate or edit canonical images.
Do not disturb an active frozen Blender Pro Bridge 0.5.0a2 acceptance workspace.
Do not change Tripo R03 while this audit is running unless a verified blocking incompatibility is proven.

---

# 1. RECOVER ALL PREVIOUS TOOL/STACK WORK FIRST

Do not begin by searching the internet for random new tools.

First recover the user's existing reviewed/tested portfolio from durable evidence.

Mandatory starting source:

`https://github.com/Kyuha927/comfy/tree/work-handoffs-v4-20260912/releases/work-handoffs/2026-09-12-v4`

Read at minimum:

- `WORK_AUDIT_CORRECTED_2026-09-12.md`
- `INDEX.md`
- `WORK_RESULTS_WEBGPT.md` only as historical evidence, with the corrected audit taking precedence
- `01_BLENDER_WEBGPT_BRIDGE_MCP_PLUS.md`
- `02_OPENCODE_WEBGPT_PLUGIN.md`
- `03_UNITY_AGENT_PLUGIN.md`
- `04_GAME_DEVELOPMENT_CORE.md`
- `05_CANONFLOW_PINFRAME_VISUAL_HANDOFF.md`
- `06_LASTLINE_ECHOES_3D_VISUAL.md`
- `07_NOIN_STORY_PRODUCTION.md`
- `08_AI_MUSIC_PIPELINE.md`
- `09_AI_MUSIC_VIDEO.md`
- `10_LIFE_AGENT_OS.md`
- `11_DEEPSEEK_DESIGN_BETA.md`
- `12_ATLAS_DESIGN_ABSORPTION.md`
- `13_LOCAL_AI_TOOLCHAIN.md`
- `14_GAME_TECH_INTAKE.md`
- `15_STORAGE_OFFLOADER_REPAIR.md`
- `16_SUPPORT_FUNDING_POSITIONING.md`
- `17_EMAIL_TRIAGE.md`
- `18_TECH_SCOUTING.md`

The corrected audit explicitly found **0/18 fully product/integration-complete**. Do not erase that boundary.

Also recover later reviewed/scouted tools and systems from GitHub history, linked project repositories, and the current user's durable records. These include, when evidence exists, examples such as:

- GameFactory / game-generation systems;
- NVIDIA NeMo Switchyard or other routing/orchestration systems;
- Microsoft AI Engineering Coach;
- Pencil Creator / 2D and game-production skill sets;
- Oracle / WebGPT review replacement;
- Three.js game skills/toolchains;
- DeepSeek Blender/headless workflows;
- Blender official/community MCP and DCC bridge approaches;
- Tripo DCC Bridge and Tripo character workflows;
- Unity Agent / Unity automation;
- CANONFLOW / PINFRAME;
- OpenCode ↔ WebGPT integration;
- local AI toolchains and open models;
- relevant image/video/music production tools;
- later tech-scouting ACT NOW / TEST / WATCH decisions.

Do not assume this example list is complete. Search durable GitHub evidence for later additions.

---

# 2. CREATE ONE GLOBAL TOOL/CAPABILITY SSOT

Create an isolated candidate branch/workspace. Do not mutate production main or project canon.

Create a durable human-readable registry and a machine-readable registry. Recommended canonical candidate locations inside `Kyuha927/comfy`:

```text
production-skill-os/tool-intake/TOOL_STACK_SSOT.md
production-skill-os/tool-intake/TOOL_CAPABILITY_REGISTRY.json
production-skill-os/tool-intake/README.md
```

If an equivalent current structure already exists, extend it instead of creating a competing registry.

Every tool/system must be decomposed into **capabilities**, not adopted as an indivisible brand.

Example:

```text
TOOL_X
├─ topology repair              VERIFIED_FOR_LIN_3D
├─ auto-rig                     REJECTED
├─ batch render                 ABSORBED_GENERIC
└─ texture generation           WATCH
```

Required capability states:

```text
DISCOVERED
REVIEWED
TEST_REQUIRED
ISOLATED_PASS
ISOLATED_FAIL
WATCH
REJECTED
ABSORBED_GENERIC
LIN_3D_TEST_REQUIRED
VERIFIED_FOR_LIN_3D
SUPERSEDED
BLOCKED
```

Do not use vague states such as `looks good`, `probably useful`, or `applied`.

---

# 3. REQUIRED REGISTRY FIELDS

For each capability record, preserve at minimum:

```text
capability_id
tool_or_system
capability_name
source_type
official_source_urls
repository_url
exact_version_or_commit
license_or_commercial_constraints
reviewed_at
review_evidence
claimed_benefit
current_stack_equivalent
target_subsystem
status
isolated_test_environment
isolated_test_evidence
quality_delta
latency_delta
cost_delta
memory_or_vram_delta
failure_modes
recovery_behavior
rollback_behavior
security_or_privacy_notes
known_incompatibilities
supersedes
superseded_by
lin_3d_relevance
lin_3d_same_path_test
lin_3d_evidence
regression_tests
owner_or_executor
next_gate
last_verified_at
```

Unknown values remain `UNKNOWN` or `NOT_RUN`. Never invent them.

---

# 4. OFFICIAL-SOURCE-FIRST VERIFICATION

The user previously identified insufficient official-source checking as a root cause of wasted work.

For every capability considered for adoption:

1. verify the current official docs/repository/release notes first;
2. pin exact version/commit/model where possible;
3. verify compatibility, limitations, licensing/commercial terms, platform constraints, and deprecations;
4. then use community evidence as secondary support;
5. record source URLs and verification date.

Do not rely on an old chat summary when current official behavior can materially differ.

A capability cannot become `ABSORBED_GENERIC` or `VERIFIED_FOR_LIN_3D` on marketing evidence alone.

---

# 5. EVIDENCE LADDER

A capability must climb this ladder:

```text
L0 DISCUSSED
L1 OFFICIAL_SOURCE_VERIFIED
L2 ISOLATED_REPRODUCIBLE_TEST
L3 CURRENT_STACK_COMPARISON
L4 FAILURE_RECOVERY_ROLLBACK
L5 REPRESENTATIVE_PROJECT_TEST
L6 LIN_3D_SAME_PATH_TEST, if relevant
L7 REGRESSION_GUARDED
L8 ABSORBED / VERIFIED_FOR_LIN_3D
```

No skipping directly from L0/L1 to L8.

For capabilities irrelevant to 3D, stop at a justified generic adoption status. Do not force every tool into LIN.

For capabilities that can affect final LIN 3D quality, correctness, speed, cost, reproducibility, or safety, **L6 is mandatory**.

---

# 6. LIN 3D SAME-PATH VALIDATION GATE

Generic success is not enough.

Before a capability is allowed into final LIN production, verify it on the same or representative production path:

```text
LOCKED LIN authority
→ actual Tripo draft/donor or approved representative equivalent
→ private Blender candidate
→ exact intended operation
→ deterministic scene/evidence capture
→ visual comparison
→ save/checkpoint
→ fresh-process reopen
→ rollback/restore when mutation is involved
→ regression against previously accepted gates
```

Required output state:

`VERIFIED_FOR_LIN_3D`

Anything without this evidence must remain outside the final production route.

Examples:

- a topology tool must prove topology improvement without face/silhouette/deformation regression;
- a hair tool must prove silhouette/identity and runtime cost on LIN-like hair;
- an auto-rig tool must prove representative shoulder/elbow/wrist/hip/knee/neck/face deformation;
- a Blender automation tool must prove correct-scene/revision behavior, save/reopen, rollback, and rendered pixels;
- an LOD tool must prove fixed-camera quality deltas and mobile cost improvements;
- a shader/material tool must prove actual-device benefit if targeted at Mobile Hero;
- an orchestration/routing tool must prove lower failure/rework cost without weakening evidence gates.

---

# 7. PROMOTION RULES

Only promote a capability when all required evidence for its scope passes.

Generic reusable capability:

```text
OFFICIAL_SOURCE_VERIFIED
+ ISOLATED_PASS
+ CURRENT_STACK_COMPARISON_PASS
+ FAILURE/RECOVERY ACCEPTABLE
+ ROLLBACK OR SAFE-NONMUTATING BEHAVIOR
+ REGRESSION_GUARD
= ABSORBED_GENERIC
```

Final LIN 3D capability:

```text
ABSORBED_GENERIC
+ LIN_3D_SAME_PATH_PASS
+ NO_CANON_REGRESSION
+ SAVE/REOPEN WHERE APPLICABLE
+ ROLLBACK/RESTORE WHERE APPLICABLE
+ VISUAL OR TECHNICAL EVIDENCE
= VERIFIED_FOR_LIN_3D
```

User approval is still required before production canon or final-lock promotion.

---

# 8. WIRE THE REGISTRY INTO FINAL 3D PRODUCTION

The end result must not be a passive spreadsheet.

Wire the candidate registry into the active Production Skill OS / LIN 3D route so that external/new capabilities are checked before use.

Required behavior:

```text
requested operation
→ identify candidate capability
→ query capability registry
→ VERIFIED_FOR_LIN_3D ?
   ├─ yes: may be selected under its exact version/constraints
   └─ no: block production use or route to isolated validation
```

For generic deterministic support capabilities that do not affect final 3D state, require the appropriate generic verified state instead.

Add merge-omission/regression guards so future edits cannot silently remove this gate.

Do not hardcode brand preference when a capability contract is the actual requirement.

---

# 9. PRESERVE CURRENT PRODUCTION ROLES

The tool registry augments, not replaces, the active control plane:

```text
Tripo
= draft/donor generation

Sol Pro
= pre-screen, decomposition, evidence packet, executable spec, delta QA

Astra
= high-consequence visual/technical judgment and architecture decisions

Astra Computer Use
= visual/spatial/interactive Blender operation

Bridge/MCP
= state/revision/exact operation/render evidence/checkpoint/rollback/receipt

Headless/scripts
= deterministic inspection, conversion, batch render, bake, export, exact validation

User
= final approval/lock
```

A newly adopted tool must occupy a bounded role inside this architecture, not silently replace the architecture.

---

# 10. DO NOT REPEAT PREVIOUS FAILURE MODES

Explicitly prevent:

- `reviewed = adopted`;
- `GitHub repo exists = production-ready`;
- `CI green = product pass`;
- `provider success = visual acceptance`;
- `pretty render = deformable model pass`;
- `unit test = real Blender/device verification`;
- `newer tool = automatically better`;
- `benchmark claim = our workflow improvement`;
- adopting a whole tool when only one capability is useful;
- replacing a validated path before rollback is proven;
- losing exact tool version/commit;
- repeatedly rediscovering a previously rejected tool without new evidence;
- using an unverified tool in the final LIN 3D path because the current operator finds it convenient.

---

# 11. REQUIRED WORK PRODUCTS

Produce and publish durable GitHub links for:

1. `TOOL_STACK_SSOT.md`
2. `TOOL_CAPABILITY_REGISTRY.json`
3. an audit report mapping the old 18 Work lanes and later tool reviews into capability records;
4. an adoption-gap report showing what was reviewed but never safely absorbed;
5. a `VERIFIED_FOR_LIN_3D` shortlist;
6. a `LIN_3D_TEST_REQUIRED` queue;
7. a `WATCH / REJECTED / SUPERSEDED` list with reasons;
8. Production Skill OS integration/guard changes;
9. regression/CI evidence;
10. a current handoff pointer for new/existing chats.

If code or local execution is unavailable in the current chat, complete all GitHub/public-source reconciliation possible and return an exact blocker only for the remaining local execution. Do not downgrade the mission into a mere plan.

---

# 12. INITIAL PORTFOLIO RECONCILIATION

At minimum, reconcile the corrected 18-lane Work audit before claiming registry completeness.

Known corrected audit boundary:

```text
FULL_PRODUCT_OR_INTEGRATION_COMPLETE = 0 / 18
LIMITED_SUBSCOPE_VERIFIED = 6
PARTIAL_OR_REVIEW_REQUIRED = 10
BLOCKED = 2
```

Preserve those historical decisions until stronger evidence supersedes them.

For Tech Scouting, preserve the policy that only `ACT NOW` findings create implementation work, but re-check whether later tests changed the status.

Do not silently mark the 11 previously classified scouting candidates as adopted merely because they were categorized.

---

# 13. INTEGRATION WITH CURRENT LIN STATE

When the registry and guards are ready, update the current LIN 3D SSOT **only by reconciling the latest SHA first**.

The SSOT should point to the tool/capability registry and state:

- final 3D may use only capability states authorized for its scope;
- unknown/unverified external tools are validation candidates, not production tools;
- actual LIN same-path evidence is required for 3D-affecting capabilities;
- failed/rejected/superseded capabilities cannot silently re-enter;
- user remains final lock authority.

Do not rewrite canonical reference hashes, Tripo R03 identity, or Bridge candidate evidence while adding this pointer.

---

# 14. VALIDATION

Before declaring this task complete:

- verify the registry parses;
- verify unique stable capability IDs;
- verify every `VERIFIED_FOR_LIN_3D` record has actual LIN/representative same-path evidence;
- verify no `REVIEWED` record is accepted as production-ready;
- verify rejected/superseded items are blocked from production selection;
- verify exact version/commit constraints are preserved;
- verify rollback/recovery fields for state-mutating tools;
- verify Production Skill OS selection honors the registry;
- run the complete relevant regression suite;
- inspect CI separately from local/runtime evidence;
- verify current Tripo R03 and Bridge 0.5.0a2 lanes were not mutated;
- verify no production/main/canon merge occurred;
- re-fetch final GitHub files after writing.

A green registry/CI test is not proof that unrun real LIN tests passed.

---

# 15. STOP / BLOCK CODES

Use exact blockers:

```text
BLOCKED_CURRENT_LIN_SSOT_UNAVAILABLE
BLOCKED_STALE_SHA_CONFLICT
BLOCKED_SOURCE_EVIDENCE_MISSING
BLOCKED_OFFICIAL_VERSION_UNVERIFIED
BLOCKED_LICENSE_OR_COMMERCIAL_STATUS
BLOCKED_ISOLATED_TEST_REQUIRED
BLOCKED_CURRENT_STACK_COMPARISON_REQUIRED
BLOCKED_FAILURE_RECOVERY_UNVERIFIED
BLOCKED_ROLLBACK_UNVERIFIED
BLOCKED_LIN_3D_SAME_PATH_TEST_REQUIRED
BLOCKED_LOCAL_EXECUTION_REQUIRED
BLOCKED_REGRESSION_FAILURE
BLOCKED_USER_APPROVAL_REQUIRED
```

A blocker in one capability must not block independent capability reconciliation.

---

# 16. COMPLETION CRITERIA

This handoff is complete only when:

1. prior reviewed/tested tool work is recovered rather than rediscovered;
2. one global capability registry exists;
3. capabilities have evidence-based states;
4. useful capabilities are adopted at capability granularity;
5. final LIN 3D use is gated by verified state;
6. representative LIN same-path validation is mandatory for 3D-affecting capabilities;
7. regression tests prevent bypass;
8. current LIN SSOT points to the gate;
9. exact unresolved items remain TEST_REQUIRED/WATCH/BLOCKED instead of being falsely promoted;
10. no production/canon/final lock occurs automatically.

The desired end state is:

```text
BEST AVAILABLE TOOLING
+ OFFICIAL-SOURCE VERIFICATION
+ REPRODUCIBLE TESTS
+ LIN-SPECIFIC SAME-PATH EVIDENCE
+ ROLLBACK / REGRESSION SAFETY
= ONLY THEN FINAL 3D PRODUCTION USE
```

---

# 17. FINAL RESPONSE FORMAT

Return exactly these sections:

1. `STATUS`
2. `CURRENT_AUTHORITIES_READ`
3. `RECOVERED_TOOL_PORTFOLIO`
4. `GLOBAL_CAPABILITY_REGISTRY`
5. `VERIFIED_FOR_LIN_3D`
6. `LIN_3D_TEST_REQUIRED`
7. `WATCH_REJECTED_SUPERSEDED`
8. `PRODUCTION_SKILL_OS_INTEGRATION`
9. `LIN_SSOT_INTEGRATION`
10. `TESTS_AND_CI`
11. `LOCAL_OR_REAL_3D_EVIDENCE`
12. `FAILURES_OR_BLOCKERS`
13. `NO_REGRESSION_CONFIRMATION`
14. `CANON_MERGE_STATUS`
15. `NEXT_BOUNDED_ACTION`

Never call the task complete if the result is only a review document and the production gate is not actually wired.