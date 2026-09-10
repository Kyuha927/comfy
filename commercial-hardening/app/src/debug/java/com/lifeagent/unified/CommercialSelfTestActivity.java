package com.lifeagent.unified;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/** Debug-only runtime contract suite. This class is excluded from release builds. */
public final class CommercialSelfTestActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        TextView output = new TextView(this);
        output.setPadding(24, 24, 24, 24);
        output.setTextSize(15f);
        List<Result> results = runTests();
        int failures = 0;
        StringBuilder text = new StringBuilder("LIFE AGENT COMMERCIAL SELF TEST\n\n");
        JSONArray jsonResults = new JSONArray();
        for (Result result : results) {
            if (!result.pass) failures++;
            text.append(result.pass ? "PASS  " : "FAIL  ").append(result.name).append('\n');
            JSONObject item = new JSONObject();
            try {
                item.put("name", result.name);
                item.put("pass", result.pass);
                item.put("detail", result.detail);
                jsonResults.put(item);
            } catch (Exception ignored) {}
        }
        text.append("\nTOTAL=").append(results.size())
                .append(" FAILURES=").append(failures)
                .append(failures == 0 ? "\nFINAL=PASS" : "\nFINAL=FAIL");
        output.setText(text.toString());
        setContentView(output);

        try {
            JSONObject report = new JSONObject();
            report.put("version", CommercialCore.VERSION);
            report.put("tests", results.size());
            report.put("failures", failures);
            report.put("final", failures == 0 ? "PASS" : "FAIL");
            report.put("results", jsonResults);
            File target = new File(getFilesDir(), "commercial-self-test.json");
            try (FileOutputStream stream = new FileOutputStream(target, false)) {
                stream.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
                stream.getFD().sync();
            }
        } catch (Exception error) {
            CommercialDiagnostics.record(this, "SELF_TEST_REPORT_WRITE");
        }
    }

    private List<Result> runTests() {
        List<Result> results = new ArrayList<>();
        results.add(test("encrypted_store_roundtrip", CommercialCore.SecureJsonStore.selfTest(this), ""));
        results.add(test("monimo_package_current",
                "net.ib.android.smcard".equals(CommercialCore.PKG_MONIMO), CommercialCore.PKG_MONIMO));
        results.add(test("otp_detected",
                CommercialCore.looksSensitive("인증번호 123456을 입력하세요"), ""));
        results.add(test("shopping_not_false_positive",
                !CommercialCore.looksSensitive("쇼핑 목록 정리해줘"), ""));
        results.add(test("card_redacted",
                CommercialCore.redact("4111 1111 1111 1111").contains("[결제정보 숨김]"), ""));

        CommercialCore.AppState state = new CommercialCore.AppState();
        CommercialCore.Plan insurance = CommercialCore.Planner.plan(
                this, "병원 진료비 서류로 보험 청구해줘", state);
        results.add(test("insurance_not_reservation",
                "insurance.claim.monimo".equals(insurance.skillId), insurance.skillId));

        CommercialCore.Plan reservation = CommercialCore.Planner.plan(
                this, "금요일 오후 병원 예약해줘", state);
        results.add(test("reservation_skill",
                "reservation.orchestrator".equals(reservation.skillId), reservation.skillId));

        CommercialCore.Plan ordinarySend = CommercialCore.Planner.plan(
                this, "이 문서를 친구에게 보내줘", state);
        results.add(test("ordinary_send_not_transfer",
                !"transfer.secure".equals(ordinarySend.skillId), ordinarySend.skillId));

        CommercialCore.Plan transfer = CommercialCore.Planner.plan(
                this, "엄마에게 5만원 보내줘", state);
        results.add(test("money_send_is_transfer",
                "transfer.secure".equals(transfer.skillId), transfer.skillId));
        results.add(test("transfer_requires_credential",
                transfer.gate == CommercialCore.Gate.DEVICE_CREDENTIAL, transfer.gate.name()));
        results.add(test("transfer_provider_fail_closed",
                transfer.integration == CommercialCore.Integration.SETUP_REQUIRED,
                transfer.integration.name()));

        CommercialCore.Plan benefit = CommercialCore.Planner.plan(
                this, "내가 받을 수 있는 지원금과 혜택 찾아줘", state);
        results.add(test("benefit_candidate_not_claimed_ready",
                benefit.integration == CommercialCore.Integration.SETUP_REQUIRED,
                benefit.integration.name()));

        CommercialCore.Plan otpPlan = CommercialCore.Planner.plan(
                this, "OTP 123456으로 로그인해줘", state);
        results.add(test("otp_execution_blocked",
                otpPlan.gate == CommercialCore.Gate.BLOCK, otpPlan.gate.name()));

        state.settings.notificationAnalysis = true;
        state.settings.allowedPackages.add(CommercialCore.PKG_KAKAO);
        CommercialCore.NotificationDecision allowed = CommercialCore.classifyNotification(
                state, CommercialCore.PKG_KAKAO, "보험금 안내", "추가서류가 필요합니다");
        results.add(test("allowed_notification_classified",
                allowed.accepted && allowed.type == CommercialCore.EventType.INSURANCE_FOLLOWUP,
                allowed.type.name()));

        CommercialCore.NotificationDecision denied = CommercialCore.classifyNotification(
                state, "com.example.unapproved", "지원금", "신청 대상입니다");
        results.add(test("unapproved_notification_ignored",
                !denied.accepted, denied.reason));

        CommercialCore.NotificationDecision sensitive = CommercialCore.classifyNotification(
                state, CommercialCore.PKG_KAKAO, "인증", "인증번호 654321");
        results.add(test("sensitive_notification_dropped",
                sensitive.sensitive && !sensitive.accepted,
                sensitive.reason));

        CommercialCore.TaskRecord task = transfer.createTask();
        results.add(test("task_cannot_complete_without_evidence", !task.canComplete(), ""));
        task.evidence = "provider-receipt-123";
        results.add(test("task_can_complete_with_evidence", task.canComplete(), ""));

        CommercialCore.StreamRule bad = new CommercialCore.StreamRule();
        bad.platform = "chzzk";
        bad.alias = "tester";
        bad.channelUrl = "https://evil.example/channel";
        results.add(test("stream_url_host_restricted",
                !CommercialCore.isAllowedChannelUrl(bad.platform, bad.channelUrl), ""));
        results.add(test("stream_official_host_allowed",
                CommercialCore.isAllowedChannelUrl("chzzk", "https://chzzk.naver.com/test"), ""));

        results.add(test("commercial_recommendations_default_off",
                !new CommercialCore.SettingsState().commercialRecommendations, ""));
        results.add(test("notification_analysis_default_off",
                !new CommercialCore.SettingsState().notificationAnalysis, ""));
        results.add(test("nearby_default_off",
                !new CommercialCore.SettingsState().nearbyOpportunities, ""));
        return results;
    }

    private static Result test(String name, boolean pass, String detail) {
        return new Result(name, pass, detail == null ? "" : detail);
    }

    private static final class Result {
        final String name;
        final boolean pass;
        final String detail;

        Result(String name, boolean pass, String detail) {
            this.name = name;
            this.pass = pass;
            this.detail = detail;
        }
    }
}
