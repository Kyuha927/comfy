---
name: failure-to-skill-promotion
description: Convert repeated 2D/Blender/Unity production failures into compact reusable skills without fossilizing one-off hacks. Use only after a failure is actually observed, diagnosed, repaired, and evidenced.
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

Do not paste full chat history into the skill. The purpose is compression, not archival bloat.

## Mechanical promotion gate
Record evidence as JSONL events matching `router/evidence_event.schema.json`.
The latest state of every gate must be PASS:

1. `reproduction` — target system actually exhibited the failure;
2. `repair` — bounded repair succeeded;
3. `same_path_verification` — success came through the real production path;
4. `rollback` — recovery path was exercised or discriminatingly verified;
5. `regression` — smallest repeatable smoke/regression passed;
6. `receipt` — durable evidence was recorded.

All six PASS events must share the same `environment` and `execution_path`. Every event needs a non-empty receipt.

Run:

```bash
python production-skill-os/router/promotion_engine.py validate --evidence <events.jsonl>
python production-skill-os/router/promotion_engine.py assess \
  --evidence <events.jsonl> \
  --record-id <failure-id>
```

The engine only emits a proposal. It never edits the catalog or promotes a record by itself.

## Canonical scope
A canonical record must include a non-empty `scope`, at minimum the proven environment and execution path. Automatic reuse outside that scope is forbidden.

## Upgrade behavior
When a canonical record fails:
- stop automatic reuse for that context;
- append a FAIL evidence event for the broken gate;
- investigate the delta, not the entire historical problem;
- update the regression before re-promotion;
- deprecate or supersede the old record if the fingerprint/repair contract changed.

## Duplicate control
The router rejects duplicate active fingerprints. Prefer sharpening or superseding one record over accumulating near-duplicates.

The knowledge base must get **smaller and sharper**, not merely longer.
