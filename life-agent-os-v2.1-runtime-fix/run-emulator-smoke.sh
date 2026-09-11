#!/usr/bin/env bash
set -euo pipefail

API=${1:?usage: run-emulator-smoke.sh API APK [DEVICE_PROFILE]}
APK=${2:?usage: run-emulator-smoke.sh API APK [DEVICE_PROFILE]}
DEVICE_PROFILE=${3:-pixel_2}
PACKAGE=${PACKAGE_NAME:-com.lifeagent.unified}
AVD="life-agent-api-${API}"
OUT="runtime-evidence/api-${API}"
EMULATOR_PID=""
mkdir -p "$OUT"

diagnostic_snapshot() {
  set +e
  adb devices -l > "$OUT/adb-devices.txt" 2>&1
  timeout 12 adb logcat -d -v threadtime > "$OUT/logcat-complete.txt" 2>&1
  timeout 12 adb shell getprop > "$OUT/getprop.txt" 2>&1
  timeout 12 adb shell dumpsys activity activities > "$OUT/dumpsys-activity.txt" 2>&1
  timeout 12 adb shell dumpsys package "$PACKAGE" > "$OUT/dumpsys-package.txt" 2>&1
  df -h > "$OUT/runner-disk.txt" 2>&1
  free -h > "$OUT/runner-memory.txt" 2>&1
  set -e
}

cleanup() {
  set +e
  diagnostic_snapshot
  timeout 8 adb emu kill >/dev/null 2>&1 || true
  if [ -n "$EMULATOR_PID" ] && kill -0 "$EMULATOR_PID" >/dev/null 2>&1; then
    kill "$EMULATOR_PID" >/dev/null 2>&1 || true
    sleep 2
    kill -9 "$EMULATOR_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo no | avdmanager create avd --force \
  --name "$AVD" \
  --package "system-images;android-${API};google_apis;x86_64" \
  --device "$DEVICE_PROFILE"

sudo chmod 666 /dev/kvm 2>/dev/null || true
nohup emulator \
  -avd "$AVD" \
  -no-window \
  -no-audio \
  -no-boot-anim \
  -no-metrics \
  -gpu swiftshader_indirect \
  -accel on \
  -no-snapshot \
  -no-snapshot-save \
  -camera-back none \
  -camera-front none \
  -memory 2048 \
  -cores 2 \
  > "$OUT/emulator.log" 2>&1 &
EMULATOR_PID=$!
echo "$EMULATOR_PID" > "$OUT/emulator.pid"

booted=0
for attempt in $(seq 1 150); do
  if ! kill -0 "$EMULATOR_PID" >/dev/null 2>&1; then
    echo "Emulator process exited before boot" >&2
    tail -n 240 "$OUT/emulator.log" >&2 || true
    exit 1
  fi

  state=$(adb get-state 2>/dev/null | tr -d '\r' || true)
  boot=$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
  animation=$(adb shell getprop init.svc.bootanim 2>/dev/null | tr -d '\r' || true)
  if [ "$state" = "device" ] && [ "$boot" = "1" ] && { [ "$animation" = "stopped" ] || [ -z "$animation" ]; }; then
    booted=1
    break
  fi
  sleep 2
done

if [ "$booted" -ne 1 ]; then
  echo "Emulator API $API did not complete boot" >&2
  adb devices -l >&2 || true
  tail -n 300 "$OUT/emulator.log" >&2 || true
  exit 1
fi

adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
adb shell svc power stayon true || true
adb shell input keyevent 82 || true
adb shell getprop ro.build.version.sdk | tee "$OUT/api.txt"
adb shell getprop ro.build.version.release | tee "$OUT/release.txt"

chmod +x life-agent-os-v2.1-runtime-fix/runtime-smoke-v21.sh
RUNTIME_OUT="$OUT" life-agent-os-v2.1-runtime-fix/runtime-smoke-v21.sh "$APK"

diagnostic_snapshot
