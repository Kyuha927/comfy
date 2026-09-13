#!/usr/bin/env bash
set -euo pipefail

python - <<'PY_PATCH'
from pathlib import Path

source = Path('.capability-bootstrap/apply.sh').read_text(encoding='utf-8')
source = source.replace(
    'rm -f .github/workflows/capability-bootstrap.yml',
    ': # workflow files are finalized by the authenticated GitHub connector after the non-workflow gate commit',
    1,
)
needle = 'python -m compileall -q production-skill-os/router production-skill-os/adapters production-skill-os/tests\n\npython - <<\'PY\'\n'
replacement = 'python -m compileall -q production-skill-os/router production-skill-os/adapters production-skill-os/tests\n\ngit restore --source=HEAD -- .github/workflows/capability-bootstrap.yml .github/workflows/production-skill-os.yml\n\npython - <<\'PY\'\n'
if needle not in source:
    raise SystemExit('BLOCKED_BOOTSTRAP_PATCH_TARGET_MISSING')
source = source.replace(needle, replacement, 1)
Path('/tmp/apply-nonworkflow-gate.sh').write_text(source, encoding='utf-8')
PY_PATCH

bash /tmp/apply-nonworkflow-gate.sh
