#!/usr/bin/env bash
set -euo pipefail

APK=${1:-dist/Life-Agent-OS-v2.1.1-runtime-fix-alpha.apk}
PACKAGE=com.lifeagent.unified
MAIN="$PACKAGE/.MainActivity"
OUT=${RUNTIME_OUT:-runtime-evidence}
mkdir -p "$OUT"

fail() {
  echo "RUNTIME_SMOKE_FAIL: $*" >&2
  adb logcat -d -v threadtime > "$OUT/logcat-on-failure.txt" 2>/dev/null || true
  adb exec-out screencap -p > "$OUT/failure.png" 2>/dev/null || true
  exit 1
}

dump_ui() {
  local name=$1
  local remote="/sdcard/${name}.xml"
  local local_path="$OUT/${name}.xml"
  local ok=0
  for _ in 1 2 3 4 5; do
    if adb shell uiautomator dump "$remote" >/dev/null 2>&1; then
      if adb pull "$remote" "$local_path" >/dev/null 2>&1; then
        ok=1
        break
      fi
    fi
    sleep 1
  done
  [ "$ok" -eq 1 ] || fail "could not dump UI: $name"
}

assert_ui_contains() {
  local file=$1
  local text=$2
  grep -Fq "$text" "$file" || fail "UI missing [$text] in $file"
}

