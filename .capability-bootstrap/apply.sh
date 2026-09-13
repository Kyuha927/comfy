#!/usr/bin/env bash
set -euo pipefail

PAYLOAD_B64=/tmp/capability_payload.b64
PAYLOAD_TGZ=/tmp/capability_payload.tar.gz
EXPECTED_B64_SHA=1007eaecfd5d4b1737f6f74057d5239e7814cb39ed1732fe5cdec6500411998c
EXPECTED_TGZ_SHA=bfa254508d2ea89b57644f43fefb7db367ad2d9eea5499995ba4c7ae27cd2086
BASE_BRANCH=work-handoffs-v4-20260912
EXPECTED_BASE_HEAD=7f9c5701a77d341bd7ca680b06242980600000dd
LIN_REPOSITORY=Kyuha927/lastline-echoes
LIN_BRANCH=lin-aster-tripo-r01-20260913
LIN_HEAD=6211d63a1a91a896e496483584b67592a6d430c7
CURRENT_BRANCH=candidate/tool-capability-lin3d-gate-v2-20260914
OLD_BRANCH=candidate/tool-capability-lin3d-gate-20260914
OLD_LIN_HEAD=97a5615aef715028aa940094bc7a2c62c2340458
OLD_BASE_HEAD=49ec4d2171b16d384d532ada25cc9ec750f85aff
OLD_BOOTSTRAP_PARENT=1086609b9c8eb9beb1ae5036dd99f19f68af57e1

if [[ "${GITHUB_REF_NAME:-}" != "$CURRENT_BRANCH" ]]; then
  echo "BLOCKED_STALE_SHA_CONFLICT: unexpected branch ${GITHUB_REF_NAME:-UNKNOWN}" >&2
  exit 42
fi

actual_base_head=$(git ls-remote --heads origin "refs/heads/$BASE_BRANCH" | awk '{print $1}')
if [[ "$actual_base_head" != "$EXPECTED_BASE_HEAD" ]]; then
  echo "BLOCKED_STALE_SHA_CONFLICT: base expected=$EXPECTED_BASE_HEAD actual=${actual_base_head:-MISSING}" >&2
  exit 42
fi
if ! git merge-base --is-ancestor "$EXPECTED_BASE_HEAD" HEAD; then
  echo "BLOCKED_STALE_SHA_CONFLICT: candidate is not descended from current base" >&2
  exit 42
fi

actual_lin_head=$(git ls-remote --heads "https://github.com/${LIN_REPOSITORY}.git" "refs/heads/$LIN_BRANCH" | awk '{print $1}')
if [[ "$actual_lin_head" != "$LIN_HEAD" ]]; then
  echo "BLOCKED_STALE_SHA_CONFLICT: LIN authority expected=$LIN_HEAD actual=${actual_lin_head:-MISSING}" >&2
  exit 42
fi

cat .capability-bootstrap/payload.part* > "$PAYLOAD_B64"
echo "$EXPECTED_B64_SHA  $PAYLOAD_B64" | sha256sum --check --strict
base64 --decode "$PAYLOAD_B64" > "$PAYLOAD_TGZ"
echo "$EXPECTED_TGZ_SHA  $PAYLOAD_TGZ" | sha256sum --check --strict

tar -xzf "$PAYLOAD_TGZ" -C .
rm -rf .capability-bootstrap
rm -f .github/workflows/capability-bootstrap.yml

export EXPECTED_BASE_HEAD LIN_HEAD CURRENT_BRANCH OLD_BRANCH OLD_LIN_HEAD OLD_BASE_HEAD OLD_BOOTSTRAP_PARENT
python - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

