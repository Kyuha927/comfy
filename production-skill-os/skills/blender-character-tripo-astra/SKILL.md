---
name: blender-character-tripo-astra
description: Fail-closed, evidence-gated LIN character route using H3.1 component generation, supervised Astra Computer Use, Sol Pro analysis/specification, and deterministic Blender verification.
---

# Blender Character Route — R04 H3.1 Components → Supervised Assembly → Deterministic Proof

## 0. Authority reload and capability authorization

This skill is subordinate to the current LIN ASTER 3D SSOT. At start and before any
completion, production-readiness, merge, or canon statement, reload:

- `Kyuha927/lastline-echoes@lin-aster-tripo-r01-20260913`
- current reconciled authority head: `e1b02b1773366677a543d764bd68638e13da1a27`
- SSOT blob: `612fd6347f7d203f9b6d8a3737a72bbaf7a6f0fe`
- live-state blob: `f44c283bd5c02a1a8e8b3adf7785c867d78b0c2f`
- production policy: `LIN_ASTER_3D_PRODUCTION_CONTROL_V1_2`

A newer branch head supersedes these pins and must be reconciled before execution.

Before selecting any tool capability, invoke:

```bash
python production-skill-os/adapters/authorize_capability.py   --capability-id <ID>   --version <EXACT_VERSION_OR_COMMIT>   --scope <GENERIC_PRODUCTION|LIN_3D_VALIDATION|LIN_3D_FINAL>   --lin-authority-head <CURRENT_LIN_HEAD>
```

`LIN_3D_FINAL` accepts only `VERIFIED_FOR_LIN_3D`. `LIN_3D_VALIDATION` additionally
requires `--isolated-workspace --no-production-mutation --no-canon-mutation`.
A denied request is a hard stop for that capability/scope, not permission to use an
unregistered substitute.

At this candidate revision, `VERIFIED_FOR_LIN_3D=0`. Therefore no external tool
capability is yet authorized for the final LIN path; validation remains isolated.

## 1. Corrected R04 route

The current route is maximum-quality component generation, not P2 full-body hero-base generation:

```text
LOCKED FOUR-VIEW CANON
→ LINEAGE-TRACKED NON-CANON DERIVED WORKING REFERENCES
→ H3.1 ULTRA HEAD / FACE / NECK
→ H3.1 ULTRA HAIR / BRAID / SILHOUETTE
→ H3.1 ULTRA BODY / OUTFIT
→ H3.1 ULTRA COAT / MAJOR GARMENT
→ NECESSARY ACCESSORY DONORS ONLY
→ PART-SPECIFIC QA AND SELECTION
→ RAW EXPORT + HASH / JOB / SETTINGS PRESERVATION
→ PRIVATE BLENDER ASSEMBLY
→ CONTROLLED OR MANUAL RETOPOLOGY / RECONSTRUCTION
→ RIG / DEFORMATION / MATERIAL / RUNTIME EVIDENCE
→ USER REVIEW
```

Hard invariants:

```text
P2_FULL_BODY_PRIMARY_HERO_BASE=false
R03_A=HOLD_NOT_PRODUCTION_BASE
R03_B=LIN_R03_DETAIL_DONOR_PROVISIONAL
TRIPO_BASE_READY=false
TEXTURE_BEFORE_GEOMETRY_ACCEPTANCE=false
AUTO_CANON_PROMOTION=false
FINAL_LOCK_AUTHORITY=USER_ONLY
```

Do not restore the superseded `P2 full-body Native Quad = preferred hero base` rule.
R03 A is topology-scaffold evidence only. R03 B is a whole-character detail donor only.

## 2. Reference and generation contract

The locked front/back/left/right canon remains immutable. A derived working reference may
be created only when explicitly authorized, lineage-tracked to the exact canon hash, and
clearly marked non-canon. Character/Asset Extraction, Head Extraction, hair isolation,
garment isolation, and 3D Enhance may be validated as provider capabilities; none may
silently change identity, proportion, construction, braid, asymmetry, or accessories.

For each H3.1 component capability, request `LIN_3D_VALIDATION` before any test. Record:

- exact provider model/version; H3.1 snapshot `v3.1-20260211` or a separately verified successor;
- input hashes and derived-reference lineage;
- live displayed cost and cumulative credit use;
- geometry settings, privacy, job ID, output hash, export identity, and rejected candidates;
- the exact decision this paid result is intended to change.

R04 geometry selection defaults:

