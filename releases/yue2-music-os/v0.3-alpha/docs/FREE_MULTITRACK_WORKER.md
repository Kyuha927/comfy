# Free multi-track transcription worker

## Purpose

`free-multitrack-v1` is the first executable free full-mix path for Note IR.
It keeps the controller independent from heavy machine-learning dependencies and can later be replaced by a paid or higher-quality provider without changing the editor, database, revision history, or export formats.

## Pipeline

1. Read the immutable source audio.
2. Separate it with `audio-separator` and `htdemucs_6s.yaml` into:
   - vocals
   - drums
   - bass
   - guitar
   - piano
   - other
3. Run Basic Pitch independently on vocals, bass, guitar, piano, and other.
4. Detect drum onsets with librosa and store them as generic MIDI-note-36 hit events.
5. Emit normalized multi-track JSON.
6. Let the existing Note IR fusion, uncertainty queue, editor, revisions, JSON export, and MIDI export handle the result.

The worker hashes the source before and after analysis and fails if size, modification time, or SHA-256 changes.

## Install on the target Mac

Requirements:

- macOS with Apple Silicon or another supported machine
- Python 3.11
- `ffmpeg`

Run:

```bash
cd releases/yue2-music-os/v0.3-alpha
bash scripts/install_free_multitrack_worker.sh
source var/workers/free-multitrack-v1/activate-provider.env
python -m yue2_music_os
```

The installer creates an isolated virtual environment, installs the optional packages, runs `pip check`, runs the worker self-test, records `pip freeze`, records an environment receipt, and writes the exact provider JSON used by the controller.

The first real analysis downloads the selected separator model. Model files are not bundled in the application release.

## Mac routing

The default precision mode is `auto`. On Apple Silicon it requests MPS autocast through `audio-separator`; elsewhere it keeps the conservative FP32 path. The default separator is six-stem Demucs because it provides a usable Mac-accelerated path.

A BS-RoFormer or remote GPU worker can be registered later through the same command-provider contract. It should not replace the Mac default unless its target-machine latency, memory use, licenses, and stem quality pass the same acceptance set.

## What individual-note editing means

The following are implemented now:

- click and edit one detected note or drum-hit event
- change pitch, cents, onset, end, duration, velocity, instrument, mute, delete, and review state
- preserve stable note identity and provider votes
- create an immutable revision for every save
- export the edited result as JSON and Standard MIDI

The following is deliberately not claimed:

- exact kick, snare, tom, and cymbal classification from the first drum worker
- guaranteed separation of two guitars inside the same guitar stem
- direct replacement of one chord tone inside the original polyphonic waveform

A symbolic edit changes Note IR and MIDI. A waveform edit remains `resynthesis-required` until a separately accepted audio-edit provider renders a new derivative without touching the source.

## Failure behavior

A failed stem is retained as an empty review track with an error receipt. Successful stems still produce a Music IR. The entire worker fails only when separation fails, the source changes, a path escapes the worker-owned output directory, or no note/onset event is produced at all.

## Licensing boundary

The worker code does not bundle external model weights.

- `audio-separator`: MIT-licensed package, subject to its notices
- Basic Pitch: Apache-2.0 package, subject to its model/package notices
- Demucs model/code and any downloaded checkpoints: review exact upstream notices before redistribution or commercial bundling

Runtime download for local evaluation is not treated as permission to redistribute weights. Production promotion requires recording the exact package versions, checkpoint identity, source URL, and applicable license in the acceptance receipt.

## Acceptance still required

Controller and contract tests do not prove musical accuracy. Production promotion still requires:

1. target-Mac installation and environment receipt
2. real full-mix inference on representative J-pop songs
3. stem audibility review
4. note/onset disagreement review against a second engine or human correction
5. runtime, memory, disk, and crash-recovery measurements
6. exact dependency and checkpoint license review
7. explicit approval before merging the Draft PR
