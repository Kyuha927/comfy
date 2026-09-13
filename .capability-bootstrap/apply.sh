#!/usr/bin/env bash
set -euo pipefail

PAYLOAD_B64=/tmp/capability_payload.b64
PAYLOAD_TGZ=/tmp/capability_payload.tar.gz
EXPECTED_B64_SHA=1007eaecfd5d4b1737f6f74057d5239e7814cb39ed1732fe5cdec6500411998c
EXPECTED_TGZ_SHA=bfa254508d2ea89b57644f43fefb7db367ad2d9eea5499995ba4c7ae27cd2086
LIN_HEAD=97a5615aef715028aa940094bc7a2c62c2340458

cat .capability-bootstrap/payload.part* > "$PAYLOAD_B64"
echo "$EXPECTED_B64_SHA  $PAYLOAD_B64" | sha256sum --check --strict
base64 --decode "$PAYLOAD_B64" > "$PAYLOAD_TGZ"
echo "$EXPECTED_TGZ_SHA  $PAYLOAD_TGZ" | sha256sum --check --strict

tar -xzf "$PAYLOAD_TGZ" -C .
rm -rf .capability-bootstrap
rm -f .github/workflows/capability-bootstrap.yml

python production-skill-os/router/skill_router.py validate
python production-skill-os/router/capability_guard.py validate

set +e
python production-skill-os/adapters/authorize_capability.py \
  --capability-id cap.tripo.h31.head_component_ultra \
  --version v3.1-20260211 \
  --scope LIN_3D_FINAL \
  --lin-authority-head "$LIN_HEAD" > /tmp/lin-final-deny.json
final_code=$?
set -e
test "$final_code" -eq 2
grep -q 'BLOCKED_CAPABILITY_NOT_VERIFIED_FOR_LIN_3D' /tmp/lin-final-deny.json

python production-skill-os/adapters/authorize_capability.py \
  --capability-id cap.tripo.h31.head_component_ultra \
  --version v3.1-20260211 \
  --scope LIN_3D_VALIDATION \
  --lin-authority-head "$LIN_HEAD" \
  --isolated-workspace \
  --no-production-mutation \
  --no-canon-mutation > /tmp/lin-validation-allow.json
grep -q 'CAPABILITY_AUTHORIZED' /tmp/lin-validation-allow.json
grep -q '"production_3d_mutation_allowed": false' /tmp/lin-validation-allow.json

python production-skill-os/adapters/authorize_capability.py \
  --capability-id cap.production_skill_os.fail_closed_selection \
  --version 1.0.0-candidate.20260914 \
  --scope GENERIC_PRODUCTION > /tmp/generic-guard-allow.json
grep -q 'CAPABILITY_AUTHORIZED' /tmp/generic-guard-allow.json

python -m unittest discover -s production-skill-os/tests -v 2>&1 | tee /tmp/production-skill-os-tests.log
python -m compileall -q production-skill-os/router production-skill-os/adapters production-skill-os/tests

python - <<'PY'
from __future__ import annotations
import hashlib
import json
import os
import platform
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

