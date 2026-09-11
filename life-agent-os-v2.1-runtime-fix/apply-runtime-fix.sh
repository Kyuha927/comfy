#!/usr/bin/env bash
set -euo pipefail

ROOT=${1:?usage: apply-runtime-fix.sh /path/to/life-agent-unified-v2}
JAVA="$ROOT/app/src/main/java/com/lifeagent/unified"
MAIN="$JAVA/MainActivity.java"
SECURE="$JAVA/SecureStore.java"
RUST="$JAVA/RustDeskUpdateChecker.java"
BOOT="$JAVA/BootReceiver.java"
GRADLE="$ROOT/app/build.gradle"

for required in "$MAIN" "$SECURE" "$RUST" "$BOOT" "$GRADLE"; do
  test -f "$required"
done

python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/lifeagent/unified"

# Android API 30 is the declared minimum. String.isBlank() is not safe on the
# whole supported range, so keep the same intent without requiring that method.
for path in java.glob("*.java"):
    text = path.read_text(encoding="utf-8")
    text = text.replace(".isBlank()", ".trim().isEmpty()")
    path.write_text(text, encoding="utf-8")

main = java / "MainActivity.java"
text = main.read_text(encoding="utf-8")
if "private static final String TAG = \"LifeAgentStartup\";" not in text:
    text = text.replace(
        "public final class MainActivity extends Activity {\n",
        "public final class MainActivity extends Activity {\n"
        "    private static final String TAG = \"LifeAgentStartup\";\n"
    )
if "import android.util.Log;" not in text:
    text = text.replace("import android.text.InputType;\n", "import android.text.InputType;\nimport android.util.Log;\n")

old_on_create = '''    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        DesignKit.applyWindow(this);
        RustDeskUpdateChecker.schedule(this);
        applyEntryIntent(getIntent());
        incomingContext = isInternalEntry(getIntent()) ? null : ContextEngine.captureIntent(this, getIntent());
        buildShell();
        render();
    }
'''
new_on_create = '''    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            DesignKit.applyWindow(this);
        } catch (RuntimeException error) {
            Log.e(TAG, "Window styling failed; continuing with platform defaults", error);
        }
        applyEntryIntent(getIntent());
        buildShell();
        captureIncomingContextSafely(getIntent());
        render();

        // Non-essential background work must never stand between a tap and the first frame.
        content.post(() -> RustDeskUpdateChecker.scheduleSafely(getApplicationContext()));
    }
'''
if old_on_create not in text:
    raise SystemExit("MainActivity onCreate anchor not found")
text = text.replace(old_on_create, new_on_create)

old_new_intent = '''        applyEntryIntent(intent);
        incomingContext = isInternalEntry(intent) ? null : ContextEngine.captureIntent(this, intent);
        render();
'''
new_new_intent = '''        applyEntryIntent(intent);
        captureIncomingContextSafely(intent);
        render();
'''
if old_new_intent not in text:
    raise SystemExit("MainActivity onNewIntent anchor not found")
text = text.replace(old_new_intent, new_new_intent)

old_render = '''    private void render() {
        content.removeAllViews();
'''
new_render = '''    private void render() {
        try {
            renderUnsafe();
        } catch (Throwable error) {
            if (error instanceof VirtualMachineError) throw (VirtualMachineError) error;
            if (error instanceof ThreadDeath) throw (ThreadDeath) error;
            Log.e(TAG, "Screen render failed; entering recovery surface", error);
            showStartupRecovery(error);
        }
    }

    private void renderUnsafe() {
        content.removeAllViews();
'''
if old_render not in text:
    raise SystemExit("MainActivity render anchor not found")
text = text.replace(old_render, new_render, 1)

insert_anchor = '''    private void applyEntryIntent(Intent intent) {
'''
helpers = '''    private void captureIncomingContextSafely(Intent intent) {
        if (isInternalEntry(intent)) {
            incomingContext = null;
            return;
        }
        try {
            incomingContext = ContextEngine.captureIntent(this, intent);
        } catch (Throwable error) {
            if (error instanceof VirtualMachineError) throw (VirtualMachineError) error;
            if (error instanceof ThreadDeath) throw (ThreadDeath) error;
            incomingContext = null;
            Log.e(TAG, "Incoming context capture failed; continuing without it", error);
        }
    }

    private void showStartupRecovery(Throwable error) {
        LinearLayout recovery = new LinearLayout(this);
        recovery.setOrientation(LinearLayout.VERTICAL);
        recovery.setGravity(Gravity.CENTER_VERTICAL);
        int pad = Math.round(24f * getResources().getDisplayMetrics().density);
        recovery.setPadding(pad, pad, pad, pad);
        recovery.setBackgroundColor(Color.rgb(246, 245, 241));

        TextView title = new TextView(this);
        title.setText("Life Agent를 복구 모드로 열었습니다");
        title.setTextSize(22f);
        title.setTextColor(Color.rgb(27, 37, 32));
        recovery.addView(title, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView detail = new TextView(this);
        detail.setText("첫 화면 구성 중 일부 기능이 실패했습니다. 앱은 종료하지 않았으며, 재시도하거나 진단 정보를 확인할 수 있습니다.\n\n오류: "
                + error.getClass().getSimpleName());
        detail.setTextSize(15f);
        detail.setTextColor(Color.rgb(76, 88, 82));
        detail.setPadding(0, pad / 2, 0, pad);
        recovery.addView(detail, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView retry = new TextView(this);
        retry.setText("다시 불러오기");
        retry.setGravity(Gravity.CENTER);
        retry.setTextSize(16f);
        retry.setTextColor(Color.WHITE);
        retry.setBackgroundColor(Color.rgb(36, 72, 58));
        retry.setPadding(pad / 2, pad / 2, pad / 2, pad / 2);
        retry.setOnClickListener(v -> render());
        recovery.addView(retry, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        if (content == null || bottomBar == null) {
            setContentView(recovery);
            return;
        }
        content.removeAllViews();
        bottomBar.removeAllViews();
        content.addView(recovery, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

'''
if insert_anchor not in text:
    raise SystemExit("MainActivity helper insertion anchor not found")
