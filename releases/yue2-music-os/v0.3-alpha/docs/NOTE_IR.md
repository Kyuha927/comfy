# Note IR: free-first transcription and note-level editing

## What this adds

YuE2 Music OS now has a separate Note IR layer beside the existing score-first composition and production-render paths.

The minimum editable object is one note. Every note keeps:

- a stable `note_id`
- instrument and track ownership
- MIDI pitch and cents offset
- start, end, duration, optional bar and beat
- velocity
- pitch, timing, instrument and overall confidence
- every provider vote used to form the note
- review state
- an explicit audio-editability boundary

The source audio is immutable. Editing `G#4` to `A4` creates a new Music IR revision and changes JSON/MIDI exports. It does not silently claim that the original waveform was changed.

## User flow

Open `/note-editor.html` in the same YuE2 Music OS server.

1. Select a project and an uploaded audio artifact.
2. Select one or more ready transcription providers.
3. Run analysis, or import normalized provider JSON.
4. Click one rectangle in the piano roll.
5. Correct pitch, cents, timing, velocity, instrument, mute/delete state, or review state.
6. Save. A new immutable revision is created.
7. Export the current revision as JSON or Standard MIDI File.
8. Restore any earlier revision. Restoration itself becomes a new revision, so history is never rewritten.

## Free-first provider design

The editor and Music IR never depend on one vendor. Providers are adapters that must return the normalized JSON contract below.

### Built in

| Provider | Cost | Best role | Runtime behavior |
|---|---:|---|---|
| `basic-pitch` | Free | One isolated melodic or polyphonic instrument | Automatically ready when the optional `basic-pitch` Python package is importable |
| `normalized-json` | Free | Import YourMT3, MT3, research models, DAW scripts, or hand-corrected data | Always ready for import; it does not run audio inference |

Basic Pitch is intentionally not installed as a base dependency. Its machine-learning dependencies can conflict with the controller's Python runtime. Use either:

- the built-in adapter when the package works in the controller environment, or
- `examples/basic_pitch_command_provider.py` from an isolated Python 3.11 virtual environment.

For a local macOS/Linux bootstrap, run `scripts/install_basic_pitch_worker.sh`. It creates an isolated virtual environment, pins Basic Pitch 0.4.0, verifies the import, and writes a provider JSON file. The script is optional and never runs during application install or CI.

### External free engines

Full-mix multi-instrument systems such as YourMT3-family models, and stem-first pipelines such as BS-RoFormer plus a specialist AMT model, should be wrapped as command providers. The wrapper may live in its own virtual environment and GPU stack.

The controller runs providers sequentially. This prevents two GPU-heavy workers from fighting for memory and keeps receipts deterministic.

Set `YUE2_MUSIC_OS_NOTE_PROVIDERS_JSON` to a JSON object. Every command uses an absolute executable path and is invoked without a shell.

```json
{
  "yourmt3-free": {
    "mode": "command",
    "tier": "free",
    "label": "YourMT3 free full-mix wrapper",
    "argv": [
      "/absolute/path/to/yourmt3-venv/bin/python",
      "/absolute/path/to/yourmt3_wrapper.py",
      "--input", "{input}",
      "--output-json", "{output_json}",
      "--instrument-hint", "{instrument_hint}"
    ],
    "timeout_seconds": 10800,
    "capabilities": {
      "full_mix": true,
      "isolated_stem": true,
      "polyphonic": true,
      "per_note_confidence": true,
      "direct_audio_edit": false
    },
    "license_reference": "Record the exact code and checkpoint license here"
  }
}
```

Supported placeholders are:

- `{input}`: immutable source-audio path
- `{output_json}`: exact normalized JSON path the provider must create
- `{output_dir}`: provider-specific receipt directory
- `{instrument_hint}`: optional hint from the editor
- `{provider_id}`: configured provider ID

Provider stdout and stderr are truncated to bounded receipt logs. A non-zero exit, timeout, missing JSON, invalid schema, or provider-ID mismatch is a recorded failure. If another selected provider succeeds, its result can still produce a Music IR and the failed provider remains in the job receipt.

## Paid replacement without redesign

