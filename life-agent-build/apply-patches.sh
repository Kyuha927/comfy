#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?project root required}"
MAIN="$ROOT/app/src/main/java/com/lifeagent/unified/MainActivity.java"
INTENTS="$ROOT/app/src/main/java/com/lifeagent/unified/AppIntents.java"
python3 - "$MAIN" "$INTENTS" <<'PY'
from pathlib import Path
import sys
main = Path(sys.argv[1])
intents = Path(sys.argv[2])
text = main.read_text(encoding='utf-8')
text = text.replace('Settings.Secure.ENABLED_NOTIFICATION_LISTENERS', '"enabled_notification_listeners"')
text = text.replace('Settings.Secure.AUTOFILL_SERVICE', '"autofill_service"')
main.write_text(text, encoding='utf-8')
text = intents.read_text(encoding='utf-8')
text = text.replace('context.startActivity(new Intent(Settings.ACTION_AUTOFILL_SETTINGS));', 'context.startActivity(new Intent(Settings.ACTION_SETTINGS));')
intents.write_text(text, encoding='utf-8')
PY
grep -q '"enabled_notification_listeners"' "$MAIN"
grep -q '"autofill_service"' "$MAIN"
! grep -q 'ACTION_AUTOFILL_SETTINGS' "$INTENTS"
