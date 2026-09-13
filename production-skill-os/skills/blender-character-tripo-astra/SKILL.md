---
name: blender-character-tripo-astra
description: Default evidence-gated 2D-to-3D character route using Tripo first, GPT-6 Astra Computer Use for supervised Blender assembly, and Blender Bridge/MCP only for deterministic inspection, exact operations, verification, rollback, and receipts.
---

# Blender Character Route: Tripo -> Astra Computer Use -> Bridge Verify

## Authority and status

This is the user-directed default route for new editable character builds. It changes control-plane priority, but it does not claim that every Tripo generation or Astra action is automatically correct. Performance claims and reusable failure repairs still require the Production Skill OS evidence gates.

Project-specific canon and image-edit restrictions take precedence over generic reference preparation. Tripo-first does not authorize cropping, redrawing, inpainting, synthetic multiview completion, or replacing a locked master.

## Hard routing rules

1. Do not ask GPT-6 Astra to create the character mesh from zero when a usable Tripo path exists.
2. Resolve the current approved reference authority, exact hashes, and image-edit policy before preparing inputs.
3. Use `DEDICATED_PART_REFERENCES` when complete approved `HEAD`, `HAIR`, and `BODY_CLOTHING` packets exist or an exact derivative operation is explicitly authorized.
4. Use `FULL_BODY_MULTIVIEW_PART_AWARE` when locked masters may not be edited or complete part packets are missing. Generate a full-body Tripo candidate, then use Tripo Generate in Parts or copied-candidate 3D segmentation without changing source-image bytes.
5. Hair requires multiview input for a dedicated production candidate. The minimum production packet is front, left, right, and back. A single-view hair result is provisional and must not enter the accepted master.
6. Head and body may use a front view for an initial technical candidate, but they remain provisional until the available authoritative multiview evidence is checked.
7. GPT-6 Astra Computer Use is the primary interactive Blender path for visual placement, scale, orientation, part assembly, supervised rig setup, secondary-motion setup, and viewport-based correction.
8. Blender Bridge/MCP is the secondary deterministic plane for scene inspection, exact transforms, typed edits, checkpointing, durable jobs, rendered-pixel evidence, audits, rollback, and receipts.
9. Do not silently switch back to MCP-primary interaction, Astra zero-base modeling, a different 3D provider, or a weaker model route. Record the blocker or explicit override.
10. Do not run this as one unattended prompt. Use a supervised stage loop with visible checkpoints and correction turns.
11. User approval is required before canon or final-lock promotion.

## Reference preparation

- Resolve the current approved character masters and exact hashes before processing.
- Preserve the approved face, palette, silhouette, age, costume construction, and material hierarchy.
- Do not crop, mask, redraw, retouch, recolor, inpaint, or otherwise edit a locked source unless the exact task explicitly authorizes that derivative operation.
- Record the selected route mode as `DEDICATED_PART_REFERENCES` or `FULL_BODY_MULTIVIEW_PART_AWARE`.
- For a dedicated route, keep head, hair, and body/clothing packets independently versioned and record whether each input is authoritative, approved-derived, provisional, or missing.
- For a full-body route, preserve exact source hashes and isolate parts only in generated 3D space through Generate in Parts or copied-candidate segmentation.
- Do not generate substitute concept art merely to fill a missing view unless the current task explicitly authorizes image generation.

## Tripo generation contract

Keep provider job IDs, model/version, input hashes, output hashes, topology mode, polygon budget, texture state, segmentation strategy, and licensing/export metadata in the receipt.

### Route A: `DEDICATED_PART_REFERENCES`

Generate `HEAD`, `HAIR`, and `BODY_CLOTHING` as separate Tripo assets only from complete approved packets. Do not label incomplete crops or a single-view hair input as production-ready part references.

### Route B: `FULL_BODY_MULTIVIEW_PART_AWARE`

Generate a full-body multiview Tripo candidate from the exact approved masters. Prefer Smart Mesh P2.0 for the editable production base when locally available and validated.

Then choose one bounded part-aware path:

1. Tripo Generate in Parts from the same approved multiview inputs; or
2. Segmentation v2 on a copied, geometry-accepted full-body candidate.

Prefer coarse or balanced segmentation before detailed fragmentation. Never segment the only accepted candidate destructively. This route must still produce a clear logical inventory for head, hair, body, clothing, and major accessories before Blender assembly.

### Head gate

- Soft starting target: approximately 2,000 to 5,000 polygons so downstream interactive work remains tractable.
- The eye sockets must read as actual recessed orbital structure, not painted-flat eye regions.
- Eyeballs and pupils/irises must be independently addressable objects or cleanly separable geometry.
- The mouth, jaw, eyelids, ears, and neck opening must be usable for later rigging or replacement.
- Reject collapsed facial planes, fused eyes, duplicate facial shells, or identity loss.
- Do not texture a weak head merely to make regeneration or rejection more expensive.