Paid engines use the same command adapter and the same normalized result. Change only the provider definition:

```json
{
  "licensed-transcriber": {
    "mode": "command",
    "tier": "paid",
    "label": "Licensed transcription bridge",
    "argv": [
      "/absolute/path/to/bridge",
      "--input", "{input}",
      "--output", "{output_json}"
    ],
    "license_reference": "invoice-or-contract-reference"
  }
}
```

The built-in `klangio-paid-slot`, `ripx-paid-slot`, and `melodyne-paid-slot` entries are disabled labels, not claims of live API access. They make the future replacement points visible. Configure a licensed command bridge before marking one ready.

A sensible routing policy is:

- high-confidence agreement: keep free result
- medium confidence: run another free provider
- low confidence or provider disagreement: optionally run a paid provider
- unresolved conflict: show the note in the human review queue

## Normalized provider JSON

```json
{
  "provider_id": "yourmt3-free",
  "provider_version": "checkpoint-sha-or-version",
  "tier": "free",
  "mode": "command",
  "tracks": [
    {
      "track_id": null,
      "name": "Electric Guitar",
      "instrument": "electric-guitar",
      "stem": "guitar",
      "polyphonic": true,
      "notes": [
        {
          "provider_note_id": "raw-1842",
          "pitch_midi": 68,
          "cents": -7.0,
          "start_sec": 73.428,
          "end_sec": 73.746,
          "velocity": 87,
          "confidence": 0.97
        }
      ]
    }
  ],
  "warnings": [],
  "metadata": {
    "checkpoint": "exact-checkpoint-id"
  }
}
```

Unknown fields are ignored by Pydantic's default model behavior, but wrappers should keep their output small and explicit. Times are seconds from the beginning of the immutable source artifact.

## Consensus and uncertainty

Provider detections are grouped when instrument, onset, duration overlap, and pitch are close. The fused note records every original vote. Provider disagreement, weak input confidence, or timing spread lowers the overall confidence and sends the note to the review queue.

The confidence score is a routing heuristic, not a scientifically calibrated probability. The UI displays the original provider votes so a user or another reasoning model can inspect why a note was accepted.

## Audio-edit boundary

The system distinguishes three cases:

- `symbolic-only`: JSON, score logic, and MIDI can be edited; no claim about waveform mutation.
- `monophonic-pitch`: a future configured pitch engine may render the change on an isolated monophonic stem.
- `resynthesis-required`: the note is inside polyphonic audio, so a safe result normally requires source separation plus resynthesis or a specialist editor.

V1 never overwrites source audio. This avoids the dangerous illusion that a MIDI correction also fixed a chord tone inside the recording.

## API surface

- `GET /api/note-providers`
- `POST /api/note-ir/import`
- `POST /api/note-jobs/analyze`
- `GET /api/note-jobs/{job_id}`
- `GET /api/projects/{project_id}/note-jobs`
- `GET /api/projects/{project_id}/note-irs`
- `GET /api/note-ir/{music_ir_id}`
- `GET /api/note-ir/{music_ir_id}/review`
- `PATCH /api/note-ir/{music_ir_id}/notes/{note_id}`
- `POST /api/note-ir/{music_ir_id}/restore`
- `GET /api/note-ir/{music_ir_id}/revisions`
- `GET /api/note-ir/{music_ir_id}/export.json`
- `GET /api/note-ir/{music_ir_id}/export.mid`

All endpoints except public health/policy inherit the existing `X-Music-OS-Token` protection.

## Verification gates

The Note IR change is not production-promoted merely because unit tests pass. Required gates are:

1. Pydantic validation and stable-ID tests.
2. Provider command sandbox tests: no shell, absolute executable, bounded timeout, strict output contract.
3. Revision immutability and revision-conflict tests.
4. MIDI binary-header and note-event tests.
5. API authentication and round-trip edit tests.
6. JavaScript syntax check.
7. Existing YuE2 Music OS regression suite.
8. Real-model acceptance on the target Mac with representative J-pop full mixes and isolated stems.
9. Human listening review of low-confidence and provider-disagreement notes.
10. Separate acceptance for any future audio re-render engine.
