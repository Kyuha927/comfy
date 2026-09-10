#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?extracted Android project root required}"

python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
debug_manifest = root / "app/src/debug/AndroidManifest.xml"
text = debug_manifest.read_text(encoding="utf-8")
needle = '''        <activity
            android:name=".CommercialSelfTestActivity"
            android:exported="true" />
'''
insert = needle + '''        <activity
            android:name=".CommercialStateSelfTestActivity"
            android:exported="true" />
'''
if needle not in text:
    raise SystemExit("PATCH_MISS:debug_manifest_self_test")
debug_manifest.write_text(text.replace(needle, insert, 1), encoding="utf-8")
PY

grep -q 'CommercialStateSelfTestActivity' "$ROOT/app/src/debug/AndroidManifest.xml"
grep -q 'FINAL=PASS' "$ROOT/app/src/debug/java/com/lifeagent/unified/CommercialSelfTestActivity.java"
grep -q 'backup_state_recovered' "$ROOT/app/src/debug/java/com/lifeagent/unified/CommercialStateSelfTestActivity.java"