root = Path('.')
receipt_path = root / 'production-skill-os/tool-intake/LOCAL_TEST_RECEIPT_2026-09-14.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
log = Path('/tmp/production-skill-os-tests.log').read_text(encoding='utf-8')
match = re.search(r'Ran (\d+) tests?', log)
count = int(match.group(1)) if match else None
kst = timezone(timedelta(hours=9))
now = datetime.now(kst).isoformat(timespec='seconds')
run_url = f"{os.environ.get('GITHUB_SERVER_URL','https://github.com')}/{os.environ.get('GITHUB_REPOSITORY','Kyuha927/comfy')}/actions/runs/{os.environ.get('GITHUB_RUN_ID','UNKNOWN')}"
tracked = [
    'production-skill-os/tool-intake/TOOL_CAPABILITY_REGISTRY.json',
    'production-skill-os/tool-intake/SELECTION_CONTRACT.json',
    'production-skill-os/router/capability_guard.py',
    'production-skill-os/adapters/authorize_capability.py',
    'production-skill-os/tests/test_tool_capability_guard.py',
    'production-skill-os/tests/test_blender_character_route.py',
    'production-skill-os/skills/blender-character-tripo-astra/SKILL.md',
    'production-skill-os/docs/CONSUMER_INTEGRATION.md',
    '.github/workflows/production-skill-os.yml',
]
receipt['receipt_id'] = f"GITHUB_ACTIONS_CAPABILITY_GATE_{os.environ.get('GITHUB_RUN_ID','UNKNOWN')}"
receipt['observed_at'] = now
receipt['environment'] = {
    'execution': 'GitHub Actions isolated ubuntu-latest candidate branch',
    'python': platform.python_version(),
    'workflow_run_url': run_url,
    'workflow_run_id': os.environ.get('GITHUB_RUN_ID'),
    'trigger_commit': os.environ.get('GITHUB_SHA'),
    'production_3d_mutation': False,
    'canon_mutation': False,
    'tripo_paid_action': False,
    'blender_scene_opened': False,
}
receipt['results']['branch_wide_unit_tests'] = {
    'status': 'PASS',
    'tests': count,
    'failures': 0,
    'errors': 0,
    'command': 'python -m unittest discover -s production-skill-os/tests -v',
}
receipt['results']['payload_integrity'] = {
    'status': 'PASS',
    'base64_sha256': '1007eaecfd5d4b1737f6f74057d5239e7814cb39ed1732fe5cdec6500411998c',
    'tar_gz_sha256': 'bfa254508d2ea89b57644f43fefb7db367ad2d9eea5499995ba4c7ae27cd2086',
}
receipt['file_sha256'] = {
    item: hashlib.sha256((root / item).read_bytes()).hexdigest()
    for item in tracked
}
receipt['limitations'] = [
    'This receipt validates registry, guard, adapter, policy, and regression behavior only.',
    'It does not prove Tripo output quality, live Bridge transport, selected-LIN same-scene evidence, ART_MASTER, Mobile Hero, or real-device readiness.',
]
receipt['canon_promotion_allowed'] = False
receipt['automatic_merge_allowed'] = False
receipt['user_final_approval_required'] = True
receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

handoff = root / 'production-skill-os/tool-intake/CURRENT_HANDOFF.md'
text = handoff.read_text(encoding='utf-8')
text = text.replace('STATUS=CANDIDATE_LOCAL_TESTED_GITHUB_PUSH_PENDING', 'STATUS=CANDIDATE_GITHUB_ACTIONS_TESTED_READY_FOR_REVIEW')
text = text.replace('1. Local registry/contract validation and the new 15-test suite are PASS.\n2. Push the candidate implementation and run the complete branch-wide GitHub Actions suite.\n3. Inspect the draft candidate PR and CI.\n4. Use only the capability adapter for selection.\n5. For the first real LIN evidence, authorize one exact R04 component capability under isolated',
                    f'1. Local registry/contract validation and the new 15-test suite are PASS.\n2. GitHub Actions branch-wide regression is PASS: {run_url}.\n3. Inspect the draft candidate PR; do not merge or promote canon automatically.\n4. Use only the capability adapter for selection.\n5. For the first real LIN evidence, authorize one exact R04 component capability under isolated')
handoff.write_text(text, encoding='utf-8')

ci_doc = root / 'production-skill-os/tool-intake/TEST_AND_CI_EVIDENCE.md'
ci_text = ci_doc.read_text(encoding='utf-8')
ci_text = ci_text.replace(
    'Candidate-branch full regression is pending the durable GitHub push. The workflow runs the existing failure catalog suite plus capability validation, explicit final-path denial, isolated-validation authorization, and the complete `unittest` discovery suite.',
    f'Candidate-branch bootstrap and branch-wide regression: **PASS**. Run: `{run_url}`. The run verified payload hashes, the existing failure catalog, capability registry/contract validation, explicit final-path denial, isolated-validation authorization, generic guard authorization, Python compilation, and the complete `unittest` discovery suite ({count if count is not None else "count unavailable"} tests).'
)
ci_doc.write_text(ci_text, encoding='utf-8')
PY

python production-skill-os/router/capability_guard.py validate

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add -A
git diff --cached --check
git commit -m 'feat: enforce fail-closed LIN 3D capability gate'
git push origin "HEAD:${GITHUB_REF_NAME}"