text = text.replace(insert_anchor, helpers + insert_anchor, 1)
main.write_text(text, encoding="utf-8")

secure = java / "SecureStore.java"
text = secure.read_text(encoding="utf-8")
if "import android.util.Log;" not in text:
    text = text.replace("import android.util.Base64;\n", "import android.util.Base64;\nimport android.util.Log;\n")
text = text.replace(
    '    private static final String PREFS = "life_agent_secure_v2";\n',
    '    private static final String TAG = "LifeAgentSecureStore";\n'
    '    private static final String PREFS = "life_agent_secure_v2";\n'
)
old_ctor = '''    private SecureStore(Context context) {
        this.context = context;
        this.prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        ensureKey();
    }
'''
new_ctor = '''    private SecureStore(Context context) {
        this.context = context;
        this.prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        // Key creation is lazy. A transient or vendor-specific Keystore fault must not
        // crash the launcher before the user can see diagnostics or recovery controls.
    }
'''
if old_ctor not in text:
    raise SystemExit("SecureStore constructor anchor not found")
text = text.replace(old_ctor, new_ctor)

old_put = '''    synchronized void putString(String key, String value) {
        prefs.edit().putString(key, encryptString(value == null ? "" : value)).apply();
    }
'''
new_put = '''    synchronized void putString(String key, String value) {
        try {
            prefs.edit().putString(key, encryptString(value == null ? "" : value)).apply();
        } catch (RuntimeException error) {
            // Fail closed: never fall back to plaintext. Keep the process alive and let
            // callers/diagnostics retry once the Android Keystore is available again.
            Log.e(TAG, "Encrypted write skipped for key=" + key, error);
        }
    }
'''
if old_put not in text:
    raise SystemExit("SecureStore putString anchor not found")
text = text.replace(old_put, new_put)

old_get_catch = '''        } catch (Exception ignored) {
            return fallback;
        }
    }

    synchronized void remove(String key) {
'''
new_get_catch = '''        } catch (Exception error) {
            Log.e(TAG, "Encrypted read failed for key=" + key, error);
            return fallback;
        }
    }

    synchronized boolean isEncryptionReady() {
        try {
            ensureKey();
            return true;
        } catch (RuntimeException error) {
            Log.e(TAG, "Android Keystore is unavailable", error);
            return false;
        }
    }

    synchronized void remove(String key) {
'''
if old_get_catch not in text:
    raise SystemExit("SecureStore getString catch anchor not found")
text = text.replace(old_get_catch, new_get_catch, 1)

# Background monitoring is opt-in. It must not be enabled by default during startup.
text = text.replace("        boolean rustDeskMonitor = true;", "        boolean rustDeskMonitor = false;")
text = text.replace('json.optBoolean("rustDeskMonitor", true)', 'json.optBoolean("rustDeskMonitor", false)')
secure.write_text(text, encoding="utf-8")

rust = java / "RustDeskUpdateChecker.java"
text = rust.read_text(encoding="utf-8")
if "import android.util.Log;" not in text:
    text = text.replace("import android.os.Looper;\n", "import android.os.Looper;\nimport android.util.Log;\n")
text = text.replace(
    '    private static final String API = "https://api.github.com/repos/rustdesk/rustdesk/releases/latest";\n',
    '    private static final String TAG = "LifeAgentRustDesk";\n'
    '    private static final String API = "https://api.github.com/repos/rustdesk/rustdesk/releases/latest";\n'
)
anchor = '''    static void schedule(Context context) {
'''
safe = '''    static void scheduleSafely(Context context) {
        try {
            schedule(context);
        } catch (RuntimeException error) {
            Log.e(TAG, "RustDesk monitor scheduling failed; app startup continues", error);
        }
    }

'''
if anchor not in text:
    raise SystemExit("RustDesk schedule anchor not found")
text = text.replace(anchor, safe + anchor, 1)
text = text.replace("        scheduler.schedule(job);", "        int result = scheduler.schedule(job);\n        if (result != JobScheduler.RESULT_SUCCESS) Log.w(TAG, \"RustDesk monitor was not scheduled\");")
rust.write_text(text, encoding="utf-8")

boot = java / "BootReceiver.java"
text = boot.read_text(encoding="utf-8")
text = text.replace("RustDeskUpdateChecker.schedule(context);", "RustDeskUpdateChecker.scheduleSafely(context);")
boot.write_text(text, encoding="utf-8")

# Version identity for the repaired alpha.
gradle = root / "app/build.gradle"
text = gradle.read_text(encoding="utf-8")
text = text.replace("versionCode 210", "versionCode 211")
text = text.replace("versionName '2.1.0-agent-os-alpha'", "versionName '2.1.1-runtime-fix-alpha'")
gradle.write_text(text, encoding="utf-8")
PY

# Hard gates: no unsupported String.isBlank calls and all startup guards present.
! grep -R -q '\.isBlank()' "$JAVA"
grep -q 'versionCode 211' "$GRADLE"
grep -q "versionName '2.1.1-runtime-fix-alpha'" "$GRADLE"
grep -q 'scheduleSafely' "$MAIN"
grep -q 'private void renderUnsafe()' "$MAIN"
grep -q 'isEncryptionReady' "$SECURE"
grep -q 'rustDeskMonitor = false' "$SECURE"

echo 'LIFE_AGENT_OS_V2_1_RUNTIME_FIX_APPLIED'
