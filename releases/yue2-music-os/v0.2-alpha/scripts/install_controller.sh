#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 or newer is required")
print(f"Controller Python: {sys.version.split()[0]}")
PY

cd "$ROOT"
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -e '.[dev]'

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

.venv/bin/python -m compileall -q src
.venv/bin/pytest

cat <<EOF

Controller installed and tested.

Run:
  cd "$ROOT"
  source .venv/bin/activate
  set -a; source .env; set +a
  yue2-music-os init-demo
  yue2-music-os serve
EOF
