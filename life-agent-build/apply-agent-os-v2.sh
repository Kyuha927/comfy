#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?project root required}"
BUILD="$ROOT/app/build.gradle"
MANIFEST="$ROOT/app/src/main/AndroidManifest.xml"
STRINGS="$ROOT/app/src/main/res/values/strings.xml"
LISTENER="$ROOT/app/src/main/java/com/lifeagent/unified/UnifiedNotificationListener.java"

python3 - "$BUILD" "$MANIFEST" "$STRINGS" "$LISTENER" <<'PY'
from pathlib import Path
import re
import sys

build, manifest, strings, listener = map(Path, sys.argv[1:])

# Keep the same package so the Agent OS build upgrades the integrated prototype.
text = build.read_text(encoding='utf-8')
text = re.sub(r'(?m)^\s*versionCode\s+\d+\s*$', '        versionCode 200', text)
text = re.sub(r"(?m)^\s*versionName\s+['\"][^'\"]+['\"]\s*$", "        versionName '2.0.0-agent-os-alpha'", text)
build.write_text(text, encoding='utf-8')

m = manifest.read_text(encoding='utf-8')
if 'AgentEntryActivity' not in m:
    block = r'''
        <activity
            android:name=".AgentEntryActivity"
            android:excludeFromRecents="true"
            android:exported="true"
            android:noHistory="true"
            android:theme="@android:style/Theme.Translucent.NoTitleBar">
            <intent-filter>
                <action android:name="android.intent.action.SEND" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="text/plain" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.SEND" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="image/*" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.SEND" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="application/pdf" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.PROCESS_TEXT" />
                <category android:name="android.intent.category.DEFAULT" />
                <data android:mimeType="text/plain" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="lifeagent" android:host="command" />
            </intent-filter>
        </activity>

        <activity
            android:name=".GeneralTaskActivity"
            android:exported="false" />

        <service
            android:name=".LifeAgentTileService"
            android:exported="true"
            android:icon="@mipmap/ic_launcher"
            android:label="Life Agent"
            android:permission="android.permission.BIND_QUICK_SETTINGS_TILE">
            <intent-filter>
                <action android:name="android.service.quicksettings.action.QS_TILE" />
            </intent-filter>
            <meta-data
                android:name="android.service.quicksettings.ACTIVE_TILE"
                android:value="true" />
        </service>
'''
    marker = '</application>'
    if marker not in m:
        raise SystemExit('AndroidManifest.xml has no </application> marker')
    m = m.replace(marker, block + '\n    ' + marker, 1)
manifest.write_text(m, encoding='utf-8')

if strings.exists():
    s = strings.read_text(encoding='utf-8')
    s = re.sub(r'(<string\s+name="app_name">).*?(</string>)', r'\1Life Agent\2', s, count=1)
    strings.write_text(s, encoding='utf-8')

# Feed notification events into the generic Context/Recipe layer without replacing
# the existing insurance and streaming-specific behavior.
if listener.exists():
    s = listener.read_text(encoding='utf-8')
    if 'AgentOsCore.Events.captureNotification' not in s:
        pattern = re.compile(r'(onNotificationPosted\s*\(\s*StatusBarNotification\s+(\w+)\s*\)\s*\{)')
        match = pattern.search(s)
        if not match:
            raise SystemExit('UnifiedNotificationListener.onNotificationPosted signature not found')
        variable = match.group(2)
        insertion = match.group(1) + '\n        AgentOsCore.Events.captureNotification(this, ' + variable + ');'
        s = s[:match.start()] + insertion + s[match.end():]
        listener.write_text(s, encoding='utf-8')
else:
    raise SystemExit('UnifiedNotificationListener.java not found')
PY

grep -q "versionCode 200" "$BUILD"
grep -q "versionName '2.0.0-agent-os-alpha'" "$BUILD"
grep -q 'AgentEntryActivity' "$MANIFEST"
grep -q 'LifeAgentTileService' "$MANIFEST"
grep -q 'AgentOsCore.Events.captureNotification' "$LISTENER"
grep -q 'class AgentOsCore' "$ROOT/app/src/main/java/com/lifeagent/unified/AgentOsCore.java"
grep -q 'class MainActivity' "$ROOT/app/src/main/java/com/lifeagent/unified/MainActivity.java"
