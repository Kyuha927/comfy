# HTTP API

The OpenAPI schema is available at `/api/openapi.json`. When `YUE2_MUSIC_OS_API_TOKEN` is set, send `X-Music-OS-Token` on all non-public API requests. Only `/api/health` and `/api/policy` are public.

## Core flow

1. `POST /api/projects`
2. Optional `POST /api/projects/{project_id}/uploads`
3. `POST /api/jobs/generate`
4. Poll `GET /api/jobs/{job_id}`
5. Optional `POST /api/jobs/rank-candidates`
6. Human A/B review
7. `POST /api/jobs/production-render`
8. Read `GET /api/projects/{project_id}/artifacts`

## Discovery

### Render providers

`GET /api/render-providers`

Returns public provider state only. Command argv and credentials are never returned.

## Job endpoints

### Generate

`POST /api/jobs/generate`

```json
{
  "project_id": "...",
  "style": "Korean cinematic J-pop, adult female vocal, 165 BPM",
  "lyrics": "[Verse]\n...",
  "cot": "full",
  "seed": 42,
  "abc_artifact_id": null,
  "candidate_count": 4
}
```

### Rank candidate integrity

`POST /api/jobs/rank-candidates`

```json
{
  "project_id": "...",
  "generation_job_id": "..."
}
```

The result has `scope=technical-readiness-only` and `quality_claim=false`. It checks receipts, one non-empty audio artifact, candidate status, parseable ABC when required, and failure markers. It does not judge musical quality.

### Production render

`POST /api/jobs/production-render`

```json
{
  "project_id": "...",
  "generation_job_id": "...",
  "candidate": "best-technical",
  "provider_ids": ["flow-lyria-manual"],
  "title": "LIN ASTER Theme",
  "notes": "Keep 165 BPM and make the chorus more explosive.",
  "commercial_intent": true,
  "license_review_acknowledged": true
}
```

`candidate` may be `best-technical` or an integer from 1 to 8. Commercial intent requires the explicit acknowledgement. The controller never sends audit-only YuE2 audio to provider packages.

### Transcribe

`POST /api/jobs/transcribe`

```json
{
  "project_id": "...",
  "source_artifact_id": "...",
  "melody_only": true
}
```

### Compare scores

`POST /api/jobs/compare`

```json
{
  "project_id": "...",
  "before_artifact_id": "...",
  "after_artifact_id": "...",
  "voices": "both",
  "allow_tempo_change": false
}
```

### Strip chords

`POST /api/jobs/strip-chords`

```json
{
  "project_id": "...",
  "source_artifact_id": "...",
  "keep_voice": "both"
}
```

## Command adapter receipt

A configured command renderer receives absolute `{request_json}` and `{output_dir}` paths through argv. It must create:

```json
{
  "status": "complete",
  "outputs": ["final-render.wav"]
}
```

Every output must be a non-empty relative file below `output_dir`. Absolute paths and traversal are rejected.
