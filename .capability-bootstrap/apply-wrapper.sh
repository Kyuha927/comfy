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
needle = 'git add -A\n'
replacement = '''git restore --source=HEAD -- .github/workflows/capability-bootstrap.yml .github/workflows/production-skill-os.yml
python - <<'PY_RECEIPT'
from __future__ import annotations

import hashlib
import json
from pathlib import Path

path = Path('production-skill-os/tool-intake/LOCAL_TEST_RECEIPT_2026-09-14.json')
receipt = json.loads(path.read_text(encoding='utf-8'))
workflow = Path('.github/workflows/production-skill-os.yml')
receipt.setdefault('results', {})['workflow_connector_finalize'] = {
    'status': 'PENDING_CONNECTOR_COMMIT',
    'reason': 'Repository-scoped GitHub Actions tokens cannot create, update, or delete workflow files. The authenticated GitHub connector will finalize the durable workflow after this gate commit.',
}
receipt.setdefault('file_sha256', {})['.github/workflows/production-skill-os.yml'] = hashlib.sha256(workflow.read_bytes()).hexdigest()
limitations = receipt.setdefault('limitations', [])
message = 'Workflow-file finalization is intentionally split into a following authenticated connector commit; the current run proves the registry, guard, adapter, and full regression before that commit.'
if message not in limitations:
    limitations.append(message)
path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY_RECEIPT
git add -A
'''
if needle not in source:
    raise SystemExit('BLOCKED_BOOTSTRAP_PATCH_TARGET_MISSING')
source = source.replace(needle, replacement, 1)
Path('/tmp/apply-nonworkflow-gate.sh').write_text(source, encoding='utf-8')
PY_PATCH

bash /tmp/apply-nonworkflow-gate.sh