### Hair gate

- Front, left, right, and back views are required for a dedicated production candidate.
- A single-view hair result is provisional.
- For the full-body route, compare the generated hair mass against every available authoritative view before accepting a segmented hair component.
- Reject fused ears, fused collar/neck, floating attachments, helmet-shell volume, repeated strand noise, or major unseen-side invention.
- Preserve separate logical masses when this improves rigging and secondary motion.

### Body and clothing gate

- Arms, hands, legs, coat openings, mantle, scarf, and major props must be visually separable.
- Verify complete anatomy and exactly two arms even when an orthographic side view visually occludes the far arm.
- Reject fused limbs, duplicate limbs, hidden missing anatomy, impossible garment intersections, or flat-image shells.
- Preserve practical attachment logic and distinct material families.

### Common geometry gate

Before master adoption, verify object separation, scale, axes, transforms, normals, non-manifold or duplicate geometry, UV/material slots, texture paths, bounding dimensions, and neutral front, three-quarter, side, and back previews. A provider success receipt is not acceptance.

## Blender assembly contract

The primary interactive sequence is:

```text
approved reference authority
-> select DEDICATED_PART_REFERENCES or FULL_BODY_MULTIVIEW_PART_AWARE
-> Tripo generation
-> geometry gate
-> Generate in Parts or copied-candidate 3D segmentation when needed
-> import into a private Blender candidate
-> GPT-6 Astra Computer Use assembly and visual correction
-> Bridge/MCP scene inspection and exact-state verification
-> supervised rig, skin, and secondary-motion setup
-> deformation and expression checks
-> fixed-camera renders
-> checkpoint, fresh-process save/reopen, and rollback proof
```

During assembly, Astra may visually align and resize parts, inspect the viewport, correct obvious intersections, and supervise rigging. Exact repeated transforms or state-sensitive mutations should be delegated to deterministic Blender operations or the Bridge after Astra defines the intended result.

Astra must not claim success from prose or a tool receipt. It must inspect actual viewport or render evidence at each major gate.

## Expression strategy

For the first stable production route, do not force shape keys when topology or automation is unreliable.

1. Generate or prepare discrete expression head meshes for the required expression set when authorized source and topology permit it.
2. Use explicit mesh/state switching for the initial validated implementation.
3. Keep neutral identity and alignment invariant across expression heads.
4. Promote to shape keys or a facial rig only after stable topology, correspondence, interpolation, save/reopen, and regression evidence are proven.

This is a fallback-safe production choice, not a permanent ban on shape keys. Do not create new 2D expression references without explicit authorization.

## Model and tool responsibility

- **GPT-6 Astra XHigh:** major visual decisions, difficult Computer Use assembly, head and whole-character integration, milestone review.
- **GPT-6 Astra High:** ordinary supervised Computer Use assembly when explicitly routed and recorded.
- **GPT-5.6 Sol High:** hard rigging, skinning, deformation, and cross-module Blender engineering failures.
- **Gemini Flash workers or deterministic scripts:** bounded preprocessing when authorized, hashes, manifests, simple validation, headless batch checks, and repetitive non-visual operations.
- **Blender Bridge/MCP:** deterministic inspection, exact edits, transaction safety, pixel/state evidence, cancellation, checkpointing, and restore.

The exact requested and actual model, profile, and effort must be recorded. No silent fallback is allowed.

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

After two identical failures with the same input, operation, and error fingerprint, park that route until the input, environment, or diagnosis changes. Continue an independent component rather than burning the same quota repeatedly.

## Acceptance evidence

A character assembly cannot pass without:

- exact approved reference hashes and the applicable image-edit policy;
- selected route mode and reason;
- dedicated part-input hashes or exact full-body multiview hashes;
- Tripo model/version/job and export receipts;
- Generate in Parts or segmentation receipts when used;
- geometry-gate results for logical head, hair, body/clothing, and accessories;
- actual requested and used model route plus Computer Use availability;
- Blender version, source file hash, object inventory, dimensions, and revision/checkpoint IDs;
- fixed-condition front, three-quarter, side, and back renders;
- rig/deformation checks where applicable;
- expression-switch or facial-rig evidence;
- fresh-process save/reopen;
- rollback proof;
- visible defect list;
- user-review status, never automatic final approval.

If Tripo, Computer Use, authoritative references, or required hair views are unavailable, return the exact blocker and continue only independent work. Do not conceal the missing lane by reverting to zero-base Astra modeling or making Bridge/MCP the creative GUI operator.