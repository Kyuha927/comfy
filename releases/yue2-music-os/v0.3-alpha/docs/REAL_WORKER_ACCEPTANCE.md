# Real worker acceptance gate

Do not describe the real model path as complete until every applicable item below has recorded evidence.

## A. Host and runtime

- [ ] Linux host identity and date recorded.
- [ ] NVIDIA GPU model, driver, CUDA visibility, and VRAM recorded.
- [ ] BF16 support confirmed.
- [ ] Free disk space recorded before and after model download.
- [ ] YuE repository code commit pinned.
- [ ] YuE2 model revision pinned.
- [ ] YuE2 VAE revision pinned.
- [ ] SheetSage2 model and remote-code revision pinned.
- [ ] Separate Python environments confirmed.
- [ ] `yue2-music-os doctor` reports the required lane ready.

## B. Generation smoke

- [ ] One original `cot=full` request finishes.
- [ ] `audio.flac` or other native audio artifact is playable.
- [ ] `score.abc`, request/config, result, model identity, tokens/latents where provided, and logs are preserved.
- [ ] No truncation flag is hidden.
- [ ] Peak VRAM, wall time, audio duration, and real-time factor are recorded.
- [ ] A second seeded run documents whether outputs are bit-identical or merely request-reproducible.

## C. Score-conditioned edit

- [ ] Baseline score is copied, never overwritten.
- [ ] Harmony-only edit passes exact melody/meter comparison and reports changed harmony.
- [ ] Both full recordings are retained.
- [ ] Listening confirms whether requested harmony is audibly realized.
- [ ] Unchanged score regions are not falsely claimed to have waveform identity.

## D. Cover/transcription

- [ ] A rights-cleared source audio file is hashed and retained.
- [ ] SheetSage2 produces `score.abc` and a manifest without hidden errors.
- [ ] Melody and section order are manually reviewed against the recording.
- [ ] Chords are removed for `cot=melody`, with invariants passing.
- [ ] A cover render completes with new target style.
- [ ] Source singer identity preservation is not claimed.

## E. Korean/Japanese validation

Use at least five rights-cleared prompts per language and score separately:

- pronunciation and dropped/duplicated syllables
- lyric order
- melody quality
- structural coherence
- vocal naturalness
- mix and artifacts
- prompt/style adherence

Keep all candidates, not only winners.

## F. Failure behavior

- [ ] OOM produces a failed job and retained logs, not a false success.
- [ ] Timeout kills the whole process group and records failure.
- [ ] Missing model/revision fails before expensive work.
- [ ] Invalid ABC fails closed.
- [ ] Service restart leaves prior artifacts readable and terminal jobs intact.
- [ ] Concurrent submissions remain sequential.

## G. Licensing and release

- [ ] Intended use is recorded as noncommercial or supported by a separate commercial license record.
- [ ] Source recording, lyrics, and voice/artist rights are documented.
- [ ] Model weights are not bundled into this repository or application package.
- [ ] Public release notes distinguish measured facts from untested expectations.

## H. Final renderer routing

- [ ] Candidate technical ranking is retained and explicitly marked not a quality verdict.
- [ ] Human A/B selection is recorded before final release.
- [ ] Noncommercial YuE2 audio remains audit-only and is absent from provider request packages.
- [ ] Provider/account/plan and current commercial terms are recorded.
- [ ] Command adapter executable, version, and source hash are recorded.
- [ ] Credentials are not present in requests, logs, or artifacts.
- [ ] One successful provider render preserves its `render-result.json` and output hashes.
- [ ] One malformed output path and one missing receipt fail closed.
- [ ] Timeout retains logs and terminates the provider process group.
- [ ] Korean/Japanese pronunciation, structure, vocal naturalness, mix, and prompt adherence are manually scored.
- [ ] Cost and wall time are measured.
