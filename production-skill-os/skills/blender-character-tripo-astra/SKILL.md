---
name: blender-character-tripo-astra
description: Default evidence-gated 2D-to-3D character route using Tripo first, GPT-6 Astra Computer Use for supervised Blender assembly, and Blender Bridge/MCP for deterministic inspection, exact operations, verification, rollback, and receipts.
---

# Blender Character Route: Tripo -> Astra Computer Use -> Bridge Verify

## Authority and status

This is the user-directed default candidate route for new editable character builds. It changes control-plane priority, but it does not claim that every Tripo generation or Astra action is automatically correct. Performance claims and reusable failure repairs still require the Production Skill OS evidence gates.

Project-specific canon and image-edit restrictions take precedence over generic reference preparation. Tripo-first does not authorize cropping, redrawing, inpainting, synthetic multiview completion, or replacing a locked master.

Do not encode this policy as a fixed percentage such as "Computer Use 99%." Route by operation type and evidence:

- Computer Use primary for visual, spatial, interactive, supervised Blender work.
- Bridge/MCP primary for deterministic, repeated, state-sensitive, auditable, recoverable operations.
- Headless or scripted workers only for bounded, deterministic, non-visual work.
- A human manual Blender intervention is valid when faster or safer, but it must be recorded and verified through the same evidence gates.

## Hard routing rules

1. Do not ask GPT-6 Astra to create the character mesh from zero when a usable Tripo path exists.
2. Resolve the current approved reference authority, exact hashes, and image-edit policy before preparing inputs.
3. Use `DEDICATED_PART_REFERENCES` when complete approved `HEAD`, `HAIR`, and `BODY_CLOTHING` packets exist or an exact derivative operation is explicitly authorized.
4. Use `FULL_BODY_MULTIVIEW_PART_AWARE` when locked masters may not be edited or complete part packets are missing. Generate a full-body Tripo candidate, then use Tripo Generate in Parts or copied-candidate 3D segmentation without changing source-image bytes.
5. Hair requires multiview input for a dedicated production candidate. The minimum production packet is front, left, right, and back. A single-view hair result is provisional and must not enter the accepted master.
6. Head and body may use a front view for an initial technical candidate, but they remain provisional until the available authoritative multiview evidence is checked.
7. GPT-6 Astra Computer Use is the primary interactive Blender path for visual placement, scale, orientation, part assembly, supervised rig setup, secondary-motion setup, and viewport-based correction.
8. Blender Bridge/MCP is the deterministic state-critical plane for scene inspection, exact transforms, typed edits, checkpointing, durable jobs, rendered-pixel evidence, audits, rollback, recovery, and receipts.
9. Do not silently switch back to MCP-primary creative interaction, Astra zero-base modeling, a different 3D provider, or a weaker model route. Record the blocker or explicit override.
10. Do not run this as one unattended prompt. Use a supervised stage loop with visible checkpoints and bounded correction turns.
11. Do not assume one fixed flow fits every character. Perform and record a character-specific preflight before generation.
12. Do not force shape keys before topology correspondence is proven. The first stable route may use discrete expression-head mesh/state switching.
13. Do not force destructive head-body welding merely to hide a neck seam. Separate meshes may pass when alignment, shading, deformation, and target-camera evidence pass.
14. Any custom app, add-on, script, or helper used for rigging or secondary motion is a declared dependency, not invisible infrastructure.
15. User approval is required before canon or final-lock promotion.

## Character-specific preflight

Before spending provider quota or Astra tokens, create a route-decision record containing:

- authoritative reference set and hashes;
- image-edit permissions and locked-source restrictions;
- availability and completeness of `HEAD`, `HAIR`, and `BODY_CLOTHING` packets;
- full-body front, left, right, and back coverage;
- hair silhouette complexity and unseen-side risk;
- garment layers, accessories, occlusion, and likely segmentation boundaries;
- target polygon budget and expected rig/deformation needs;
- required expression set and whether discrete mesh switching is acceptable;
- secondary-motion requirements;
- available Computer Use, Bridge, Blender, Tripo, and human-manual lanes;
- declared helper applications or add-ons;
- chosen route mode, rejected alternatives, blockers, and next gate.

The flow may change per character, but the control order must not silently invert. Character variation is handled by an explicit route decision, not by improvising a zero-base Astra fallback.

## Reference preparation

