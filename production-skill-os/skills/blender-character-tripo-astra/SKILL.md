---
name: blender-character-tripo-astra
description: Default evidence-gated 2D-to-3D character route using Tripo part generation, GPT-6 Astra Computer Use for supervised Blender assembly, and the Blender Bridge/MCP only for deterministic inspection, exact operations, verification, rollback, and receipts.
---

# Blender Character Route: Tripo -> Astra Computer Use -> Bridge Verify

## Authority and status

This is the user-directed default route for new editable character builds. It changes control-plane priority, but it does not claim that every Tripo generation or Astra action is automatically correct. Performance claims and reusable failure repairs still require the Production Skill OS evidence gates.

## Hard routing rules

1. Do not ask GPT-6 Astra to create the character mesh from zero when a usable Tripo path exists.
2. Split the approved reference packet into at least `HEAD`, `HAIR`, and `BODY_CLOTHING` inputs before 3D generation.
3. Generate those parts with Tripo Smart Mesh P2.0, or a later locally validated equivalent, before Blender assembly.
4. Hair requires multiview input. The minimum production packet is front, left, right, and back. A single-view hair result is provisional and must not enter the accepted master.
5. Head and body may use a front view for an initial candidate, but multiview is preferred whenever authoritative side/back references exist.
6. GPT-6 Astra Computer Use is the primary interactive Blender path for visual placement, scale, orientation, part assembly, supervised rig setup, secondary-motion setup, and viewport-based correction.
7. The Blender Bridge/MCP is the secondary deterministic plane for scene inspection, exact transforms, typed edits, checkpointing, durable jobs, rendered-pixel evidence, audits, rollback, and receipts.
8. Do not silently switch back to MCP-primary interaction, Astra zero-base modeling, a different 3D provider, or a weaker model route. Record the blocker or explicit override.
9. Do not run this as one unattended prompt. Use a supervised stage loop with visible checkpoints and correction turns.
10. User approval is required before canon or final-lock promotion.

## Reference preparation

- Resolve the current approved character masters and exact hashes before processing.
- Preserve the approved face, palette, silhouette, age, costume construction, and material hierarchy.
- Crop or derive private part references without replacing the locked source.
- Keep head, hair, and body/clothing packets independently versioned.
- Record whether each input is authoritative, derived, provisional, or missing.
- Do not generate substitute concept art merely to fill a missing view unless the current task explicitly authorizes image generation.

## Tripo generation contract

Generate `HEAD`, `HAIR`, and `BODY_CLOTHING` as separate assets. Keep provider job IDs, model/version, input hashes, output hashes, topology mode, polygon budget, texture state, and licensing/export metadata in the receipt.

### Head gate

- Soft starting target: approximately 2000-5000 polygons so downstream interactive work remains tractable.
- The eye sockets must read as actual recessed orbital structure, not painted flat eye regions.
- Eyeballs and pupils/irises must be independently addressable objects or cleanly separable geometry.
- The mouth, jaw, eyelids, ears, and neck opening must be usable for later rigging or replacement.
- Reject collapsed facial planes, fused eyes, duplicate facial shells, or identity loss.

### Hair gate

- Front, left, right, and back views are required for the production candidate.
- The side and back silhouette must agree with the approved design.
- Reject fused ears, fused collar/neck, floating hairpin attachments, helmet-shell volume, or major unseen-side invention.
- Preserve separate logical masses when this improves rigging and secondary motion.

### Body and clothing gate

- Arms, hands, legs, coat openings, mantle, scarf, and major props must be visually separable.
- Reject fused limbs, hidden missing anatomy, impossible garment intersections, or flat-image shells.
- Preserve practical attachment logic and distinct material families.

### Common geometry gate

Before master adoption, verify object separation, scale, axes, transforms, normals, non-manifold/duplicate geometry, UV/material slots, texture paths, bounding dimensions, and a neutral front/side/back preview. A provider success receipt is not acceptance.

## Blender assembly contract

The primary interactive sequence is:

```text
approved reference packet
-> split HEAD / HAIR / BODY_CLOTHING
-> Tripo part generation
-> geometry gate
-> import into a private Blender candidate
-> GPT-6 Astra Computer Use assembly and visual correction
-> Bridge/MCP scene inspection and exact-state verification
-> supervised rig / skin / secondary-motion setup
-> deformation and expression checks
-> fixed-camera renders
-> checkpoint, fresh-process reopen, and rollback proof
```

During assembly, Astra may visually align and resize parts, inspect the viewport, correct obvious intersections, and supervise rigging. Exact repeated transforms or state-sensitive mutations should be delegated to deterministic Blender operations or the Bridge after Astra defines the intended result.

Astra must not claim success from prose or a tool receipt. It must inspect actual viewport/render evidence at each major gate.

## Expression strategy

For the first stable production route, do not force shape keys when topology or automation is unreliable.

1. Generate or prepare discrete expression head meshes for the required expression set.
2. Use explicit mesh/state switching for the initial validated implementation.
3. Keep neutral identity and alignment invariant across expression heads.
4. Promote to shape keys or a facial rig only after stable topology, correspondence, interpolation, save/reopen, and regression evidence are proven.

This is a fallback-safe production choice, not a permanent ban on shape keys.

## Model and tool responsibility

- **GPT-6 Astra XHigh:** major visual decisions, difficult Computer Use assembly, head/whole-character integration, milestone review.
- **GPT-6 Astra High:** ordinary supervised Computer Use assembly when explicitly routed and recorded.
- **GPT-5.6 Sol High:** hard rigging, skinning, deformation, and cross-module Blender engineering failures.
- **Gemini Flash workers or deterministic scripts:** bounded preprocessing, hashes, manifests, simple validation, headless batch checks, and repetitive non-visual operations.
- **Blender Bridge/MCP:** deterministic inspection, exact edits, transaction safety, pixel/state evidence, cancellation, checkpointing, and restore.

The exact requested and actual model/profile/effort must be recorded. No silent fallback is allowed.

## Bridge boundary

Use the Bridge/MCP for:

- `bridge_health`, scene and object inventory;
- exact revision and stable request ID;
- typed transforms and bounded property edits;
- durable job submission and terminal-state polling;
- preview/render hash and garment/deformation audits;
- save/checkpoint and restore-as-new-revision;
- exact error codes and compact receipts.

Do not make Bridge/MCP the default interactive operator for the full creative assembly loop. Do not expose arbitrary remote Python merely to imitate Computer Use.

## Supervision loop

At every stage:

```text
act
-> inspect real geometry or pixels
-> compare against the current approved reference
-> record the smallest visible defect
-> issue one bounded correction
-> verify again
```

After two identical failures with the same input, operation, and error fingerprint, park that route until the input, environment, or diagnosis changes. Continue an independent part rather than burning the same quota repeatedly.

## Acceptance evidence

A character assembly cannot pass without:

- exact reference and part hashes;
- Tripo model/version/job and exported-part receipts;
- geometry-gate results for head, hair, and body/clothing;
- actual requested/used model route and Computer Use availability;
- Blender version, source file hash, object inventory, dimensions, and revision/checkpoint IDs;
- fixed-condition front, three-quarter, side, and back renders;
- rig/deformation checks where applicable;
- expression-switch or facial-rig evidence;
- fresh-process save/reopen;
- rollback proof;
- visible defect list;
- user-review status, never automatic final approval.

If Tripo, Computer Use, the approved references, or required multiview hair inputs are unavailable, return the exact blocker and continue only independent work. Do not conceal the missing lane by reverting to zero-base Astra modeling.