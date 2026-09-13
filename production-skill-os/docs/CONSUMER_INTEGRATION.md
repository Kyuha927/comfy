# Consumer integration contract

Production Skill OS is a read-mostly knowledge layer. It must not become a second orchestrator.

## Event in

Emit one compact failure event:

```json
{
  "domain": "blender_bridge",
  "error_code": "HTTP_429",
  "message": "MCP SSE probe returned 429",
  "environment": "blender-pro-bridge-local",
  "execution_path": "webgpt->bridge->blender"
}
```

Run `adapters/route_packet.py`. Canonical matches may be used only inside the record's scope.
Candidate/external matches remain advisory and require diagnosis. Unknown failures escalate.

## Evidence out

After a local reproduction/repair attempt, append evidence events for these gates:

1. `reproduction`
2. `repair`
3. `same_path_verification`
4. `rollback`
5. `regression`
6. `receipt`

Every PASS must carry a non-empty receipt. The promotion engine requires all latest gate states to
PASS in the same environment and execution path. It emits a proposal only; it never edits the catalog.

## Blender binding

Recommended domain: `blender_bridge`.

Receipts should favor durable identifiers already emitted by the bridge: head revision, job id,
preview SHA-256, audit receipt, restore revision, and exact failure code. Never convert a tool-call
receipt into success without terminal job state plus scene/pixel evidence.

## Character 3D binding

For new editable character builds, consumers must load
`skills/blender-character-tripo-astra/SKILL.md` before choosing a Blender control path.

The default production path is:

```text
approved references
-> split HEAD / HAIR / BODY_CLOTHING
-> Tripo Smart Mesh P2.0 part generation
-> per-part geometry gate
-> GPT-6 Astra Computer Use supervised Blender assembly
-> Blender Bridge/MCP deterministic verification and exact edits
-> rig/deformation/expression checks
-> fixed-camera render evidence
-> checkpoint, fresh-process reopen, and rollback proof
```

Use an execution path equivalent to:

```text
reference-split->tripo-p2->astra-computer-use->bridge-verify
```

The routing policy is user-directed and active for new character work. It is not a blanket quality
claim about any provider result. Reusable repair claims still require the six evidence gates.

Mandatory consumer behavior:

- do not route zero-base character modeling to Astra when usable Tripo generation is available;
- require front/left/right/back input for production hair candidates;
- use Astra Computer Use as the primary interactive operator for visual assembly and supervised setup;
- use Bridge/MCP as the secondary deterministic plane for inspection, exact operations, checkpointing,
  rendered-pixel/state verification, rollback, and receipts;
- do not silently revert to MCP-primary interaction, another provider, or a weaker model route;
- do not claim success from provider, model, or API receipts without geometry and pixel evidence;
- require explicit user review before canon or final-lock promotion.

Character-route receipts should include approved reference hashes; derived part-input hashes; Tripo
model/version/job IDs and export hashes; geometry-gate results; requested and actual Astra route and
Computer Use availability; Blender version, object inventory, dimensions, revisions, job IDs, preview
hashes, save/reopen proof, rollback proof, visible defects, and the next bounded correction.

If Tripo, Astra Computer Use, authoritative references, or required hair views are unavailable, report
the exact blocker and continue only independent work. Do not conceal the missing lane by using Astra
for zero-base modeling or by making Bridge/MCP the creative GUI operator.

## Unity binding

Recommended domain: `unity`.

Use one production path string for a gate set, for example:
`agent->unity-editor->compile->playmode->capture`. Receipts should include editor/package versions,
compile result, PlayMode journey id, runtime screenshot/frame hash, and test result.

Do not use editor-only evidence to promote a runtime/capture fix.
