# YuE2 Music OS v0.3 alpha handoff

## Goal

Keep the existing YuE2 composition and commercial-render router intact while adding a free-first, provider-neutral transcription layer whose smallest editable object is one note.

## Baseline and branch

- Repository: `Kyuha927/comfy`
- Preserved baseline release: `releases/yue2-music-os/v0.2-alpha`
- Development release: `releases/yue2-music-os/v0.3-alpha`
- Development branch: `yue2-music-os-note-ir-free-v0.3-dev-20260916`
- v0.2 remains immutable; v0.3 is copied from the previously verified v0.2 source and receives an overlay.

## Implemented in v0.3

- Stable-ID Music IR for individual notes, tracks, instruments, confidence and provider votes.
- Free-first provider registry with optional Basic Pitch and isolated command adapters.
- Multi-track normalized JSON contract for YourMT3-family, stem-first, paid or future engines.
- Sequential provider execution to avoid GPU contention.
- Partial-provider-failure receipts and a human review queue.
- Non-destructive pitch, cents, onset, duration, velocity, instrument, mute and delete edits.
- Immutable revisions and restore-as-new-revision behavior.
- Standard MIDI and JSON exports.
- Same-server piano-roll editor at `/note-editor.html`.
- Existing API token and trusted-host protections inherited by all Note IR endpoints.

## Evidence boundary

Passing controller tests proves the data model, adapter boundary, revision history, API round trip, MIDI writer and browser syntax. It does not prove real multi-instrument transcription quality. Basic Pitch is live only when its optional runtime is installed. YourMT3-family and stem-first workers are command-provider integration points until target-Mac installation and representative-audio acceptance are recorded.

Changing a symbolic note changes Music IR and MIDI. It does not silently change one tone inside a polyphonic waveform. Such audio correction remains `resynthesis-required` unless a separately accepted specialist audio-edit provider is configured.

## Non-negotiable rules

- Never overwrite uploaded source audio.
- Never erase a revision or provider failure receipt.
- Never call a confidence routing score a calibrated probability.
- Never call a MIDI correction a waveform correction.
- Never expose provider commands, credentials or private paths through the public API.
- Never mark a paid slot live without a configured licensed adapter and terms reference.
- Never promote real-model quality without target-Mac inference plus listening evidence.
- Do not merge into the authoritative branch or `main` without explicit user approval.

## Next acceptance lane

Install one free full-mix worker and one free isolated-stem worker on the target Mac, run a representative J-pop set, measure note/onset/instrument disagreement, review flagged notes by ear, and record exact code/checkpoint licenses before production promotion.