- Resolve the current approved character masters and exact hashes before processing.
- Preserve the approved face, palette, silhouette, age, costume construction, and material hierarchy.
- Do not crop, mask, redraw, retouch, recolor, inpaint, or otherwise edit a locked source unless the exact task explicitly authorizes that derivative operation.
- Record the selected route mode as `DEDICATED_PART_REFERENCES` or `FULL_BODY_MULTIVIEW_PART_AWARE`.
- For a dedicated route, keep head, hair, and body/clothing packets independently versioned and record whether each input is authoritative, approved-derived, provisional, or missing.
- For a full-body route, preserve exact source hashes and isolate parts only in generated 3D space through Generate in Parts or copied-candidate segmentation.
- Do not generate substitute concept art merely to fill a missing view unless the current task explicitly authorizes image generation.

## Tripo generation contract

Keep provider job IDs, model/version, input hashes, output hashes, topology mode, polygon budget, texture state, segmentation strategy, licensing/export metadata, rejected-candidate reasons, and quota use in the receipt.

### Candidate-selection and texture gate

Treat texture generation as a post-geometry acceptance transition, not as a harmless preview step.

1. Generate or regenerate candidates while geometry remains rejectable and replacement is still cheap.
2. Inspect the actual exported mesh, not only provider thumbnails.
3. Reject failed candidates before texture generation when possible.
4. Do not texture a weak head, hair, or body merely to make it look more finished.
5. Record whether the exact Tripo version disables, limits, or complicates regeneration after texturing.
6. Preserve rejected Tripo job IDs and concise rejection reasons so the same failure is not repeatedly purchased.
7. Cross the texture gate only after the relevant head, hair, body/clothing, and common geometry checks pass or an explicit provisional exception is recorded.

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
-> character-specific preflight and route decision
-> select DEDICATED_PART_REFERENCES or FULL_BODY_MULTIVIEW_PART_AWARE
-> Tripo generation and candidate-selection loop
-> geometry gate before texture commitment
-> Generate in Parts or copied-candidate 3D segmentation when needed
-> import into a private Blender candidate
-> GPT-6 Astra Computer Use assembly and visual correction
-> optional recorded human manual correction when faster or safer
-> Bridge/MCP scene inspection and exact-state verification
-> supervised rig, skin, and secondary-motion setup
-> deformation and expression checks
-> fixed-camera renders
-> checkpoint, fresh-process save/reopen, and rollback proof
```

During assembly, Astra may visually align and resize parts, inspect the viewport, correct obvious intersections, and supervise rigging. Exact repeated transforms or state-sensitive mutations should be delegated to deterministic Blender operations or the Bridge after Astra defines the intended result.

A skilled human may perform simple placement, scale, orientation, or cleanup directly when this saves time or tokens. The manual step must identify the edited objects, before/after revisions, and verification evidence. Manual work does not waive checkpoint, render, reopen, or rollback requirements.

Astra must not claim success from prose or a tool receipt. It must inspect actual viewport or render evidence at each major gate.

### Neck seam policy

Do not force destructive neck welding as the default.

- First align head and body scale, rotation, centerline, neck opening, materials, normals, and shading.
- Separate head and body meshes may pass when the seam is visually unobtrusive in required cameras and deformation tests do not expose a functional defect.
- If joining is required, duplicate the candidate first, preserve a rollback point, inspect both border loops, and use a reversible, testable bridge or equivalent operation.
- Reject a join that damages identity, topology, weights, UVs, normals, materials, expression switching, or save/reopen stability.
- Record whether the accepted result is `SEPARATE_ALIGNED`, `JOINED_LOOP_BRIDGE`, or another explicitly justified strategy.

## Expression strategy

For the first stable production route, do not force shape keys when topology or automation is unreliable.

1. Generate or prepare discrete expression head meshes for the required expression set when authorized source and topology permit it.
2. Use explicit mesh/state switching for the initial validated implementation.
3. Keep neutral identity, scale, origin, neck alignment, eye placement, and material assignments invariant across expression heads.
4. Verify every expression in fixed cameras, after save/reopen, and after rig or animation changes.
5. Promote to shape keys or a facial rig only after stable topology, correspondence, interpolation, save/reopen, and regression evidence are proven.

This is a fallback-safe production choice, not a permanent ban on shape keys. Do not create new 2D expression references without explicit authorization.

## Rigging and secondary-motion contract

Astra Computer Use may own the supervised first pass for armature setup, parenting, weight setup, cloth/hair/accessory bones, constraints, and secondary-motion configuration when the imported structure is suitable.

Acceptance still requires:

- named armature and bone inventory;
- object-parent and modifier audit;
- neutral pose plus representative extreme-pose deformation checks;
- collision and clipping checks for hair, scarf, mantle, skirt, sleeves, and accessories as applicable;
- fixed-camera rendered evidence;
- save/reopen proof;
- rollback proof;
- exact known limitations.

If a custom application, Blender add-on, helper script, or generated rig template is used, record its name, version, configuration, artifact hash or commit, license, and availability. Do not claim the setup is reproducible without that dependency. If the dependency is absent, return an exact blocker or use a separately validated standard Blender path. Never conceal the substitution.

## Model and tool responsibility

- **GPT-6 Astra XHigh:** major visual decisions, difficult Computer Use assembly, head and whole-character integration, milestone review.
- **GPT-6 Astra High:** ordinary supervised Computer Use assembly when explicitly routed and recorded.
- **GPT-5.6 Sol High:** hard rigging, skinning, deformation, and cross-module Blender engineering failures.
- **Gemini Flash workers or deterministic scripts:** bounded preprocessing when authorized, hashes, manifests, simple validation, headless batch checks, and repetitive non-visual operations.
- **Blender Bridge/MCP:** deterministic inspection, exact edits, transaction safety, pixel/state evidence, cancellation, checkpointing, and restore.
- **Human manual Blender operation:** bounded placement or repair when faster or safer, with exact receipt and independent verification.

The exact requested and actual model, profile, effort, tools, and helper dependencies must be recorded. No silent fallback is allowed.

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

Do not interpret a single successful prompt, provider job, API response, or tool receipt as completion. After two identical failures with the same input, operation, and error fingerprint, park that route until the input, environment, or diagnosis changes. Continue an independent component rather than burning the same quota repeatedly.

When a correction succeeds, capture the minimal reusable instruction, exact scope, prerequisites, and evidence so Production Skill OS can later evaluate it for candidate-to-canonical promotion. One successful character does not automatically generalize to every design.

## Merge-omission guards

A consumer or merge candidate is incomplete if it drops any of these behaviors:

- Tripo-first when an authorized usable Tripo route exists;
- no Astra zero-base character mesh fallback;
- source-gated dedicated-part versus full-body-part-aware routing;
- four-view dedicated production hair requirement;
- head 2,000 to 5,000 polygon soft start, recessed orbital structure, and independently addressable eyes/pupils;
- geometry acceptance before texture commitment;
- supervised, non-one-shot Computer Use assembly;
- Bridge/MCP deterministic and state-critical responsibilities;
- character-specific preflight and route decision;
- non-destructive neck-seam policy;
- discrete expression-head mesh/state switching as the stable fallback;
- declared helper-app/add-on dependencies;
- checkpoint, fixed-camera pixels, fresh-process reopen, rollback, and user-review separation.

Regression tests must assert these contracts as behavior or explicit policy text. A green suite that does not cover them is not sufficient evidence of successful reconciliation.

## Acceptance evidence

A character assembly cannot pass without:

- exact approved reference hashes and the applicable image-edit policy;
- character-specific preflight and selected route mode with reason;
- dedicated part-input hashes or exact full-body multiview hashes;
- Tripo model/version/job, rejected-candidate, texture-state, and export receipts;
- Generate in Parts or segmentation receipts when used;
- geometry-gate results for logical head, hair, body/clothing, and accessories;
- actual requested and used model route plus Computer Use availability;
- declared custom app/add-on/script dependencies with exact versions and hashes;
- Blender version, source file hash, object inventory, dimensions, and revision/checkpoint IDs;
- neck strategy and evidence;
- fixed-condition front, three-quarter, side, and back renders;
- rig/deformation and secondary-motion checks where applicable;
- expression-switch or facial-rig evidence;
- fresh-process save/reopen;
- rollback proof;
- visible defect list;
- user-review status, never automatic final approval.

If Tripo, Computer Use, authoritative references, required hair views, or declared helper dependencies are unavailable, return the exact blocker and continue only independent work. Do not conceal the missing lane by reverting to zero-base Astra modeling, silently changing provider/model, editing locked references without authority, or making Bridge/MCP the creative GUI operator.
