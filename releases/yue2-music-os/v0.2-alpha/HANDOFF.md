# YuE2 Music OS v0.2 alpha handoff

## Goal

Maintain one score-first music workspace in which YuE2 supplies controllable composition candidates, symbolic tools verify score edits, people perform A/B selection, and separately governed renderers create final performances.

## Current implementation

- Target branch: `yue2-music-os-composition-router-v0.2-alpha-20260915`
- Release root: `releases/yue2-music-os/v0.2-alpha`
- Safe engine: deterministic `mock`
- Real composition adapters: first-party YuE2 and SheetSage2 helpers
- Renderer modes: manual export, operator command bridge, deterministic mock
- Persistence: SQLite plus immutable files beneath `YUE2_MUSIC_OS_DATA`
- UI: generation, transcription, score surgery, final-render router, artifact library, A/B listening
- Safety: token option, trusted hosts, no shell, contained paths, timeouts, one-process lock, restart recovery, provider receipt validation, commercial acknowledgement gate

## Evidence boundary

Passing controller tests does not prove real YuE2 inference or a hosted provider call. Manual packages explicitly say no authenticated API call occurred. A command adapter is only production-qualified after `docs/REAL_WORKER_ACCEPTANCE.md` and `docs/PRODUCTION_RENDERERS.md` acceptance evidence is recorded.

## Non-negotiable rules

- Never overwrite source uploads or baseline scores.
- Never call technical ranking musical quality.
- Never call symbolic equality waveform preservation.
- Never expose provider command definitions or credentials through the API.
- Never send audit-only noncommercial YuE2 audio to final-render packages.
- Never mark a live commercial command provider verified without a terms/contract reference and operator evidence.
- Preserve failures, prompts, revisions, logs, receipts, and partial outputs.
- Do not merge into `main` without explicit user approval.
