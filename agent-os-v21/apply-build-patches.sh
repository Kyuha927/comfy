#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?project root required}"
python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])

build = root / "app/build.gradle"
text = build.read_text(encoding="utf-8")
if "text-recognition-korean" not in text:
    text = text.replace('dependencies {\n    testImplementation', 'dependencies {\n    implementation "com.google.mlkit:text-recognition-korean:16.0.1"\n    testImplementation')
build.write_text(text, encoding="utf-8")

manifest = root / "app/src/main/AndroidManifest.xml"
text = manifest.read_text(encoding="utf-8")
activity = '''        <activity
            android:name=".DocumentIntakeActivity"
            android:exported="false" />

'''
if ".DocumentIntakeActivity" not in text:
    text = text.replace('        <service\n            android:name=".services.UnifiedNotificationListener"', activity + '        <service\n            android:name=".services.UnifiedNotificationListener"')
manifest.write_text(text, encoding="utf-8")

main = root / "app/src/main/java/com/lifeagent/unified/MainActivity.java"
text = main.read_text(encoding="utf-8")
if "RustDeskUpdateChecker" not in text:
    text = text.replace('import com.lifeagent.unified.services.LocationContextService;\n',
                        'import com.lifeagent.unified.services.LocationContextService;\nimport com.lifeagent.unified.services.RustDeskUpdateChecker;\n')
old_update = '''            case "software.update.monitor":
                repository.updateTaskState(task.id, AgentCore.TaskStatus.VERIFYING,
                        "공식 릴리스와 설치 버전을 비교하세요", "", "", now);
                openWeb("https://github.com/rustdesk/rustdesk/releases/latest");
                break;'''
new_update = '''            case "software.update.monitor":
                repository.updateTaskState(task.id, AgentCore.TaskStatus.RUNNING,
                        "설치 버전과 공식 안정판을 비교하는 중입니다", "", "", now);
                RustDeskUpdateChecker.checkAsync(this, result -> {
                    long checkedAt = AgentCore.now();
                    if (!result.error.isBlank()) {
                        repository.updateTaskState(task.id, AgentCore.TaskStatus.FAILED,
                                "네트워크를 확인하고 공식 릴리스를 다시 검사하세요", "", "UPDATE_CHECK_FAILED", checkedAt);
                        runtime.recordSkillFailure(task.skillId);
                        alert("RustDesk 업데이트 확인 실패", result.summary());
                    } else if (!result.installed) {
                        repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_USER,
                                "RustDesk 설치 여부를 결정하세요", result.summary(), "NOT_INSTALLED", checkedAt);
                        new AlertDialog.Builder(this)
                                .setTitle("RustDesk가 설치되어 있지 않습니다")
                                .setMessage(result.summary())
                                .setNegativeButton("닫기", null)
                                .setPositiveButton("공식 릴리스 보기", (dialog, which) -> openWeb(result.releaseUrl))
                                .show();
                    } else if (result.updateAvailable) {
                        repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_USER,
                                "변경사항을 확인하고 업데이트하세요", result.summary(), "UPDATE_AVAILABLE", checkedAt);
                        new AlertDialog.Builder(this)
                                .setTitle("RustDesk 업데이트가 있습니다")
                                .setMessage(result.summary())
                                .setNegativeButton("나중에", null)
                                .setPositiveButton("공식 릴리스 보기", (dialog, which) -> openWeb(result.releaseUrl))
                                .show();
                    } else {
                        repository.updateTaskState(task.id, AgentCore.TaskStatus.COMPLETED,
                                "완료", result.summary(), "", checkedAt);
                        runtime.recordSkillSuccess(task.skillId);
                        toast(result.summary());
                    }
                    showPage(Page.TASKS);
                });
                break;'''
if old_update in text:
    text = text.replace(old_update, new_update)
old_insurance = '''            case "insurance.monimo.claim":
                repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_USER,
                        "병원 서류 확인 후 모니모 본인인증을 진행하세요", "", "MANUAL_AUTH", now);
                alert("보험 청구 준비",
                        "서류 판독과 작업 연결은 준비됐습니다. 실제 모니모 제출은 설치된 앱 화면과 본인인증을 확인한 뒤 진행해야 하며, 접수번호가 있어야 완료됩니다.");
                showPage(Page.TASKS);
                break;'''
new_insurance = '''            case "insurance.monimo.claim":
                repository.updateTaskState(task.id, AgentCore.TaskStatus.RUNNING,
                        "병원 서류를 선택하거나 촬영해 기기 OCR을 진행하세요", "", "", now);
                Intent document = new Intent(this, DocumentIntakeActivity.class);
                document.putExtra(DocumentIntakeActivity.EXTRA_TASK_ID, task.id);
                startActivity(document);
                break;'''
if old_insurance in text:
    text = text.replace(old_insurance, new_insurance)
main.write_text(text, encoding="utf-8")

doc = root / "app/src/main/java/com/lifeagent/unified/DocumentIntakeActivity.java"
text = doc.read_text(encoding="utf-8")
if "EXTRA_TASK_ID" not in text:
    text = text.replace('public final class DocumentIntakeActivity extends Activity {\n    private static final int PICK_DOCUMENT = 501;',
                        'public final class DocumentIntakeActivity extends Activity {\n    public static final String EXTRA_TASK_ID = "life_agent_existing_insurance_task";\n    private static final int PICK_DOCUMENT = 501;')
    text = text.replace('    private Uri selectedUri;\n    private String extractedText = "";',
                        '    private Uri selectedUri;\n    private String existingTaskId = "";\n    private String extractedText = "";')
    text = text.replace('        buildUi();\n        Uri incoming = getIntent().getData();',
                        '        existingTaskId = getIntent().getStringExtra(EXTRA_TASK_ID);\n        if (existingTaskId == null) existingTaskId = "";\n        buildUi();\n        Uri incoming = getIntent().getData();')
    old_create = '''        AgentCore.ActionPlan plan = runtime.plan("이 병원 서류로 보험금 청구 준비해줘");
        runtime.acceptPlan(plan);'''
    new_create = '''        if (existingTaskId.isBlank()) {
            AgentCore.ActionPlan plan = runtime.plan("이 병원 서류로 보험금 청구 준비해줘");
            runtime.acceptPlan(plan);
        } else {
            runtime.repository().updateTaskState(existingTaskId, AgentCore.TaskStatus.WAITING_USER,
                    "OCR 결과를 검토하고 모니모 본인인증을 진행하세요", compact, "MANUAL_AUTH", now);
        }'''
    text = text.replace(old_create, new_create)
doc.write_text(text, encoding="utf-8")
PY

grep -q 'text-recognition-korean' "$ROOT/app/build.gradle"
grep -q 'DocumentIntakeActivity' "$ROOT/app/src/main/AndroidManifest.xml"
grep -q 'RustDeskUpdateChecker.checkAsync' "$ROOT/app/src/main/java/com/lifeagent/unified/MainActivity.java"