```text
GEOMETRY_QUALITY=ULTRA_DETAILED
TEXTURE=OFF
PBR=OFF
QUAD=OFF
SMART_LOW_POLY=OFF
GENERATE_IN_PARTS=OFF_FOR_ALREADY_ISOLATED_HERO_PARTS
AUTO_RIG=OFF
ORIENTATION=DEFAULT
UV_EXPORT=OFF_WHEN_INDEPENDENTLY_CONTROLLABLE
FACE_LIMIT=ADAPTIVE_OR_UNSET
PRIVACY=PRIVATE
```

Two million faces is a ceiling, not an acceptance criterion. Use multiview only when
reliable, mutually consistent directional references actually exist. Do not fabricate a
missing part view. A single-view hair result is provisional. If the same structural failure
repeats twice with the same reference strategy, redesign the reference rather than buying a
third stochastic retry.

## 3. Geometry-before-texture gates

Do not texture, rig, or promote rejected geometry. Inspect the actual exported asset, not
only a provider thumbnail or success receipt.

Head gate: identity, recessed orbital structure, independently addressable eyes and
pupils/irises, usable eyelids/mouth/jaw/ears/neck opening, no duplicate/fused face shell.

Hair gate: front/left/right/back silhouette when reliable views exist, braid and mass
continuity, no fused ears/collar/neck, no helmet shell, floating masses, or invented rear.

Body/outfit and coat gates: exactly two arms, intact hands/feet, readable garment layers,
openings and asymmetry, separable accessories/material families, no flat image shell,
duplicate limb, hidden missing anatomy, or impossible intersections.

Common gate: object separation, dimensions, axes, transforms, normals, manifold/duplicate
findings, UV/material slots, texture paths, front/back/side/three-quarter pixels, and a
ranked defect list.

## 4. Execution roles

- **GPT-6 Astra XHigh / Computer Use:** visual-spatial supervised assembly and high-consequence artistic judgment.
- **GPT-5.6 Sol Pro:** candidate pre-screen, evidence packet, topology/face/hair/garment/rig/material/mobile analysis, executable specification, and delta QA.
- **Blender Bridge/MCP:** exact state-critical operations, typed inspection/editing, durable jobs, rendered evidence, checkpoint/revision, retry/discard, save/reopen, rollback/restore, and receipts.
- **Reviewed bpy/headless Blender:** bounded deterministic inspection, conversion, batch render, bake, export, and reproducible validation only after capability authorization.
- **Recorded human correction:** bounded placement/cleanup when faster or safer, with before/after identity and independent verification.
- **USER:** final approval and lock.

Do not ask Astra to zero-base model the character when an authorized Tripo route exists.
Do not make Bridge/MCP the default creative GUI operator. Do not encode the split as a fixed
percentage. No silent model, provider, tool, version, profile, or route fallback is allowed.

## 5. Supervised Blender loop

Never run a one-shot unattended character build. Use:

```text
act
→ inspect real geometry or pixels
→ compare with current approved authority
→ record the smallest visible defect
→ issue one bounded correction
→ verify again
```

Preserve head, hair, body, coat, and accessories as separately selectable components until
there is evidence for a reversible join. Do not force destructive neck welding. First align
scale, rotation, centerline, openings, normals, shading, and materials. `SEPARATE_ALIGNED`
may pass when fixed cameras and deformation show no functional defect. If joining is needed,
duplicate, checkpoint, inspect loops, use a reviewed reversible operation, and preserve rollback.

Do not force shape keys without proven topology correspondence. Explicit discrete
expression-head mesh/state switching is the stable fallback. Any rigging, secondary-motion,
retopology, or export helper must declare exact name, version/commit, configuration, artifact
hash, license, availability, failure behavior, and rollback.

## 6. Final-path evidence

A capability cannot become `VERIFIED_FOR_LIN_3D` from documentation, repository tests,
isolated smoke, API success, provider success, or CI alone. It requires L8 evidence through
the same LIN execution path and environment, including actual artifact IDs, fixed-condition
pixels/state, regression PASS, failure recovery, and rollback proof.

A final LIN assembly requires, at minimum:

- current authority SHA and exact canon hashes;
- component/reference lineage and provider receipts;
- requested and actual model/tool routes;
- raw exports, Blender version, source/scene hashes, object inventory, revisions;
- front/back/left/right, three-quarter, face, hair, garment, and relevant deformation pixels;
- topology, UV, material, rig, expression, collision, clipping, and performance findings for the current gate;
- checkpoint, fresh-process save/reopen, and rollback/restore proof;
- no unresolved regression in unrelated accepted components;
- explicit `READY_FOR_USER_REVIEW`, never automatic canon/final lock.

A green CI run verifies the guard implementation, not 3D quality. User approval remains a
separate final gate.
