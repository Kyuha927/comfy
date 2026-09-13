---
name: 2d-motion-compression
description: Coarse-to-fine reference/video analysis for sprite and 2D animation work. Use when motion, pose, gesture, or keyframe information must be extracted without spending tokens on every frame.
---

# 2D Motion Compression

## Goal
Convert long visual sequences into a small motion specification before generation or animation work begins.

## Procedure
1. Read metadata first: duration, fps, resolution, source identity.
2. Produce an overview contact sheet at low temporal density.
3. Mark only windows with meaningful pose/camera/motion change.
4. Produce dense montages only for those windows.
5. Extract: base pose, repeated motion, accent/climax, transition, body-part deltas.
6. Select 4–8 representative poses for each loop or action unless the motion demonstrably needs more.
7. Pass a compact pose/timing spec to the sprite/generation stage.
8. Verify the produced sheet deterministically: dimensions, alpha, frame count/order, palette/format, import metadata.

## Token guardrails
- Never begin with maximum-density extraction over the full clip.
- Never send duplicate/near-identical frames to a reasoning model when a contact sheet answers the same question.
- Keep raw frames as artifacts; keep the prompt/context to the derived motion spec plus only the few frames needed to adjudicate ambiguity.

## Evidence
Record source hash/URL, extraction parameters, selected windows, final key-pose timestamps, and sprite/import validation results.
