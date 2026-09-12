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

## Unity binding

Recommended domain: `unity`.

Use one production path string for a gate set, for example:
`agent->unity-editor->compile->playmode->capture`. Receipts should include editor/package versions,
compile result, PlayMode journey id, runtime screenshot/frame hash, and test result.

Do not use editor-only evidence to promote a runtime/capture fix.