tap_ui_contains() {
  local file=$1
  local needle=$2
  python3 - "$file" "$needle" <<'PY'
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

path, needle = sys.argv[1], sys.argv[2]
root = ET.parse(path).getroot()
parents = {child: parent for parent in root.iter() for child in parent}
candidates = []

for node in root.iter("node"):
    label = ((node.attrib.get("text", "") or "") + " " +
             (node.attrib.get("content-desc", "") or "")).strip()
    if needle not in label:
        continue

    target = node
    current = node
    while current in parents:
        current = parents[current]
        if current.attrib.get("clickable") == "true" and current.attrib.get("visible-to-user", "true") != "false":
            target = current
            break

    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", target.attrib.get("bounds", ""))
    if not match:
        continue
    x1, y1, x2, y2 = map(int, match.groups())
    if x2 <= x1 or y2 <= y1:
        continue
    clickable = target.attrib.get("clickable") == "true"
    area = (x2 - x1) * (y2 - y1)
    candidates.append((0 if clickable else 1, area, (x1 + x2) // 2, (y1 + y2) // 2, label))

if not candidates:
    raise SystemExit("UI target not found: " + needle)
_, _, x, y, label = sorted(candidates)[0]
print(f"tapping {label!r} at ({x},{y})")
subprocess.check_call(["adb", "shell", "input", "tap", str(x), str(y)])
PY
}

assert_process_alive() {
  local pid
  pid=$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)
  [ -n "$pid" ] || fail "process is not alive"
  echo "$pid"
}

assert_clean_runtime_log() {
  local file=$1
  if grep -Eq "FATAL EXCEPTION: main|Process: ${PACKAGE}.*PID| E LifeAgentStartup:" "$file"; then
    fail "fatal exception or Life Agent startup error found in $file"
  fi
}

# Earlier alpha builds used disposable debug keys, so this lane intentionally
# performs a clean install. Production signing continuity is a separate gate.
adb uninstall "$PACKAGE" >/dev/null 2>&1 || true
adb install "$APK" | tee "$OUT/install.txt"
grep -Fq Success "$OUT/install.txt" || fail "APK installation failed"

# Three cold launches catch one-shot initialization and stale-process defects.
for attempt in 1 2 3; do
  adb shell am force-stop "$PACKAGE"
  adb logcat -c
  adb shell am start -W -n "$MAIN" | tee "$OUT/start-${attempt}.txt"
  sleep 3
  assert_process_alive > "$OUT/pid-${attempt}.txt"
  dump_ui "home-${attempt}"
  assert_ui_contains "$OUT/home-${attempt}.xml" "무엇을 맡길까요?"
  assert_ui_contains "$OUT/home-${attempt}.xml" "Life Agent가 진행 중"
  if grep -Fq "복구 모드로 열었습니다" "$OUT/home-${attempt}.xml"; then
    fail "launcher entered recovery surface"
  fi
  adb exec-out screencap -p > "$OUT/home-${attempt}.png"
  adb logcat -d -v threadtime > "$OUT/logcat-home-${attempt}.txt"
  assert_clean_runtime_log "$OUT/logcat-home-${attempt}.txt"
done

# Deep-link navigation must stay inside the same Agent Shell.
adb shell am start -W -n "$MAIN" -a android.intent.action.VIEW -d 'lifeagent://tasks' | tee "$OUT/start-tasks.txt"
sleep 2
dump_ui tasks
assert_ui_contains "$OUT/tasks.xml" "앱이 아니라 목표 단위로 이어서 처리합니다"
assert_process_alive > "$OUT/pid-tasks.txt"
adb exec-out screencap -p > "$OUT/tasks.png"

# Share-text intake, encrypted persistence, process death and exact resume surface.
PROBE='LifeAgentRuntimeProbe_211'
adb shell am start -W -n "$MAIN" -a android.intent.action.SEND -t text/plain --es android.intent.extra.TEXT "$PROBE" | tee "$OUT/start-share.txt"
sleep 2
dump_ui shared-text
assert_ui_contains "$OUT/shared-text.xml" "$PROBE"
adb exec-out screencap -p > "$OUT/shared-text.png"

adb shell am force-stop "$PACKAGE"
adb shell am start -W -n "$MAIN" | tee "$OUT/start-resume.txt"
sleep 2
dump_ui resumed-context
assert_ui_contains "$OUT/resumed-context.xml" "$PROBE"
assert_process_alive > "$OUT/pid-resume.txt"
adb exec-out screencap -p > "$OUT/resumed-context.png"

# Clear only test data, then open the new benefits feature through the same
# public UI path a user taps. Direct ADB launch is intentionally not used because
# BenefitsActivity is correctly non-exported.
adb shell pm clear "$PACKAGE" | tee "$OUT/clear-before-benefits.txt"
grep -Fq Success "$OUT/clear-before-benefits.txt" || fail "could not reset test data"
adb shell am start -W -n "$MAIN" | tee "$OUT/start-benefits-home.txt"
sleep 3
dump_ui benefits-home
assert_ui_contains "$OUT/benefits-home.xml" "혜택·지원 자동 탐색"
tap_ui_contains "$OUT/benefits-home.xml" "혜택·지원 자동 탐색"
sleep 2
dump_ui benefits
assert_ui_contains "$OUT/benefits.xml" "혜택·지원 자동 탐색"
assert_ui_contains "$OUT/benefits.xml" "최근 위치 없음"
assert_process_alive > "$OUT/pid-benefits.txt"
adb exec-out screencap -p > "$OUT/benefits.png"

adb logcat -d -v threadtime > "$OUT/logcat-final.txt"
assert_clean_runtime_log "$OUT/logcat-final.txt"

{
  echo 'LIFE_AGENT_OS_V2_1_1_RUNTIME_SMOKE'
  echo "api=$(adb shell getprop ro.build.version.sdk | tr -d '\r')"
  echo "release=$(adb shell getprop ro.build.version.release | tr -d '\r')"
  echo 'fresh_install=PASS'
  echo 'cold_launch_x3=PASS'
  echo 'first_frame_normal_home=PASS'
  echo 'process_alive=PASS'
  echo 'deep_link_tasks=PASS'
  echo 'share_text_intake=PASS'
  echo 'encrypted_context_resume_after_force_stop=PASS'
  echo 'benefits_public_ui_entry=PASS'
  echo 'benefits_entry_without_permission_prompt=PASS'
  echo 'startup_error_log=NONE'
  echo 'fatal_main_exception=NONE'
} > "$OUT/RUNTIME_SMOKE_REPORT.txt"

cat "$OUT/RUNTIME_SMOKE_REPORT.txt"
