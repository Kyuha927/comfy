# Production renderer adapters

## Why this layer exists

YuE2 is used as a controllable composition and score-planning engine. A separate renderer may be chosen for the final performance. The controller keeps this division explicit so model licenses, provider terms, and technical evidence are not blurred together.

## Built-in providers

The following are manual export packages:

- `flow-lyria-manual`
- `suno-manual`
- `eleven-music-manual`
- `generic-manual`

They do not make network calls. Each package contains a provider-neutral request, style, lyrics, optional ABC, warnings, and an export receipt.

`mock-renderer` is a plumbing test only. It emits a deterministic WAV and is blocked when `commercial_intent=true`.

## Registering a command bridge

Set `YUE2_MUSIC_OS_RENDER_PROVIDERS_JSON` to a JSON object. Each key is a provider ID.

```json
{
  "lyria-bridge": {
    "label": "Operator Lyria bridge",
    "mode": "command",
    "argv": [
      "/absolute/path/to/python",
      "/absolute/path/to/adapter.py",
      "{request_json}",
      "{output_dir}",
      "{provider_id}"
    ],
    "timeout_seconds": 1800,
    "commercial_status": "operator-verified",
    "terms_reference": "internal-contract-001"
  }
}
```

Rules:

- The executable path must be absolute.
- No shell is used.
- Only the three documented placeholders are allowed.
- Credentials must be obtained by the adapter from its environment, operating-system keychain, or provider SDK configuration. Do not put secrets in the JSON definition.
- A commercial live command is blocked unless `commercial_status` is `operator-verified`.

## Input contract

`render-request.json` contains:

- provider identity and recorded terms state
- title and operator notes
- `style.txt`, `lyrics.txt`, and optional `score.abc`
- selected YuE2 candidate/seed provenance
- explicit confirmation that source audio is not included
- commercial intent and operator acknowledgement
- the expected output receipt contract

The request directs the adapter to create a new performance rather than copy the audit-only YuE2 audio.

## Output contract

The adapter writes `output/render-result.json`:

```json
{
  "status": "complete",
  "outputs": ["final-render.wav", "provider-metadata.json"]
}
```

Allowed statuses are `complete` and `needs_review`. Output entries must be relative, remain below the assigned output directory, exist, and be non-empty. On failure, the command logs and partial files remain attached to the failed job.

## Acceptance before production use

Record at least:

- provider/account/plan identity
- provider terms or commercial contract reference
- adapter version and source hash
- authentication method without secret values
- one successful rights-cleared render
- one provider-side failure and one timeout
- output receipt and file hashes
- pronunciation, structure, mix, and prompt-adherence review
- measured cost and latency

Until these checks exist, a command adapter is technically connected but not production-qualified.
