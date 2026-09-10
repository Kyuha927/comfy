#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?project root required}"
FILE="$ROOT/app/src/main/java/com/lifeagent/unified/FeatureActivity.java"
python3 - "$FILE" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
needle = "import android.content.Intent;\n"
addition = "import android.content.Intent;\nimport android.graphics.Color;\n"
if "import android.graphics.Color;" not in text:
    if needle not in text:
        raise SystemExit("expected import anchor missing")
    text = text.replace(needle, addition, 1)
path.write_text(text, encoding="utf-8")
PY
grep -q '^import android.graphics.Color;' "$FILE"
