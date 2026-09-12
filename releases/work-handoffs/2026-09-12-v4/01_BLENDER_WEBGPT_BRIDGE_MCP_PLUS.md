# ONE-SHOT WORK HANDOFF — Blender WebGPT Bridge / MCP-Plus

## Model routing
- MAIN / architecture / root-cause owner: **GPT-6 Astra — XHigh**
- Blender implementation worker: **GPT-5.6 Sol — High**
- Visual/spatial QA and final independent reviewer: **GPT-6 Astra — XHigh**
- Regression/test worker: **GPT-5.6 Terra — High**
- Logs, inventory, repetitive state collection: **GPT-5.6 Luna — Medium**
- Never use any Pro model/profile in Work.

## Mission
Take full ownership of the existing local Blender Pro Bridge built so WebGPT/ChatGPT can operate Blender. Raise it to practical parity with, and preferably superiority over, a strong modern Blender MCP. Do not replace the project with MCP and do not stop at recommendations.

Recover existing implementation, prior tests, bridge health, tool schemas, logs, scenes, known failures, and architecture before modifying anything. Preserve accepted model/workspace routing.

Build a capability matrix covering scene/object/property inspection, geometry, modifiers, materials, rigs/animation where relevant, cameras, viewport/render inspection, Python execution, screenshots/renders, undo/rollback, transaction safety, long operations, timeouts, cancellation, reconnect/restart, state synchronization, error propagation, deterministic verification, and observability.

Run discriminating end-to-end smoke tests through the same path ChatGPT uses. A successful API response is not proof. Verify actual Blender state and rendered/visual state. Find the smallest root cause before broad rewrites. Strengthen weak architecture instead of stacking fragile patches.

The Sol implementation worker may modify code and tests. Terra owns repeatable regression/failure cases. Luna only gathers bounded evidence. Astra must arbitrate architecture and visual correctness and perform the final adversarial audit.

Completion requires: critical workflows working end to end; no silent-success behavior; visual/state verification; safe rollback strategy; performance/stability checks; and explicit evidence. Report MCP parity/superiority per capability, changes made, tests run, failures fixed, and only genuinely external blockers.

Continue through inspection, implementation, testing, repair, and validation. Do not return a plan as the final result.