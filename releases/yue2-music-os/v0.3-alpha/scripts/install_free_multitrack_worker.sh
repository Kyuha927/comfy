#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${YUE2_FREE_WORKER_PYTHON:-python3.11}"
WORKER_ROOT="${YUE2_FREE_WORKER_ROOT:-$ROOT/var/workers/free-multitrack-v1}"
VENV="$WORKER_ROOT/venv"
CONFIG="$WORKER_ROOT/provider-config.json"
ENV_FILE="$WORKER_ROOT/activate-provider.env"
RECEIPT="$WORKER_ROOT/install-receipt.json"
WORKER_SCRIPT="$ROOT/examples/free_multitrack_command_provider.py"

command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  echo "Python 3.11 is required. Set YUE2_FREE_WORKER_PYTHON to an absolute compatible interpreter." >&2
  exit 2
}
command -v ffmpeg >/dev/null 2>&1 || {
  echo "ffmpeg is required. On macOS: brew install ffmpeg" >&2
  exit 2
}
test -f "$WORKER_SCRIPT"
mkdir -p "$WORKER_ROOT"

"$PYTHON_BIN" -m venv "$VENV"
PY="$VENV/bin/python"
"$PY" -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
"$PY" -m pip install --disable-pip-version-check \
  "${YUE2_AUDIO_SEPARATOR_SPEC:-audio-separator[cpu]}" \
  "${YUE2_BASIC_PITCH_SPEC:-basic-pitch}"
"$PY" -m pip check
"$PY" "$WORKER_SCRIPT" --self-test
"$VENV/bin/audio-separator" --env_info > "$WORKER_ROOT/audio-separator-env.txt" 2>&1 || true
"$PY" -m pip freeze --all > "$WORKER_ROOT/requirements.lock.txt"

"$PY" - "$PY" "$WORKER_SCRIPT" "$CONFIG" "$ENV_FILE" "$RECEIPT" <<'PY'
from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

python_bin = Path(sys.argv[1]).resolve()
worker_script = Path(sys.argv[2]).resolve()
config_path = Path(sys.argv[3]).resolve()
env_path = Path(sys.argv[4]).resolve()
receipt_path = Path(sys.argv[5]).resolve()

provider = {
    "free-multitrack-v1": {
        "mode": "command",
        "tier": "free",
        "label": "Free six-stem transcription (Demucs 6s + Basic Pitch)",
        "argv": [
            str(python_bin),
            str(worker_script),
            "--input", "{input}",
            "--output-json", "{output_json}",
            "--output-dir", "{output_dir}",
            "--instrument-hint", "{instrument_hint}",
            "--precision", "auto"
        ],
        "timeout_seconds": 21600,
        "capabilities": {
            "full_mix": True,
            "isolated_stem": True,
            "polyphonic": True,
            "per_note_confidence": False,
            "direct_audio_edit": False
        },
        "license_reference": (
            "audio-separator MIT; Spotify Basic Pitch Apache-2.0; "
            "Demucs code/weights and downloaded model notices must be reviewed before redistribution"
        )
    }
}
config_path.write_text(json.dumps(provider, indent=2, sort_keys=True) + "\n", encoding="utf-8")
env_path.write_text(
    "export YUE2_MUSIC_OS_NOTE_PROVIDERS_JSON="
    + json.dumps(json.dumps(provider, separators=(",", ":")))
    + "\n",
    encoding="utf-8"
)

def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None

receipt = {
    "installed_at": datetime.now(timezone.utc).isoformat(),
    "python": sys.version,
    "platform": platform.platform(),
    "machine": platform.machine(),
    "provider_id": "free-multitrack-v1",
    "audio_separator_version": package_version("audio-separator"),
    "basic_pitch_version": package_version("basic-pitch"),
    "provider_config": str(config_path),
    "worker_script": str(worker_script),
    "source_audio_policy": "read-only",
    "waveform_single_note_edit": "not-claimed-resynthesis-required"
}
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

cat <<EOF
FREE_MULTITRACK_WORKER_INSTALL=PASS
WORKER_ROOT=$WORKER_ROOT
PROVIDER_CONFIG=$CONFIG
ENV_FILE=$ENV_FILE
NEXT=source "$ENV_FILE" && restart YuE2 Music OS
EOF
