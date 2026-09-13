---
name: unity-playmode-verify
description: Verify Unity changes through compile, Play Mode interaction, runtime observation, visual evidence, logs, and rollback. Use whenever success depends on runtime behavior rather than file existence.
---

# Unity PlayMode Verify

## Golden path
`change/create → compile → error capture → Play Mode → interact/advance → observe → screenshot/frame/log evidence → assertions → receipt`

## Rules
- File creation is not success.
- Compilation is not gameplay success.
- Editor preview is not Play Mode success.
- A capture workaround is valid only if it advances the same runtime animation/game state the final product uses.
- Record Unity editor and relevant package versions with every version-sensitive failure.
- Import/material/rig fixes require a runtime visual check when the defect is visible.

## External trap intake
Useful external fixes enter as `external_advisory`. Reproduce in the target Unity project before promotion. Current examples include skinned-mesh freeze on an offscreen AnimationMode sampling path, embedded texture extraction for white FBX imports, and Recorder-version incompatibility. None is auto-applied until locally proven.

## Canonical promotion
Require a minimal reproduction scene or journey, before/after evidence, deterministic rerun, package/version constraint, and rollback path.
