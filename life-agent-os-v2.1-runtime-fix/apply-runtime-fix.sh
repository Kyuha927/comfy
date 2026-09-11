#!/usr/bin/env bash
set -euo pipefail

ROOT=${1:?usage: apply-runtime-fix.sh /path/to/life-agent-unified-v2}
JAVA="$ROOT/app/src/main/java/com/lifeagent/unified"
GRADLE="$ROOT/app/build.gradle"
for name in MainActivity SecureStore ContextEngine RustDeskUpdateChecker BootReceiver DesignKit; do
  test -f "$JAVA/$name.java"
done
test -f "$GRADLE"

python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
java = root / "app/src/main/java/com/lifeagent/unified"

for path in java.glob("*.java"):
    text = path.read_text(encoding="utf-8").replace(".isBlank()", ".trim().isEmpty()")
    path.write_text(text, encoding="utf-8")

def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing patch anchor: {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

main = java / "MainActivity.java"
text = main.read_text(encoding="utf-8")
if "import android.util.Log;" not in text:
    text = text.replace("import android.text.InputType;\n", "import android.text.InputType;\nimport android.util.Log;\n", 1)
if 'private static final String TAG = "LifeAgentStartup";' not in text:
    text = text.replace("public final class MainActivity extends Activity {\n",
                        'public final class MainActivity extends Activity {\n    private static final String TAG = "LifeAgentStartup";\n', 1)
main.write_text(text, encoding="utf-8")

replace_once(main, '''    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        DesignKit.applyWindow(this);
        RustDeskUpdateChecker.schedule(this);
        applyEntryIntent(getIntent());
        incomingContext = isInternalEntry(getIntent()) ? null : ContextEngine.captureIntent(this, getIntent());
        buildShell();
        render();
    }
''', '''    @Override
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
        content.post(() -> RustDeskUpdateChecker.scheduleSafely(getApplicationContext()));
    }
''', "MainActivity.onCreate")

replace_once(main, '''        applyEntryIntent(intent);
        incomingContext = isInternalEntry(intent) ? null : ContextEngine.captureIntent(this, intent);
        render();
''', '''        applyEntryIntent(intent);
        captureIncomingContextSafely(intent);
        render();
''', "MainActivity.onNewIntent")

replace_once(main, '''    private void render() {
        content.removeAllViews();
''', '''    private void render() {
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
''', "MainActivity.render")

helpers = r'''    private void captureIncomingContextSafely(Intent intent) {
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
        detail.setText("첫 화면 구성 중 일부 기능이 실패했습니다. 앱은 종료하지 않았으며, 재시도할 수 있습니다.\n\n오류: "
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
replace_once(main, "    private void applyEntryIntent(Intent intent) {\n",
             helpers + "    private void applyEntryIntent(Intent intent) {\n", "MainActivity.helpers")

secure = java / "SecureStore.java"
replace_once(secure, '''    private SecureStore(Context context) {
        this.context = context;
        this.prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        ensureKey();
    }
''', '''    private SecureStore(Context context) {
        this.context = context;
        this.prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }
''', "SecureStore.constructor")
replace_once(secure, "    synchronized void remove(String key) {\n", '''    synchronized boolean isEncryptionReady() {
        try {
            ensureKey();
            return true;
        } catch (RuntimeException ignored) {
            return false;
        }
    }

    synchronized void remove(String key) {
''', "SecureStore.readiness")
text = secure.read_text(encoding="utf-8")
text = text.replace("        boolean rustDeskMonitor = true;", "        boolean rustDeskMonitor = false;")
text = text.replace('json.optBoolean("rustDeskMonitor", true)', 'json.optBoolean("rustDeskMonitor", false)')
secure.write_text(text, encoding="utf-8")

context = java / "ContextEngine.java"
replace_once(context, '''    private static synchronized void prune(Context context) {
        List<Event> events = load(context);
        SecureStore.Settings settings = SecureStore.get(context).loadSettings();
''', '''    private static synchronized void prune(Context context) {
        List<Event> events = load(context);
        if (events.isEmpty()) return;
        SecureStore.Settings settings = SecureStore.get(context).loadSettings();
''', "ContextEngine.prune")

rust = java / "RustDeskUpdateChecker.java"
text = rust.read_text(encoding="utf-8")
if "import android.util.Log;" not in text:
    text = text.replace("import android.os.Looper;\n", "import android.os.Looper;\nimport android.util.Log;\n", 1)
if 'private static final String TAG = "LifeAgentRustDesk";' not in text:
    text = text.replace('    private static final String API = "https://api.github.com/repos/rustdesk/rustdesk/releases/latest";\n',
                        '    private static final String TAG = "LifeAgentRustDesk";\n    private static final String API = "https://api.github.com/repos/rustdesk/rustdesk/releases/latest";\n', 1)
rust.write_text(text, encoding="utf-8")
replace_once(rust, "    static void schedule(Context context) {\n", '''    static void scheduleSafely(Context context) {
        try {
            schedule(context);
        } catch (RuntimeException error) {
            Log.e(TAG, "RustDesk monitor scheduling failed; app startup continues", error);
        }
    }

    static void schedule(Context context) {
''', "RustDesk.safeSchedule")
replace_once(rust, "        scheduler.schedule(job);", '''        int result = scheduler.schedule(job);
        if (result != JobScheduler.RESULT_SUCCESS) {
            Log.w(TAG, "RustDesk monitor was not scheduled");
        }''', "RustDesk.scheduleResult")

boot = java / "BootReceiver.java"
text = boot.read_text(encoding="utf-8").replace(
    "RustDeskUpdateChecker.schedule(context);", "RustDeskUpdateChecker.scheduleSafely(context);")
boot.write_text(text, encoding="utf-8")

design = java / "DesignKit.java"
replace_once(design, '''    static void applyWindow(Activity activity) {
        Window window = activity.getWindow();
        window.setStatusBarColor(BG);
        window.setNavigationBarColor(SURFACE);
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController controller = window.getInsetsController();
            if (controller != null) {
                controller.setSystemBarsAppearance(
                        WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                                | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,
                        WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                                | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);
            }
        } else {
            window.getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        }
    }
''', '''    static void applyWindow(Activity activity) {
        Window window = activity.getWindow();
        window.setStatusBarColor(BG);
        window.setNavigationBarColor(SURFACE);
        View decor = window.getDecorView();
        if (Build.VERSION.SDK_INT >= 30) {
            decor.post(() -> {
                try {
                    WindowInsetsController controller = window.getInsetsController();
                    if (controller != null) {
                        int appearance = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                                | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
                        controller.setSystemBarsAppearance(appearance, appearance);
                    }
                } catch (RuntimeException ignored) {
                    decor.setSystemUiVisibility(
                            View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
                }
            });
        } else {
            decor.setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        }
    }
''', "DesignKit.applyWindow")

gradle = root / "app/build.gradle"
text = gradle.read_text(encoding="utf-8")
text = text.replace("versionCode 210", "versionCode 211")
text = text.replace("versionName '2.1.0-agent-os-alpha'", "versionName '2.1.1-runtime-fix-alpha'")
gradle.write_text(text, encoding="utf-8")
PY

! grep -R -q '\.isBlank()' "$JAVA"
grep -q 'versionCode 211' "$GRADLE"
grep -q "versionName '2.1.1-runtime-fix-alpha'" "$GRADLE"
grep -q 'scheduleSafely' "$JAVA/MainActivity.java"
grep -q 'private void renderUnsafe()' "$JAVA/MainActivity.java"
grep -q 'isEncryptionReady' "$JAVA/SecureStore.java"
grep -q 'if (events.isEmpty()) return;' "$JAVA/ContextEngine.java"
grep -q 'rustDeskMonitor = false' "$JAVA/SecureStore.java"
grep -q 'decor.post(() ->' "$JAVA/DesignKit.java"

echo 'LIFE_AGENT_OS_V2_1_RUNTIME_FIX_APPLIED'
