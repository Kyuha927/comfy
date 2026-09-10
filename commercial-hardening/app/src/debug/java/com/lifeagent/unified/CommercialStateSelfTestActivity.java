package com.lifeagent.unified;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.location.Location;
import android.os.Bundle;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/** Debug-only encrypted state, event ingestion and recovery integration tests. */
public final class CommercialStateSelfTestActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        List<Result> results = runTests();
        int failures = 0;
        StringBuilder output = new StringBuilder("LIFE AGENT STATE INTEGRATION TEST\n\n");
        JSONArray array = new JSONArray();
        for (Result result : results) {
            if (!result.pass) failures++;
            output.append(result.pass ? "PASS  " : "FAIL  ").append(result.name).append('\n');
            try {
                JSONObject row = new JSONObject();
                row.put("name", result.name);
                row.put("pass", result.pass);
                row.put("detail", result.detail);
                array.put(row);
            } catch (Exception ignored) {}
        }
        output.append("\nTOTAL=").append(results.size())
                .append(" FAILURES=").append(failures)
                .append(failures == 0 ? "\nFINAL=PASS" : "\nFINAL=FAIL");
        TextView text = new TextView(this);
        text.setPadding(24, 24, 24, 24);
        text.setTextSize(15f);
        text.setText(output.toString());
        setContentView(text);
        writeReport(results, failures);
    }

    private List<Result> runTests() {
        List<Result> results = new ArrayList<>();
        try {
            CommercialCore.SecureJsonStore.wipe(this);
        } catch (CommercialCore.StoreException ignored) {}

        try {
            CommercialCore.AppState state = CommercialCore.load(this);
            state.profile.healthNotes = "비타민과 영양제 관심";
            state.settings.notificationAnalysis = true;
            state.settings.allowedPackages.add(CommercialCore.PKG_KAKAO);
            state.settings.nearbyOpportunities = true;
            CommercialCore.save(this, state);

            CommercialCore.OpportunityRecord insurance = CommercialCore.ingestNotification(
                    this, CommercialCore.PKG_KAKAO, "보험금 안내", "진료비 추가서류가 필요합니다");
            results.add(result("insurance_event_persisted",
                    insurance != null && "insurance".equals(insurance.category),
                    insurance == null ? "null" : insurance.category));

            CommercialCore.OpportunityRecord duplicate = CommercialCore.ingestNotification(
                    this, CommercialCore.PKG_KAKAO, "보험금 안내", "진료비 추가서류가 필요합니다");
            results.add(result("notification_deduplicated", duplicate == null, ""));

            Location location = new Location("self-test");
            location.setLatitude(37.5665d);
            location.setLongitude(126.9780d);
            location.setAccuracy(100f);
            CommercialCore.addNearbyPharmacyOpportunity(this, location);
            CommercialCore.AppState afterLocation = CommercialCore.load(this);
            boolean foundNearby = false;
            for (CommercialCore.OpportunityRecord item : afterLocation.opportunities) {
                if ("nearby_pharmacy".equals(item.category)) foundNearby = true;
            }
            results.add(result("nearby_opportunity_persisted", foundNearby, ""));

            CommercialCore.Plan transfer = CommercialCore.Planner.plan(this, "엄마에게 5만원 송금", afterLocation);
            CommercialCore.TaskRecord task = CommercialCore.createTask(this, transfer);
            boolean withoutEvidence = CommercialCore.completeTask(this, task.id, "");
            results.add(result("completion_without_evidence_rejected", !withoutEvidence, ""));
            boolean withEvidence = CommercialCore.completeTask(this, task.id, "provider-test-receipt");
            results.add(result("completion_with_evidence_accepted", withEvidence, ""));

            CommercialCore.AppState revisionOne = CommercialCore.load(this);
            revisionOne.profile.interestTags = "first-version";
            CommercialCore.save(this, revisionOne);
            CommercialCore.AppState revisionTwo = CommercialCore.load(this);
            revisionTwo.profile.interestTags = "second-version";
            CommercialCore.save(this, revisionTwo);

            SharedPreferences prefs = getSharedPreferences(
                    "life_agent_commercial_ciphertext_v5", Context.MODE_PRIVATE);
            boolean corrupted = prefs.edit().putString("agent_state.current", "{corrupt").commit();
            CommercialCore.AppState recovered = CommercialCore.load(this);
            results.add(result("current_state_corruption_written", corrupted, ""));
            results.add(result("backup_state_recovered",
                    "first-version".equals(recovered.profile.interestTags),
                    recovered.profile.interestTags));
            CommercialCore.save(this, recovered);

            String prefsDump = prefs.getAll().toString();
            results.add(result("plaintext_profile_not_in_preferences",
                    !prefsDump.contains("first-version")
                            && !prefsDump.contains("비타민")
                            && !prefsDump.contains("provider-test-receipt"), ""));
        } catch (Exception error) {
            results.add(result("integration_suite_exception", false,
                    error.getClass().getSimpleName() + ":" + error.getMessage()));
        }
        return results;
    }

    private void writeReport(List<Result> results, int failures) {
        try {
            JSONObject report = new JSONObject();
            report.put("version", CommercialCore.VERSION);
            report.put("tests", results.size());
            report.put("failures", failures);
            report.put("final", failures == 0 ? "PASS" : "FAIL");
            JSONArray array = new JSONArray();
            for (Result result : results) {
                JSONObject row = new JSONObject();
                row.put("name", result.name);
                row.put("pass", result.pass);
                row.put("detail", result.detail);
                array.put(row);
            }
            report.put("results", array);
            File target = new File(getFilesDir(), "commercial-state-self-test.json");
            try (FileOutputStream stream = new FileOutputStream(target, false)) {
                stream.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
                stream.getFD().sync();
            }
        } catch (Exception error) {
            CommercialDiagnostics.record(this, "STATE_TEST_REPORT_WRITE");
        }
    }

    private static Result result(String name, boolean pass, String detail) {
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
