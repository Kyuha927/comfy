#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT/runtime"
YUE_REF="88da114a67df892af0329472073b96a5ef700b93"
DOWNLOAD_MODELS=0
ACCEPTED=0
YUE_MODEL_REVISION=""
YUE_VAE_REVISION=""
SHEETSAGE2_REVISION=""

usage() {
  cat <<'EOF'
Usage: install_worker.sh --accept-noncommercial-model-license [options]

Options:
  --runtime-dir PATH       Runtime root (default: <release>/runtime)
  --yue-ref REF            Reviewed YuE repository commit/tag
  --download-models        Download public model snapshots and install SheetSage2
  --yue-model-revision REF Pin the YuE2-3B model snapshot
  --yue-vae-revision REF   Pin the YuE2-Vae model snapshot
  --sheetsage2-revision REF
                           Pin SheetSage2 weights and remote code
  --accept-noncommercial-model-license
                           Required acknowledgement for the checked public weights
  -h, --help               Show this help

This script prepares a Linux/NVIDIA worker. It does not grant commercial rights.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runtime-dir) RUNTIME_DIR="$2"; shift 2 ;;
    --yue-ref) YUE_REF="$2"; shift 2 ;;
    --download-models) DOWNLOAD_MODELS=1; shift ;;
    --yue-model-revision) YUE_MODEL_REVISION="$2"; shift 2 ;;
    --yue-vae-revision) YUE_VAE_REVISION="$2"; shift 2 ;;
    --sheetsage2-revision) SHEETSAGE2_REVISION="$2"; shift 2 ;;
    --accept-noncommercial-model-license) ACCEPTED=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ "$ACCEPTED" -ne 1 ]]; then
  echo "Refusing model setup without --accept-noncommercial-model-license." >&2
  echo "Review the exact model snapshot licenses before proceeding." >&2
  exit 2
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Real worker setup currently requires Linux." >&2
  exit 2
fi

for tool in git nvidia-smi ffmpeg python3.12 python3.11; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing required command: $tool" >&2; exit 2; }
done

GPU_INFO="$(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader | paste -sd ';' -)"
echo "$GPU_INFO"
FFMPEG_LINE="$(ffmpeg -version | head -n 1)"
echo "$FFMPEG_LINE"
FFMPEG_VERSION="$(printf '%s' "$FFMPEG_LINE" | awk '{print $3}' | sed 's/[^0-9.].*$//')"
FFMPEG_MAJOR="${FFMPEG_VERSION%%.*}"
FFMPEG_MINOR_PART="${FFMPEG_VERSION#*.}"
FFMPEG_MINOR="${FFMPEG_MINOR_PART%%.*}"
if [[ ! "$FFMPEG_MAJOR" =~ ^[0-9]+$ || ! "$FFMPEG_MINOR" =~ ^[0-9]+$ ]] || \
   (( FFMPEG_MAJOR < 6 || (FFMPEG_MAJOR == 6 && FFMPEG_MINOR < 1) )); then
  echo "FFmpeg 6.1 or newer is required for the checked SheetSage2 setup; found $FFMPEG_VERSION" >&2
  exit 2
fi
mkdir -p "$RUNTIME_DIR/yue2" "$RUNTIME_DIR/sheetsage2"

YUE_REPO="$RUNTIME_DIR/yue2/YuE"
if [[ ! -d "$YUE_REPO/.git" ]]; then
  git clone https://github.com/multimodal-art-projection/YuE.git "$YUE_REPO"
fi
git -C "$YUE_REPO" fetch --tags --force origin
git -C "$YUE_REPO" checkout --detach "$YUE_REF"
ACTUAL_REF="$(git -C "$YUE_REPO" rev-parse HEAD)"

python3.12 -m venv "$RUNTIME_DIR/yue2/.venv"
"$RUNTIME_DIR/yue2/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
"$RUNTIME_DIR/yue2/.venv/bin/python" -m pip install "$YUE_REPO"

SHEET_MODEL="$RUNTIME_DIR/sheetsage2/model"
python3.11 -m venv "$RUNTIME_DIR/sheetsage2/.venv"
"$RUNTIME_DIR/sheetsage2/.venv/bin/python" -m pip install --upgrade pip
"$RUNTIME_DIR/sheetsage2/.venv/bin/python" -m pip install 'huggingface-hub==0.36.2'

YUE_MODEL_EFFECTIVE_REVISION="$YUE_MODEL_REVISION"
YUE_VAE_EFFECTIVE_REVISION="$YUE_VAE_REVISION"
SHEETSAGE2_EFFECTIVE_REVISION="$SHEETSAGE2_REVISION"

if [[ "$DOWNLOAD_MODELS" -eq 1 ]]; then
  RESOLVED_REVISIONS="$RUNTIME_DIR/resolved-model-revisions.env"
  YUE_MODEL_REVISION="$YUE_MODEL_REVISION" \
  YUE_VAE_REVISION="$YUE_VAE_REVISION" \
  SHEETSAGE2_REVISION="$SHEETSAGE2_REVISION" \
  SHEET_MODEL="$SHEET_MODEL" \
  RESOLVED_REVISIONS="$RESOLVED_REVISIONS" \
    "$RUNTIME_DIR/yue2/.venv/bin/python" - <<'PYMODELS'
import os
import re
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

