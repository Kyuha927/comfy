---
name: failure-to-skill-promotion
description: Convert repeated 2D/Blender/Unity production failures into compact reusable skills without fossilizing one-off hacks. Use after a failure is actually diagnosed and repaired.
---

# Failure → Skill Promotion

## State machine
`novel → candidate → canonical → deprecated`

External knowledge enters at `external_advisory`, never directly at `canonical`.

## Candidate capture
Store only operational facts:
- failure id/domain;
- stable error code/fingerprint;
- context/version constraints;
- smallest diagnosis probe;
- repair;
- forbidden/known-bad paths;
- verification;
- rollback;
- confidence;
- evidence receipts;
- last verified date.

Do not paste full chat history into the skill.

## Promotion gate
Promote only when all are true:
1. failure was reproduced or directly observed in the target system;
2. repair succeeds through the real production path;
3. smallest discriminating regression/smoke passes;
4. visible failures have visual/runtime evidence;
5. repair is bounded enough to avoid collateral changes;
6. rollback is known;
7. version/context constraints are explicit.

## Upgrade behavior
When a canonical record fails:
- stop automatic reuse for that context;
- open a new candidate or mark the old one deprecated/superseded;
- investigate the delta, not the entire historical problem;
- update the regression test before re-promotion.

The knowledge base must get **smaller and sharper**, not merely longer.
