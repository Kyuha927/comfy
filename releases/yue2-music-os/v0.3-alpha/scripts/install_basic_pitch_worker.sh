#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${YUE2_NOTE_PYTHON:-python3.11}"
RUNTIME_ROOT="${YUE2_NOTE_RUNTIME:-$HOME/Library/Application Support/YuE2 Music OS/note-workers/basic-pitch}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$RUNTIME_ROOT/venv"
CONFIG_OUT="$RUNTIME_ROOT/provider.json"
WRAPPER="$RELEASE_ROOT/examples/basic_pitch_command_provider.py"

command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  printf 'Required Python executable not found: %s\n' "$PYTHON_BIN" >&2
  exit 2
}
[[ -f "$WRAPPER" ]] || {
  printf 'Basic Pitch wrapper is missing: %s\n' "$WRAPPER" >&2
  exit 3
}

mkdir -p "$RUNTIME_ROOT"
"$PYTHON_BIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install --disable-pip-version-check 'basic-pitch==0.4.0'
"$VENV/bin/python" - <<'PY'
from importlib.metadata import version
from basic_pitch.inference import predict
print('basic-pitch', version('basic-pitch'), 'import PASS')
PY

python3 - "$VENV/bin/python" "$WRAPPER" "$CONFIG_OUT" <<'PY'
import json
import sys
from pathlib import Path
python_path, wrapper_path, output_path = map(lambda value: str(Path(value).expanduser().resolve()), sys.argv[1:])
payload = {
    "basic-pitch-cli": {
        "mode": "command",
        "tier": "free",
        "label": "Basic Pitch isolated worker",
        "argv": [
            python_path,
            wrapper_path,
            "--input", "{input}",
            "--output-json", "{output_json}",
            "--instrument-hint", "{instrument_hint}"
        ],
        "timeout_seconds": 3600,
        "capabilities": {
            "full_mix": False,
            "isolated_stem": True,
            "polyphonic": True,
            "per_note_confidence": False,
            "direct_audio_edit": False
        },
        "license_reference": "Spotify Basic Pitch 0.4.0, Apache-2.0; preserve upstream notices"
    }
}
Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(output_path)
PY

printf '\nBasic Pitch worker installed.\n'
printf 'Provider JSON: %s\n' "$CONFIG_OUT"
printf 'Set YUE2_MUSIC_OS_NOTE_PROVIDERS_JSON to the JSON object in that file, then restart YuE2 Music OS.\n'
