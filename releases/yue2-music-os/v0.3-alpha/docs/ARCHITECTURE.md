# Architecture

## Design objective

The application is an evidence-preserving music production system rather than a prompt box:

```text
intent → YuE2 candidates → score checks → technical ranking → human listening
       → provider package/adapter → new final render → retained receipt
```

## Components

### Browser studio

The static UI exposes five modes: generation, audio transcription, score surgery, final-render routing, and artifact review. External renderer complexity is represented as provider status and rights state, not hidden behind a misleading “connected” badge.

### API

FastAPI validates requests with Pydantic and exposes projects, uploads, jobs, artifacts, policy, health, and render-provider discovery. An optional token protects non-public routes.

### Store

SQLite stores metadata. Bytes remain under one configured root. Source uploads are immutable. Every job has a fresh directory; every indexed artifact has a SHA-256 digest and a contained relative path.

### Sequential service

`MusicService` owns one executor and one process lock. Jobs left queued/running after termination are converted to explicit interrupted failures. Ranking and package creation share the same durable job lifecycle as model inference.

### Composition engines

- `MockEngine` exercises plumbing with deterministic test tones.
- `LocalEngine` invokes first-party YuE2 and SheetSage2 helper scripts with argv arrays.
- Generation and transcription have independent readiness checks.
- Timeout kills the process group.
- Exit code, receipt status, and required files must agree.

### Technical candidate evaluator

`rank_generation_candidates` checks only observable technical evidence:

- candidate request/result receipts
- supported completion status
- exactly one non-empty audio file
- decoded WAV metadata or partial compressed-audio evidence
- parseable ABC when score planning was requested
- absence of a failure receipt

The report explicitly sets `quality_claim=false`. Ties are deterministic. Ineligible candidates cannot be routed.

### Production render router

The router creates one immutable production package:

```text
production/
├── composition/          style, lyrics, optional ABC
├── audit/                source job, ranking, selected YuE2 audio
├── providers/<id>/       provider request, files, receipt/output
└── production-manifest.json
```

The provider package deliberately excludes source YuE2 audio. Built-in external services use manual export contracts. Operator-installed bridges use `command` mode with a registered absolute executable, a fixed placeholder set, no shell, a timeout, and a required `render-result.json` receipt.

### Renderer modes

- `manual`: creates a copy/paste package and records that no live call occurred.
- `command`: invokes an operator-configured local adapter and verifies its outputs.
- `mock`: creates a deterministic test tone and is prohibited for commercial intent.

## State transitions

```text
queued → running → succeeded + indexed artifacts
                 └→ failed + service-failure.json + partial evidence
```

No button press, subprocess start, or file appearance alone is treated as success.

## Extension rules

A future provider must fit the same request/receipt contract. Credentials stay outside manifests. Remote workers should use authenticated content-addressed transport, never arbitrary remote shell strings. Musical ranking must remain separate from technical readiness unless a listening evaluator has its own measured acceptance evidence.
