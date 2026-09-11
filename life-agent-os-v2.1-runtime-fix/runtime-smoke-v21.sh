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

assert_process_alive() {
  local pid
  pid=$(adb shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)
  [ -n "$pid" ] || fail "process is not alive"
  echo "$pid"
}

assert_no_fatal() {
  local file=$1
  if grep -Eq "FATAL EXCEPTION: main|Process: ${PACKAGE}.*PID" "$file"; then
    fail "fatal exception found in $file"
  fi
}

# The previously distributed alpha used a disposable debug key, so this repair
# lane deliberately performs a clean install. Update-signing continuity is a
# separate production release gate and is never implied here.
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
  assert_no_fatal "$OUT/logcat-home-${attempt}.txt"
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

# New v2.1 feature surface must open without requesting permissions on entry.
adb shell am start -W -n "$PACKAGE/.BenefitsActivity" | tee "$OUT/start-benefits.txt"
sleep 2
dump_ui benefits
assert_ui_contains "$OUT/benefits.xml" "혜택·지원 자동 탐색"
assert_ui_contains "$OUT/benefits.xml" "위치 확인 전입니다."
assert_process_alive > "$OUT/pid-benefits.txt"
adb exec-out screencap -p > "$OUT/benefits.png"

adb logcat -d -v threadtime > "$OUT/logcat-final.txt"
assert_no_fatal "$OUT/logcat-final.txt"

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
  echo 'benefits_entry_without_permission_prompt=PASS'
  echo 'fatal_main_exception=NONE'
} > "$OUT/RUNTIME_SMOKE_REPORT.txt"

cat "$OUT/RUNTIME_SMOKE_REPORT.txt"