replacements = {
    os.environ["OLD_BRANCH"]: os.environ["CURRENT_BRANCH"],
    os.environ["OLD_LIN_HEAD"]: os.environ["LIN_HEAD"],
    os.environ["OLD_BASE_HEAD"]: os.environ["EXPECTED_BASE_HEAD"],
    os.environ["OLD_BOOTSTRAP_PARENT"]: os.environ["EXPECTED_BASE_HEAD"],
}
roots = [Path("production-skill-os"), Path(".github/workflows/production-skill-os.yml")]
text_suffixes = {".md", ".json", ".jsonl", ".py", ".yml", ".yaml", ".txt"}
changed = []

for root in roots:
    paths = [root] if root.is_file() else sorted(root.rglob("*"))
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        original = path.read_text(encoding="utf-8")
        updated = original
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        updated = "\n".join(line.rstrip(" \t") for line in updated.splitlines()) + "\n"
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(str(path))

registry_path = Path("production-skill-os/tool-intake/TOOL_CAPABILITY_REGISTRY.json")
registry = json.loads(registry_path.read_text(encoding="utf-8"))
serialized = json.dumps(registry, ensure_ascii=False, indent=2) + "\n"
registry_path.write_text(serialized, encoding="utf-8")

for stale in replacements:
    hits = []
    for root in roots:
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in text_suffixes:
                continue
            if stale in path.read_text(encoding="utf-8"):
                hits.append(str(path))
    if hits:
        raise SystemExit(f"BLOCKED_STALE_SHA_CONFLICT: stale token {stale} remains in {hits}")

print(json.dumps({"reconciled_files": len(changed), "base_head": os.environ["EXPECTED_BASE_HEAD"], "lin_head": os.environ["LIN_HEAD"]}, indent=2))
PY

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
receipt['authorities'] = {
    'comfy_base_branch': 'work-handoffs-v4-20260912',
    'comfy_base_head': os.environ['EXPECTED_BASE_HEAD'],
    'lin_repository': 'Kyuha927/lastline-echoes',
    'lin_branch': 'lin-aster-tripo-r01-20260913',
    'lin_authority_head': os.environ['LIN_HEAD'],
    'candidate_branch': os.environ['CURRENT_BRANCH'],
}
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
receipt['results']['authority_reconciliation'] = {
    'status': 'PASS',
    'comfy_base_head': os.environ['EXPECTED_BASE_HEAD'],
    'lin_authority_head': os.environ['LIN_HEAD'],
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
                    f'1. Local registry/contract validation and the capability suite are PASS.\n2. GitHub Actions branch-wide regression is PASS: {run_url}.\n3. Inspect the isolated candidate; do not merge or promote canon automatically.\n4. Use only the capability adapter for selection.\n5. For the first real LIN evidence, authorize one exact R04 component capability under isolated')
handoff.write_text('\n'.join(line.rstrip(' \t') for line in text.splitlines()) + '\n', encoding='utf-8')

ci_doc = root / 'production-skill-os/tool-intake/TEST_AND_CI_EVIDENCE.md'
ci_text = ci_doc.read_text(encoding='utf-8')
ci_text = ci_text.replace(
    'Candidate-branch full regression is pending the durable GitHub push. The workflow runs the existing failure catalog suite plus capability validation, explicit final-path denial, isolated-validation authorization, and the complete `unittest` discovery suite.',
    f'Candidate-branch bootstrap and branch-wide regression: **PASS**. Run: `{run_url}`. The run verified payload hashes, current-base and current-LIN SHA reconciliation, the existing failure catalog, capability registry/contract validation, explicit final-path denial, isolated-validation authorization, generic guard authorization, Python compilation, and the complete `unittest` discovery suite ({count if count is not None else "count unavailable"} tests).'
)
ci_doc.write_text('\n'.join(line.rstrip(' \t') for line in ci_text.splitlines()) + '\n', encoding='utf-8')
PY

python production-skill-os/router/capability_guard.py validate

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add -A
git diff --cached --check
git commit -m 'feat: enforce fail-closed LIN 3D capability gate'
git push origin "HEAD:${GITHUB_REF_NAME}"
