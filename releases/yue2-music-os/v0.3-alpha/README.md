# YuE2 Music OS v0.3 alpha

A score-first music production controller that uses **YuE2 as a composition laboratory** and routes approved material to separate final renderers. It combines generation, transcription, score surgery, technical candidate checks, render packaging, artifact retention, and A/B listening in one resumable workspace.

> **Evidence boundary:** the mock engine, web UI, API, storage, candidate integrity ranking, render packaging, command-adapter contract, ABC checks, and CI are executable without model weights. Real YuE2/SheetSage2 inference and any external commercial renderer remain unverified until their separate hardware/provider acceptance gates pass.

## What is implemented

- One local web workspace with projects, uploads, sequential jobs, artifacts, and A/B audio slots.
- `full`, `melody`, and `off` generation requests through the first-party YuE2 helper interface.
- SheetSage2 audio-to-ABC requests through the first-party transcription helper interface.
- Fail-closed parsing and exact symbolic comparison of pitch, onset, duration, meter, bar grid, and optional tempo changes.
- Chord removal to a new file, with selected-voice preservation checks.
- Deterministic **technical candidate ranking** based only on receipts, audio presence, parseable ABC, and review/failure flags.
- A final-render router with built-in manual export packages for Flow/Lyria, Suno, Eleven Music, and a generic renderer.
- An argv-only command adapter for an operator's authenticated renderer bridge, with no shell, fixed placeholders, timeouts, logs, and mandatory output receipts.
- Commercial-intent gate: explicit license acknowledgement is required before a production package is created.
- Noncommercial YuE2 audio is retained for audit and A/B listening but excluded from final-render provider packages.
- Immutable source uploads and fresh output directories for every job.
- SQLite audit index plus SHA-256, size, model/request logs, failures, and generated artifacts.
- Single-instance data-directory lock, interrupted-job recovery, streamed subprocess logs, trusted-host controls, token support, upload limits, and one GPU job at a time.

## Intended workflow

```text
lyrics + style
      │
      ▼
YuE2 composition candidates
      │
      ├── ABC edit / compare / strip chords
      ├── technical readiness ranking
      └── human A/B listening
                │
                ▼
approved candidate + score + lyrics + style
                │
                ├── manual Flow/Lyria package
                ├── manual Suno package
                ├── manual Eleven Music package
                └── operator-configured command adapter
                            │
                            ▼
                  new final performance + receipt
```

The controller never calls a proxy score “music quality.” Technical ranking and musical selection are separate evidence channels.

## Fast start: safe mock mode

Linux or macOS with Python 3.11+:

```bash
cd releases/yue2-music-os/v0.2-alpha
./scripts/install_controller.sh
source .venv/bin/activate
cp .env.example .env
set -a; source .env; set +a

yue2-music-os init-demo
yue2-music-os serve
```

Open `http://127.0.0.1:8787`.

The default `mock` engine creates deterministic 48 kHz stereo test tones and sample ABC files. The `mock-renderer` also creates a test tone only and is blocked for commercial-intent jobs.

## Run verification

```bash
source .venv/bin/activate
pytest --cov=yue2_music_os --cov-branch --cov-report=term-missing
python -m compileall -q src tests
node --check src/yue2_music_os/static/app.js
bash -n scripts/*.sh
./scripts/smoke.sh
```

## Real Linux/NVIDIA worker

The upstream project recommends a BF16-capable NVIDIA GPU and a 24 GB baseline for YuE2. SheetSage2 is installed separately because its dependency versions differ.

```bash
./scripts/install_worker.sh --accept-noncommercial-model-license --download-models
source runtime/worker.env
export YUE2_MUSIC_OS_ENGINE=local
export YUE2_MUSIC_OS_MODEL_USE_SCOPE=noncommercial

yue2-music-os doctor
yue2-music-os serve
```

For a separately licensed YuE2 deployment:

```bash
export YUE2_MUSIC_OS_MODEL_USE_SCOPE=commercial-licensed
export YUE2_MUSIC_OS_COMMERCIAL_LICENSE_REFERENCE='contract-or-license-record-id'
```

This records operator policy. It does not create rights or replace legal review.

## Final renderer connections

