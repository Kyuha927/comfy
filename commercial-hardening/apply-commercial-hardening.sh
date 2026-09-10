#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?extracted Android project root required}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cp -R "$SCRIPT_DIR/app/." "$ROOT/app/"

python3 - "$ROOT" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])

def replace_required(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"PATCH_MISS:{label}:{path}")
    path.write_text(text.replace(old, new), encoding="utf-8")

build = root / "app/build.gradle"
text = build.read_text(encoding="utf-8")
text, n1 = re.subn(r"versionCode\s+\d+", "versionCode 320", text, count=1)
text, n2 = re.subn(r"versionName\s+['\"][^'\"]+['\"]", "versionName '3.2.0-hardening-beta'", text, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit("PATCH_MISS:version")
# Keep one stable application id for in-place beta upgrades.
if "applicationId 'com.lifeagent.unified'" not in text and 'applicationId "com.lifeagent.unified"' not in text:
    text, n3 = re.subn(r"applicationId\s+['\"][^'\"]+['\"]", "applicationId 'com.lifeagent.unified'", text, count=1)
    if n3 != 1:
        raise SystemExit("PATCH_MISS:applicationId")
build.write_text(text, encoding="utf-8")

core = root / "app/src/main/java/com/lifeagent/unified/CommercialCore.java"
replace_required(
    core,
    '(?i)(password|passwd|비밀번호|간편비밀번호|pin|보안카드|복구코드|seed phrase|private key)',
    '(?i)(password|passwd|비밀번호|간편비밀번호|\\\\bpin\\\\b|보안카드|복구코드|seed phrase|private key)',
    "password_pattern_word_boundary",
)
replace_required(
    core,
    'if (containsAny(normalized, "예약", "병원", "식당", "미용실", "전화해")) {',
    'if (containsAny(normalized, "예약", "병원", "식당", "미용실", "전화해")\n                    && !containsAny(normalized, "보험", "모니모", "진료비", "추가서류", "청구")) {',
    "insurance_before_reservation",
)
replace_required(
    core,
    'if (containsAny(normalized, "송금", "보내줘", "입금", "이체")) {',
    'if (containsAny(normalized, "송금", "입금", "이체")\n                    || (normalized.contains("보내") && goal.matches(".*\\\\d+[만천]?원.*"))) {',
    "transfer_false_positive",
)
replace_required(
    core,
    'className = "com.lifeagent.unified.RustDeskActivity";',
    'className = "com.lifeagent.unified.CommercialUpdateActivity";',
    "explicit_update_checker",
)

autofill = root / "app/src/main/java/com/lifeagent/unified/SafeAutofillService.java"
text = autofill.read_text(encoding="utf-8")
text = text.replace('import android.view.autofill.AutofillManager;\n', '')
replacements = {
    'AutofillManager.AUTOFILL_HINT_EMAIL_ADDRESS.equals(hint)': '"emailAddress".equals(hint)',
    'AutofillManager.AUTOFILL_HINT_PHONE_NUMBER.equals(hint)': '"phoneNumber".equals(hint)',
    'AutofillManager.AUTOFILL_HINT_NAME.equals(hint)': '"name".equals(hint)',
    'AutofillManager.AUTOFILL_HINT_POSTAL_ADDRESS.equals(hint)': '"postalAddress".equals(hint)',
    'AutofillManager.AUTOFILL_HINT_POSTAL_CODE.equals(hint)': '"postalCode".equals(hint)',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"PATCH_MISS:autofill_hint:{old}")
    text = text.replace(old, new)
autofill.write_text(text, encoding="utf-8")

main = root / "app/src/main/java/com/lifeagent/unified/CommercialMainActivity.java"
text = main.read_text(encoding="utf-8")
old = '    private CommercialCore.Plan pendingCredentialPlan;\n'
new = '    private CommercialCore.Plan pendingCredentialPlan;\n    private boolean pendingDataWipe;\n'
if old not in text:
    raise SystemExit("PATCH_MISS:pending_wipe_field")
text = text.replace(old, new, 1)

old = '''        } else if (requestCode == REQUEST_DEVICE_CREDENTIAL) {
            if (resultCode == RESULT_OK && pendingCredentialPlan != null) {
                createTaskFromPlan(pendingCredentialPlan, true);
            } else {
                toast("기기 인증이 취소되었습니다.");
            }
            pendingCredentialPlan = null;
        }
'''
new = '''        } else if (requestCode == REQUEST_DEVICE_CREDENTIAL) {
            if (resultCode == RESULT_OK && pendingDataWipe) {
                pendingDataWipe = false;
                wipeNow();
            } else if (resultCode == RESULT_OK && pendingCredentialPlan != null) {
                createTaskFromPlan(pendingCredentialPlan, true);
            } else {
                pendingDataWipe = false;
                toast("기기 인증이 취소되었습니다.");
            }
            pendingCredentialPlan = null;
        }
'''
if old not in text:
    raise SystemExit("PATCH_MISS:credential_result")
text = text.replace(old, new, 1)

old = '''                    new AlertDialog.Builder(this)
                            .setTitle("마지막 확인")
                            .setMessage("정말 삭제하려면 다시 '삭제'를 누르세요.")
                            .setNegativeButton("취소", null)
                            .setPositiveButton("삭제", (d, w) -> wipeNow())
                            .show();
'''
new = '''                    pendingDataWipe = true;
                    startActivityForResult(credential, REQUEST_DEVICE_CREDENTIAL);
'''
if old not in text:
    raise SystemExit("PATCH_MISS:wipe_auth_launch")
text = text.replace(old, new, 1)

old = '''        } catch (CommercialCore.StoreException error) {
            state = new CommercialCore.AppState();
        }
'''
new = '''        } catch (CommercialCore.StoreException error) {
            CommercialDiagnostics.record(this, "STORE_LOAD_" + error.getMessage());
            state = new CommercialCore.AppState();
        }
'''
if old not in text:
    raise SystemExit("PATCH_MISS:load_diagnostic")
text = text.replace(old, new, 1)

old = '''    private void showStoreError(CommercialCore.StoreException error) {
        showMessage("안전 저장에 실패했습니다",
'''
new = '''    private void showStoreError(CommercialCore.StoreException error) {
        CommercialDiagnostics.record(this, "STORE_" + error.getMessage());
        showMessage("안전 저장에 실패했습니다",
'''
if old not in text:
    raise SystemExit("PATCH_MISS:store_error_diagnostic")
text = text.replace(old, new, 1)
main.write_text(text, encoding="utf-8")

listener = root / "app/src/main/java/com/lifeagent/unified/CommercialNotificationListener.java"
text = listener.read_text(encoding="utf-8")
old = '''        } catch (CommercialCore.StoreException ignored) {
            // Fail closed. Storage failures never trigger actions and are surfaced in app health.
        }
'''
new = '''        } catch (CommercialCore.StoreException error) {
            CommercialDiagnostics.record(this, "NOTIFICATION_STORE_" + error.getMessage());
            // Fail closed. Storage failures never trigger actions.
        }
'''
if old not in text:
    raise SystemExit("PATCH_MISS:listener_diagnostic")
listener.write_text(text.replace(old, new, 1), encoding="utf-8")

location = root / "app/src/main/java/com/lifeagent/unified/CommercialLocationService.java"
text = location.read_text(encoding="utf-8")
old = '''        } catch (CommercialCore.StoreException ignored) {
            // Do not keep running actions after a persistence failure.
            stopSelfSafely();
        }
'''
new = '''        } catch (CommercialCore.StoreException error) {
            CommercialDiagnostics.record(this, "LOCATION_STORE_" + error.getMessage());
            // Do not keep running actions after a persistence failure.
            stopSelfSafely();
        }
'''
if old not in text:
    raise SystemExit("PATCH_MISS:location_diagnostic")
location.write_text(text.replace(old, new, 1), encoding="utf-8")
PY

# Commercial release invariants.
grep -q "versionCode 320" "$ROOT/app/build.gradle"
grep -q "versionName '3.2.0-hardening-beta'" "$ROOT/app/build.gradle"
grep -q 'android.permission.ACCESS_COARSE_LOCATION' "$ROOT/app/src/main/AndroidManifest.xml"
! grep -q 'android.permission.ACCESS_BACKGROUND_LOCATION' "$ROOT/app/src/main/AndroidManifest.xml"
! grep -q 'android.permission.READ_SMS' "$ROOT/app/src/main/AndroidManifest.xml"
! grep -q 'android.permission.READ_CONTACTS' "$ROOT/app/src/main/AndroidManifest.xml"
! grep -q 'android.permission.QUERY_ALL_PACKAGES' "$ROOT/app/src/main/AndroidManifest.xml"
grep -q 'net.ib.android.smcard' "$ROOT/app/src/main/AndroidManifest.xml"
grep -q 'CommercialMainActivity' "$ROOT/app/src/main/AndroidManifest.xml"
grep -q 'CommercialNotificationListener' "$ROOT/app/src/main/AndroidManifest.xml"
grep -q 'SafeAutofillService' "$ROOT/app/src/main/AndroidManifest.xml"
grep -q 'CommercialLocationService' "$ROOT/app/src/main/AndroidManifest.xml"
