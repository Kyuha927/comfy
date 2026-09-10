#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?extracted Android project root required}"

python3 - "$ROOT" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])

def replace_required(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"PATCH_MISS:{label}:{path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

build = root / "app/build.gradle"
text = build.read_text(encoding="utf-8")
text, n1 = re.subn(r"versionCode\s+320", "versionCode 330", text, count=1)
text, n2 = re.subn(r"versionName\s+'3\.2\.0-hardening-beta'", "versionName '3.3.0-hardening-beta'", text, count=1)
if n1 != 1 or n2 != 1:
    raise SystemExit("PATCH_MISS:v3_3_version")
build.write_text(text, encoding="utf-8")

core = root / "app/src/main/java/com/lifeagent/unified/CommercialCore.java"
replace_required(core,
    'static final String VERSION = "3.2.0-hardening-beta";',
    'static final String VERSION = "3.3.0-hardening-beta";',
    "core_version")
replace_required(core,
    '''    enum Integration {
        READY,
        PARTIAL,
        SETUP_REQUIRED,
        BLOCKED
    }
''',
    '''    enum Integration {
        READY,
        PARTIAL,
        SETUP_REQUIRED,
        BLOCKED
    }

    enum EvidenceSource {
        USER_ATTESTED,
        SYSTEM_VERIFIED,
        PROVIDER_SIGNED
    }
''',
    "evidence_source_enum")
replace_required(core,
    '''        boolean canComplete() {
            return !TextUtils.isEmpty(verificationType)
                    && !"none".equals(verificationType)
                    && !TextUtils.isEmpty(evidence)
                    && integration != Integration.BLOCKED;
        }
''',
    '''        boolean canComplete() {
            return baseEvidencePresent() && !requiresProviderEvidence(verificationType);
        }

        boolean canCompleteFromProvider() {
            return baseEvidencePresent();
        }

        private boolean baseEvidencePresent() {
            return !TextUtils.isEmpty(verificationType)
                    && !"none".equals(verificationType)
                    && !TextUtils.isEmpty(evidence)
                    && integration != Integration.BLOCKED;
        }
''',
    "task_evidence_policy")
replace_required(core,
    '''        double roundedLat = Math.round(location.getLatitude() * 1000d) / 1000d;
        double roundedLon = Math.round(location.getLongitude() * 1000d) / 1000d;
''',
    '''        double roundedLat = Math.round(location.getLatitude() * 100d) / 100d;
        double roundedLon = Math.round(location.getLongitude() * 100d) / 100d;
''',
    "coarser_location_persistence")
replace_required(core,
    '''        } else {
            decision.type = EventType.GENERAL_ACTION;
        }
        return decision;
    }
''',
    '''        } else {
            decision.type = EventType.GENERAL_ACTION;
        }
        switch (decision.type) {
            case INSURANCE_FOLLOWUP:
                decision.safeSummary = "보험 또는 추가서류 관련 알림 1건";
                break;
            case BENEFIT_CANDIDATE:
                decision.safeSummary = "지원·혜택 후보 알림 1건";
                break;
            case RESERVATION_CHANGE:
                decision.safeSummary = "예약 상태 관련 알림 1건";
                break;
            case STREAM_LIVE:
                decision.safeSummary = "방송 시작 알림 1건";
                break;
            case SOFTWARE_UPDATE:
                decision.safeSummary = "소프트웨어 업데이트 알림 1건";
                break;
            case DELIVERY:
                decision.safeSummary = "배송 상태 알림 1건";
                break;
            default:
                decision.safeSummary = "허용 앱의 일반 알림 1건";
                break;
        }
        return decision;
    }
''',
    "semantic_notification_summary")
old_complete = '''    static synchronized boolean completeTask(
            Context context, String taskId, String externalEvidence) throws StoreException {
        AppState state = load(context);
        TaskRecord task = findTask(state, taskId);
        if (task == null) return false;
        task.evidence = clipped(redact(externalEvidence), 400);
        task.updatedAt = System.currentTimeMillis();
        if (!task.canComplete()) {
            task.status = TaskStatus.VERIFYING;
            task.nextAction = "외부 완료 증거를 확인해야 합니다.";
            task.failureCode = "MISSING_VERIFIED_EVIDENCE";
            save(context, state);
            return false;
        }
        task.status = TaskStatus.COMPLETED;
        task.nextAction = "완료 증거가 저장되었습니다.";
        task.failureCode = "";
        save(context, state);
        return true;
    }
'''
new_complete = '''    static synchronized boolean completeTask(
            Context context, String taskId, String externalEvidence) throws StoreException {
        return recordEvidence(context, taskId, externalEvidence,
                EvidenceSource.USER_ATTESTED, false);
    }

    static synchronized boolean completeTaskFromProvider(
            Context context, String taskId, String externalEvidence, boolean signatureVerified)
            throws StoreException {
        return recordEvidence(context, taskId, externalEvidence,
                EvidenceSource.PROVIDER_SIGNED, signatureVerified);
    }

    private static boolean recordEvidence(
            Context context,
            String taskId,
            String externalEvidence,
            EvidenceSource source,
            boolean providerSignatureVerified) throws StoreException {
        AppState state = load(context);
        TaskRecord task = findTask(state, taskId);
        if (task == null) return false;
        task.evidence = clipped(redact(externalEvidence), 400);
        task.updatedAt = System.currentTimeMillis();
        boolean providerRequired = requiresProviderEvidence(task.verificationType);
        if (providerRequired && (source != EvidenceSource.PROVIDER_SIGNED
                || !providerSignatureVerified)) {
            task.status = TaskStatus.VERIFYING;
            task.nextAction = "정식 제공자의 서명된 완료 응답이 필요합니다.";
            task.failureCode = "PROVIDER_EVIDENCE_REQUIRED";
            save(context, state);
            return false;
        }
        boolean canComplete = providerRequired
                ? task.canCompleteFromProvider() : task.canComplete();
        if (!canComplete) {
            task.status = TaskStatus.VERIFYING;
            task.nextAction = "외부 완료 증거를 확인해야 합니다.";
            task.failureCode = "MISSING_VERIFIED_EVIDENCE";
            save(context, state);
            return false;
        }
        task.status = TaskStatus.COMPLETED;
        task.nextAction = source == EvidenceSource.PROVIDER_SIGNED
                ? "정식 제공자의 완료 증거가 검증되었습니다."
                : "사용자 확인 증거와 함께 종료했습니다.";
        task.failureCode = "";
        save(context, state);
        return true;
    }

    private static boolean requiresProviderEvidence(String verificationType) {
        return "provider_transaction_receipt".equals(verificationType)
                || "claim_receipt_number".equals(verificationType)
                || "official_application_receipt".equals(verificationType);
    }
'''
replace_required(core, old_complete, new_complete, "provider_evidence_completion")
replace_required(core,
    '''        boolean corePass() {
            return encryptedStore && deviceSecure && notificationPermission;
        }
''',
    '''        boolean corePass() {
            return encryptedStore && deviceSecure;
        }
''',
    "optional_notification_permission")
core.write_text(core.read_text(encoding="utf-8"), encoding="utf-8")

main = root / "app/src/main/java/com/lifeagent/unified/CommercialMainActivity.java"
replace_required(main,
    '''        autofill.setOnClickListener(v -> openSettingsAction(Settings.ACTION_SETTINGS));
''',
    '''        autofill.setOnClickListener(v -> openAutofillSettings());
''',
    "autofill_settings_action")
text = main.read_text(encoding="utf-8")
needle = '''    private void openSettingsAction(String action) {
'''
method = '''    private void openAutofillSettings() {
        try {
            Intent request = new Intent(Settings.ACTION_REQUEST_SET_AUTOFILL_SERVICE);
            request.setData(Uri.parse("package:" + getPackageName()));
            startActivity(request);
        } catch (ActivityNotFoundException error) {
            openSettingsAction(Settings.ACTION_SETTINGS);
        }
    }

'''
if needle not in text:
    raise SystemExit("PATCH_MISS:autofill_method_insertion")
main.write_text(text.replace(needle, method + needle, 1), encoding="utf-8")

self_test = root / "app/src/debug/java/com/lifeagent/unified/CommercialSelfTestActivity.java"
replace_required(self_test,
    '''        task.evidence = "provider-receipt-123";
        results.add(test("task_can_complete_with_evidence", task.canComplete(), ""));
''',
    '''        task.evidence = "provider-receipt-123";
        results.add(test("high_risk_task_rejects_manual_evidence", !task.canComplete(), ""));
        results.add(test("high_risk_task_accepts_provider_path", task.canCompleteFromProvider(), ""));
''',
    "self_test_provider_evidence")

state_test = root / "app/src/debug/java/com/lifeagent/unified/CommercialStateSelfTestActivity.java"
replace_required(state_test,
    '''            boolean withEvidence = CommercialCore.completeTask(this, task.id, "provider-test-receipt");
            results.add(result("completion_with_evidence_accepted", withEvidence, ""));
''',
    '''            boolean manualEvidence = CommercialCore.completeTask(
                    this, task.id, "provider-test-receipt");
            results.add(result("manual_high_risk_evidence_rejected", !manualEvidence, ""));
            boolean withEvidence = CommercialCore.completeTaskFromProvider(
                    this, task.id, "provider-test-receipt", true);
            results.add(result("signed_provider_evidence_accepted", withEvidence, ""));
''',
    "state_test_provider_evidence")
PY

grep -q "versionCode 330" "$ROOT/app/build.gradle"
grep -q "versionName '3.3.0-hardening-beta'" "$ROOT/app/build.gradle"
grep -q 'PROVIDER_EVIDENCE_REQUIRED' "$ROOT/app/src/main/java/com/lifeagent/unified/CommercialCore.java"
grep -q '지원·혜택 후보 알림 1건' "$ROOT/app/src/main/java/com/lifeagent/unified/CommercialCore.java"
grep -q 'Math.round(location.getLatitude() \* 100d)' "$ROOT/app/src/main/java/com/lifeagent/unified/CommercialCore.java"
grep -q 'ACTION_REQUEST_SET_AUTOFILL_SERVICE' "$ROOT/app/src/main/java/com/lifeagent/unified/CommercialMainActivity.java"