The built-in Flow/Lyria, Suno, and Eleven Music entries are **manual export contracts**, not claims of API access. They create self-contained packages containing:

- `render-request.json`
- `style.txt`
- `lyrics.txt`
- optional `score.abc`
- rights warnings and an export receipt

An authenticated local bridge can be registered with `YUE2_MUSIC_OS_RENDER_PROVIDERS_JSON`. Example:

```bash
export YUE2_MUSIC_OS_RENDER_PROVIDERS_JSON='{
  "lyria-bridge": {
    "label": "Operator Lyria bridge",
    "mode": "command",
    "argv": [
      "/absolute/path/to/python",
      "/absolute/path/to/adapter.py",
      "{request_json}",
      "{output_dir}"
    ],
    "timeout_seconds": 1800,
    "commercial_status": "operator-verified",
    "terms_reference": "internal-contract-001"
  }
}'
```

The adapter must write `output/render-result.json` with status `complete` or `needs_review` and a non-empty list of relative output paths. See [`docs/PRODUCTION_RENDERERS.md`](docs/PRODUCTION_RENDERERS.md).

## Controller on Mac, worker on another machine

v0.2 still executes YuE2 and configured command adapters on the API host. The safest deployment remains a trusted SSH tunnel to a loopback-bound Linux GPU host:

```bash
ssh -L 8787:127.0.0.1:8787 gpu-host
```

Then open `http://127.0.0.1:8787` on the Mac.

## Main commands

```bash
yue2-music-os doctor
yue2-music-os init-demo [--no-generate]
yue2-music-os serve [--host 127.0.0.1] [--port 8787]
```

A non-loopback bind without `YUE2_MUSIC_OS_API_TOKEN` is refused unless the operator explicitly passes `--insecure-no-auth`. Wildcard hosts require a token.

## Data layout

```text
var/
├── music_os.sqlite3
└── projects/<project-id>/
    ├── uploads/
    └── jobs/<job-id>/
        ├── request, command, log, and failure receipts
        ├── output/...
        └── production/
            ├── composition/       # style, lyrics, optional score
            ├── audit/             # ranking and source YuE2 evidence
            ├── providers/...      # renderer packages and outputs
            └── production-manifest.json
```

Every indexed artifact receives a SHA-256 digest. Provider output paths are resolved beneath their assigned output directory before indexing.

## Current limitations

- No partial waveform inpainting. A score edit causes a new complete recording.
- Symbolic equality does not guarantee identical singing, instrumentation, mix, or waveform.
- Automatic transcription must be reviewed against source audio.
- Technical ranking does not evaluate composition, emotion, pronunciation, mix, or prompt adherence.
- Manual provider packages require the operator to perform the external render and preserve the resulting provider receipt.
- Command adapters require a separately installed, authenticated bridge and verified provider terms.
- The controller does not determine copyright ownership or commercial eligibility.
- Real GPU inference, Korean/Japanese quality, OOM recovery, long-song behavior, and live commercial-renderer execution require separate acceptance evidence.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/PRODUCTION_RENDERERS.md`](docs/PRODUCTION_RENDERERS.md)
- [`docs/SECURITY.md`](docs/SECURITY.md)
- [`docs/API.md`](docs/API.md)
- [`docs/REAL_WORKER_ACCEPTANCE.md`](docs/REAL_WORKER_ACCEPTANCE.md)
- [`HANDOFF.md`](HANDOFF.md)

## Licensing

First-party controller code is Apache-2.0. Model weights, hosted services, source recordings, lyrics, voices, and generated outputs retain their own terms and rights requirements. The controller license does not change the license of YuE2, SheetSage2, Flow/Lyria, Suno, Eleven Music, or any other renderer.


## Note IR and individual-note editing

v0.3 adds a free-first Note IR pipeline next to the existing score and production-render paths. Open `/note-editor.html` to analyze or import note detections, inspect provider votes and confidence, edit one note, restore immutable revisions, and export JSON or MIDI. Source audio is never overwritten. Polyphonic single-note waveform edits remain an explicit resynthesis or specialist-engine boundary.

See `docs/NOTE_IR.md` for provider configuration, the normalized JSON contract, free/paid adapter replacement, and acceptance gates.
