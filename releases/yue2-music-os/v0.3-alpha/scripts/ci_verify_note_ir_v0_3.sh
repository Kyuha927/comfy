#!/usr/bin/env bash
set -euo pipefail

: "${TESTED_SOURCE_COMMIT:?TESTED_SOURCE_COMMIT is required}"
: "${CI_RUN_ID:?CI_RUN_ID is required}"
: "${CI_RUN_ATTEMPT:?CI_RUN_ATTEMPT is required}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p validation

python -m pip install --disable-pip-version-check --upgrade pip setuptools wheel build
python -m pip install --disable-pip-version-check -e '.[dev]'
python -m pip check

python -m compileall -q src tests examples
node --check src/yue2_music_os/static/app.js
node --check src/yue2_music_os/static/note-editor.js
bash -n scripts/*.sh
python examples/basic_pitch_command_provider.py --help >/dev/null

pytest \
  --cov=yue2_music_os \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=json:validation/coverage.json \
  --cov-report=xml:validation/coverage.xml \
  --cov-fail-under=80 \
  --junitxml=validation/pytest.xml \
  | tee validation/pytest.txt

./scripts/smoke.sh | tee validation/smoke.txt
grep -q 'SMOKE PASS' validation/smoke.txt

if grep -RIlE 'BEGIN ([A-Z ]+ )?PRIVATE KEY' \
  --exclude-dir=.git --exclude-dir=.venv --exclude='*.md' . | grep -q .; then
  echo 'Private key material detected in the release tree.' >&2
  exit 1
fi
if find . -type l -print -quit | grep -q .; then
  echo 'Symlinks are not permitted in the release tree.' >&2
  exit 1
fi

rm -rf dist build src/*.egg-info
python -m build --wheel --sdist | tee validation/build.txt

python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import stat
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

root = Path('.').resolve()
dist = root / 'dist'
validation = root / 'validation'
wheel = next(dist.glob('yue2_music_os-0.3.0a1-*.whl'))
sdist = next(dist.glob('yue2_music_os-0.3.0a1.tar.gz'))

with zipfile.ZipFile(wheel) as package:
    wheel_members = set(package.namelist())
required_wheel = {
    'yue2_music_os/note_ir.py',
    'yue2_music_os/note_providers.py',
    'yue2_music_os/note_workspace.py',
    'yue2_music_os/static/note-editor.html',
    'yue2_music_os/static/note-editor.css',
    'yue2_music_os/static/note-editor.js',
}
missing = sorted(required_wheel - wheel_members)
if missing:
    raise SystemExit('wheel missing: ' + ', '.join(missing))

with tarfile.open(sdist, 'r:gz') as package:
    sdist_members = set(package.getnames())
required_suffixes = {
    'src/yue2_music_os/note_ir.py',
    'src/yue2_music_os/note_providers.py',
    'src/yue2_music_os/note_workspace.py',
    'docs/NOTE_IR.md',
    'HANDOFF.md',
}
for suffix in required_suffixes:
    if not any(name.endswith(suffix) for name in sdist_members):
        raise SystemExit(f'sdist missing: {suffix}')

coverage = json.loads((validation / 'coverage.json').read_text(encoding='utf-8'))
coverage_percent = round(float(coverage['totals']['percent_covered']), 2)
if coverage_percent < 80:
    raise SystemExit(f'coverage below gate: {coverage_percent}')

suite = ET.parse(validation / 'pytest.xml').getroot()
tests = int(suite.attrib.get('tests', 0))
failures = int(suite.attrib.get('failures', 0))
errors = int(suite.attrib.get('errors', 0))
skipped = int(suite.attrib.get('skipped', 0))
if failures or errors:
    raise SystemExit('pytest XML contains failures or errors')

def describe(path: Path) -> dict[str, object]:
    return {
        'name': path.name,
        'size_bytes': path.stat().st_size,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }

status = {
    'release': 'yue2-music-os-v0.3-alpha',
    'branch': 'yue2-music-os-note-ir-free-v0.3-dev-20260916',
    'tested_source_commit': os.environ['TESTED_SOURCE_COMMIT'],
    'ci_run_id': int(os.environ['CI_RUN_ID']),
    'ci_run_attempt': int(os.environ['CI_RUN_ATTEMPT']),
    'verdict': 'PASS_CONTROLLER_NOTE_IR_REAL_MULTI_INSTRUMENT_MODELS_PENDING',
    'tests': {
        'passed': tests - failures - errors - skipped,
        'failed': failures,
        'errors': errors,
        'skipped': skipped,
        'branch_coverage_percent': coverage_percent,
        'minimum_percent': 80,
    },
    'checks': {
        'existing_v0_2_regression_suite': 'PASS',
        'note_ir_stable_ids_and_fusion': 'PASS',
        'individual_note_edit_and_revision_history': 'PASS',
        'provider_command_no_shell_and_timeout': 'PASS',
        'api_token_round_trip': 'PASS',
        'midi_export': 'PASS',
        'javascript_syntax': 'PASS',
        'http_smoke': 'PASS',
        'wheel_required_members': 'PASS',
        'sdist_required_members': 'PASS',
    },
    'artifacts': [describe(wheel), describe(sdist)],
    'not_run': [
        'real YourMT3-family full-mix inference',
        'real BS-RoFormer stem separation',
        'real Basic Pitch target-Mac inference',
        'polyphonic waveform single-note repair',
        'paid provider calls',
        'representative-song human listening acceptance',
    ],
}
(root / 'RELEASE_STATUS.json').write_text(
    json.dumps(status, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
provenance = {
    'base_release': 'releases/yue2-music-os/v0.2-alpha',
    'base_verified_commit': '646b118c48693045ad06bf70f17e3c17d72443b5',
    'overlay_sha256': os.environ.get('OVERLAY_SHA256'),
    'tested_source_commit': os.environ['TESTED_SOURCE_COMMIT'],
    'ci_run_id': int(os.environ['CI_RUN_ID']),
    'construction': 'copy verified v0.2 release, apply path-confined checksum-pinned v0.3 overlay',
}
(root / 'BUILD_PROVENANCE.json').write_text(
    json.dumps(provenance, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)

source_zip = dist / 'yue2-music-os-v0.3-alpha-source.zip'
excluded_roots = {'dist', 'validation', '.pytest_cache', 'build', 'var', 'runtime'}
source_files: list[tuple[Path, Path]] = []
for path in sorted(root.rglob('*'), key=lambda item: item.as_posix()):
    if not path.is_file() or path.is_symlink():
        continue
    rel = path.relative_to(root)
    if rel.parts and rel.parts[0] in excluded_roots:
        continue
    if '__pycache__' in rel.parts or path.suffix in {'.pyc', '.pyo'}:
        continue
    source_files.append((path, rel))
with zipfile.ZipFile(source_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as output:
    for path, rel in source_files:
        info = zipfile.ZipInfo(
            (Path('yue2-music-os-v0.3-alpha') / rel).as_posix(),
            date_time=(2026, 9, 16, 0, 0, 0),
        )
        info.external_attr = (stat.S_IMODE(path.stat().st_mode) & 0xFFFF) << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        output.writestr(
            info,
            path.read_bytes(),
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )

distribution_report = {
    'wheel': describe(wheel),
    'sdist': describe(sdist),
    'source_zip': describe(source_zip),
    'wheel_member_count': len(wheel_members),
    'sdist_member_count': len(sdist_members),
}
(validation / 'distribution-report.json').write_text(
    json.dumps(distribution_report, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
PY

python - <<'PY'
import hashlib
from pathlib import Path

root = Path('.')
excluded = {'.coverage', 'SHA256SUMS.txt'}
lines = []
for path in sorted(root.rglob('*'), key=lambda item: item.as_posix()):
    if not path.is_file() or path.is_symlink():
        continue
    rel = path.relative_to(root)
    if path.name in excluded or '__pycache__' in rel.parts or path.suffix in {'.pyc', '.pyo'}:
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    lines.append(f'{digest}  {rel.as_posix()}\n')
(root / 'SHA256SUMS.txt').write_text(''.join(lines), encoding='utf-8')
PY
sha256sum -c SHA256SUMS.txt