api = HfApi()
resolved = {}
for repo_id, request_env, result_name, local_dir in (
    ("m-a-p/YuE2-3B", "YUE_MODEL_REVISION", "YUE_MODEL_EFFECTIVE_REVISION", None),
    ("m-a-p/YuE2-Vae", "YUE_VAE_REVISION", "YUE_VAE_EFFECTIVE_REVISION", None),
    (
        "m-a-p/SheetSage2",
        "SHEETSAGE2_REVISION",
        "SHEETSAGE2_EFFECTIVE_REVISION",
        os.environ["SHEET_MODEL"],
    ),
):
    requested = os.environ.get(request_env) or "main"
    info = api.model_info(repo_id, revision=requested)
    revision = info.sha
    if not revision or re.fullmatch(r"[0-9a-f]{40,64}", revision) is None:
        raise RuntimeError(f"Could not resolve an immutable revision for {repo_id}")
    path = snapshot_download(repo_id, revision=revision, local_dir=local_dir)
    print(f"downloaded {repo_id} requested={requested} resolved={revision} path={path}")
    resolved[result_name] = revision

receipt = Path(os.environ["RESOLVED_REVISIONS"])
receipt.write_text(
    "".join(f"{name}={value}\n" for name, value in sorted(resolved.items())),
    encoding="utf-8",
)
PYMODELS
  # The file contains only validated hexadecimal repository revisions.
  # shellcheck disable=SC1090
  source "$RESOLVED_REVISIONS"
  "$RUNTIME_DIR/sheetsage2/.venv/bin/python" -m pip install \
    'torch==2.8.0' 'torchaudio==2.8.0' \
    --index-url https://download.pytorch.org/whl/cu126
  "$RUNTIME_DIR/sheetsage2/.venv/bin/python" -m pip install -r "$SHEET_MODEL/requirements.txt"
else
  echo "Model files were not downloaded. Re-run with --download-models when ready."
fi

cat > "$RUNTIME_DIR/worker.env" <<EOF
YUE2_MUSIC_OS_ENGINE=local
YUE2_MUSIC_OS_DATA=$ROOT/var
YUE2_MUSIC_OS_MODEL_USE_SCOPE=noncommercial
YUE2_MUSIC_OS_GPU_WORKERS=1
YUE2_MUSIC_OS_YUE2_PYTHON=$RUNTIME_DIR/yue2/.venv/bin/python
YUE2_MUSIC_OS_YUE2_REPO=$YUE_REPO
YUE2_MUSIC_OS_YUE2_MODEL=m-a-p/YuE2-3B
YUE2_MUSIC_OS_YUE2_REVISION=$YUE_MODEL_EFFECTIVE_REVISION
YUE2_MUSIC_OS_YUE2_VAE=m-a-p/YuE2-Vae
YUE2_MUSIC_OS_YUE2_VAE_REVISION=$YUE_VAE_EFFECTIVE_REVISION
YUE2_MUSIC_OS_SHEETSAGE2_PYTHON=$RUNTIME_DIR/sheetsage2/.venv/bin/python
YUE2_MUSIC_OS_SHEETSAGE2_DIR=$SHEET_MODEL
YUE2_MUSIC_OS_SHEETSAGE2_MODEL=m-a-p/SheetSage2
YUE2_MUSIC_OS_SHEETSAGE2_REVISION=$SHEETSAGE2_EFFECTIVE_REVISION
YUE2_MUSIC_OS_SHEETSAGE2_BASE_MODEL=
EOF

DISK_FREE_KIB="$(df -Pk "$RUNTIME_DIR" | awk 'NR==2 {print $4}')"
YUE_PYTHON_VERSION="$($RUNTIME_DIR/yue2/.venv/bin/python -c 'import platform; print(platform.python_version())')"
SHEETSAGE2_PYTHON_VERSION="$($RUNTIME_DIR/sheetsage2/.venv/bin/python -c 'import platform; print(platform.python_version())')"

cat > "$RUNTIME_DIR/INSTALL_RECEIPT.txt" <<EOF
installed_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
host_kernel=$(uname -srvmo)
gpu_info=$GPU_INFO
ffmpeg_version=$FFMPEG_VERSION
disk_free_kib_after_install=$DISK_FREE_KIB
yue_python_version=$YUE_PYTHON_VERSION
sheetsage2_python_version=$SHEETSAGE2_PYTHON_VERSION
yue_requested_ref=$YUE_REF
yue_actual_commit=$ACTUAL_REF
download_models=$DOWNLOAD_MODELS
yue_model_requested_revision=${YUE_MODEL_REVISION:-main-not-downloaded}
yue_model_effective_revision=${YUE_MODEL_EFFECTIVE_REVISION:-un-pinned}
yue_vae_requested_revision=${YUE_VAE_REVISION:-main-not-downloaded}
yue_vae_effective_revision=${YUE_VAE_EFFECTIVE_REVISION:-un-pinned}
sheetsage2_requested_revision=${SHEETSAGE2_REVISION:-main-not-downloaded}
sheetsage2_effective_revision=${SHEETSAGE2_EFFECTIVE_REVISION:-un-pinned}
license_acknowledgement=noncommercial_public_weights_reviewed_by_operator
EOF

if [[ -z "$YUE_MODEL_EFFECTIVE_REVISION" || -z "$YUE_VAE_EFFECTIVE_REVISION" || -z "$SHEETSAGE2_EFFECTIVE_REVISION" ]]; then
  echo "WARNING: model files were not downloaded and one or more revisions remain unpinned." >&2
fi

cat <<EOF

Worker runtime prepared.
YuE code commit: $ACTUAL_REF
Environment file: $RUNTIME_DIR/worker.env

Next:
  source "$ROOT/.venv/bin/activate"
  set -a; source "$RUNTIME_DIR/worker.env"; set +a
  yue2-music-os doctor

Before claiming completion, fill docs/REAL_WORKER_ACCEPTANCE.md with measured evidence.
EOF
