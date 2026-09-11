#!/usr/bin/env bash
set -euo pipefail

API=${1:?usage: run-emulator-smoke.sh API APK [DEVICE_PROFILE]}
APK=${2:?usage: run-emulator-smoke.sh API APK [DEVICE_PROFILE]}
DEVICE_PROFILE=${3:-pixel_2}
PACKAGE=${PACKAGE_NAME:-com.lifeagent.unified}
AVD="life-agent-api-${API}"
OUT="runtime-evidence/api-${API}"
EMULATOR_PID=""
SDK_ROOT=${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}

if [ -z "$SDK_ROOT" ]; then
  echo 'ANDROID_HOME and ANDROID_SDK_ROOT are both unset' >&2
  exit 1
fi

EMULATOR_BIN="$SDK_ROOT/emulator/emulator"
ADB_BIN="$SDK_ROOT/platform-tools/adb"
AVDMANAGER_BIN="$SDK_ROOT/cmdline-tools/latest/bin/avdmanager"

if [ ! -x "$AVDMANAGER_BIN" ]; then
  AVDMANAGER_BIN=$(command -v avdmanager || true)
fi
for required in "$EMULATOR_BIN" "$ADB_BIN" "$AVDMANAGER_BIN"; do
  if [ -z "$required" ] || [ ! -x "$required" ]; then
    echo "Required Android SDK executable is missing: $required" >&2
    find "$SDK_ROOT" -maxdepth 4 -type f \( -name emulator -o -name adb -o -name avdmanager \) 2>/dev/null | sort >&2 || true
    exit 1
  fi
done

mkdir -p "$OUT"

# avdmanager and emulator must resolve the same user/AVD directories. GitHub
# runners can expose different HOME values between setup actions and shell steps,
# so pin all Android user state inside this checkout before creating the AVD.
ANDROID_STATE_ROOT="$PWD/.android-ci/api-${API}"
export ANDROID_USER_HOME="$ANDROID_STATE_ROOT"
export ANDROID_EMULATOR_HOME="$ANDROID_STATE_ROOT"
export ANDROID_AVD_HOME="$ANDROID_STATE_ROOT/avd"
mkdir -p "$ANDROID_AVD_HOME"

{
  echo "ANDROID_HOME=$SDK_ROOT"
  echo "ANDROID_USER_HOME=$ANDROID_USER_HOME"
  echo "ANDROID_EMULATOR_HOME=$ANDROID_EMULATOR_HOME"
  echo "ANDROID_AVD_HOME=$ANDROID_AVD_HOME"
  echo "HOME=$HOME"
} > "$OUT/android-paths.txt"

diagnostic_snapshot() {
  set +e
  "$ADB_BIN" devices -l > "$OUT/adb-devices.txt" 2>&1
  timeout 12 "$ADB_BIN" logcat -d -v threadtime > "$OUT/logcat-complete.txt" 2>&1
  timeout 12 "$ADB_BIN" shell getprop > "$OUT/getprop.txt" 2>&1
  timeout 12 "$ADB_BIN" shell dumpsys activity activities > "$OUT/dumpsys-activity.txt" 2>&1
  timeout 12 "$ADB_BIN" shell dumpsys package "$PACKAGE" > "$OUT/dumpsys-package.txt" 2>&1
  find "$ANDROID_STATE_ROOT" -maxdepth 4 -printf '%y %p\n' > "$OUT/avd-files.txt" 2>&1
  "$EMULATOR_BIN" -list-avds > "$OUT/avd-list-final.txt" 2>&1
  df -h > "$OUT/runner-disk.txt" 2>&1
  free -h > "$OUT/runner-memory.txt" 2>&1
  set -e
}

cleanup() {
  set +e
  diagnostic_snapshot
  timeout 8 "$ADB_BIN" emu kill >/dev/null 2>&1 || true
  if [ -n "$EMULATOR_PID" ] && kill -0 "$EMULATOR_PID" >/dev/null 2>&1; then
    kill "$EMULATOR_PID" >/dev/null 2>&1 || true
    sleep 2
    kill -9 "$EMULATOR_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

rm -rf "$ANDROID_AVD_HOME/$AVD.avd" "$ANDROID_AVD_HOME/$AVD.ini"
echo no | "$AVDMANAGER_BIN" create avd --force \
  --name "$AVD" \
  --package "system-images;android-${API};google_apis;x86_64" \
  --device "$DEVICE_PROFILE" \
  --path "$ANDROID_AVD_HOME/$AVD.avd"

"$EMULATOR_BIN" -list-avds | tee "$OUT/avd-list-created.txt"
grep -Fxq "$AVD" "$OUT/avd-list-created.txt" || {
  echo "Created AVD is not visible to emulator: $AVD" >&2
  find "$ANDROID_STATE_ROOT" "$HOME/.android" -maxdepth 5 -printf '%y %p\n' 2>/dev/null | sort >&2 || true
  exit 1
}

test -f "$ANDROID_AVD_HOME/$AVD.ini"
test -d "$ANDROID_AVD_HOME/$AVD.avd"

sudo chmod 666 /dev/kvm 2>/dev/null || true
nohup "$EMULATOR_BIN" \
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

  state=$("$ADB_BIN" get-state 2>/dev/null | tr -d '\r' || true)
  boot=$("$ADB_BIN" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
  animation=$("$ADB_BIN" shell getprop init.svc.bootanim 2>/dev/null | tr -d '\r' || true)
  if [ "$state" = "device" ] && [ "$boot" = "1" ] && { [ "$animation" = "stopped" ] || [ -z "$animation" ]; }; then
    booted=1
    break
  fi
  sleep 2
done

if [ "$booted" -ne 1 ]; then
  echo "Emulator API $API did not complete boot" >&2
  "$ADB_BIN" devices -l >&2 || true
  tail -n 300 "$OUT/emulator.log" >&2 || true
  exit 1
fi

"$ADB_BIN" shell settings put global window_animation_scale 0
"$ADB_BIN" shell settings put global transition_animation_scale 0
"$ADB_BIN" shell settings put global animator_duration_scale 0
"$ADB_BIN" shell svc power stayon true || true
"$ADB_BIN" shell input keyevent 82 || true
"$ADB_BIN" shell getprop ro.build.version.sdk | tee "$OUT/api.txt"
"$ADB_BIN" shell getprop ro.build.version.release | tee "$OUT/release.txt"

export PATH="$SDK_ROOT/platform-tools:$PATH"
chmod +x life-agent-os-v2.1-runtime-fix/runtime-smoke-v21.sh
RUNTIME_OUT="$OUT" life-agent-os-v2.1-runtime-fix/runtime-smoke-v21.sh "$APK"

diagnostic_snapshot
