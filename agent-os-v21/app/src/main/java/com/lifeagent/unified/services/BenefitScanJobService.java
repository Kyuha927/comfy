package com.lifeagent.unified.services;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.job.JobInfo;
import android.app.job.JobParameters;
import android.app.job.JobScheduler;
import android.app.job.JobService;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;

import com.lifeagent.unified.MainActivity;
import com.lifeagent.unified.core.AgentCore;
import com.lifeagent.unified.core.AgentRuntime;

import java.util.Map;

/** Periodic eligibility trigger. It never submits an application without the policy gate. */
public final class BenefitScanJobService extends JobService {
    private static final int JOB_ID = 2210;
    private static final int NOTICE_ID = 2211;
    private static final String CHANNEL = "life_agent_benefit_scan";
    private static final long PERIOD_MS = 24L * 60 * 60 * 1000;

    public static void schedule(Context context) {
        JobScheduler scheduler = context.getSystemService(JobScheduler.class);
        if (scheduler == null) return;
        JobInfo info = new JobInfo.Builder(JOB_ID,
                new ComponentName(context, BenefitScanJobService.class))
                .setPeriodic(PERIOD_MS)
                .setPersisted(true)
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                .build();
        scheduler.schedule(info);
    }

    @Override
    public boolean onStartJob(JobParameters params) {
        AgentRuntime runtime = AgentRuntime.get(this);
        long now = AgentCore.now();
        AgentCore.PersonalContextGraph graph = runtime.repository().loadContextGraph(now);
        boolean ready = !graph.value("profile.region", now).isBlank()
                && !graph.value("profile.age_band", now).isBlank();
        long last = parseLong(runtime.repository().getPlainString("last_benefit_scan", "0"));
        if (ready && now - last >= 20L * 60 * 60 * 1000) {
            runtime.repository().setPlainString("last_benefit_scan", Long.toString(now));
            runtime.handleAmbientEvent(new AgentCore.AmbientEvent(
                    null,
                    "schedule",
                    "notification.benefit",
                    "저장된 자격 프로필로 혜택 후보를 다시 확인할 시간입니다.",
                    getPackageName(),
                    now,
                    Map.of("origin", "daily_profile_scan"),
                    AgentCore.Sensitivity.PERSONAL,
                    true
            ));
            postNotice();
        }
        jobFinished(params, false);
        return false;
    }

    @Override
    public boolean onStopJob(JobParameters params) {
        return true;
    }

    private void postNotice() {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return;
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) return;
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(new NotificationChannel(
                    CHANNEL, "혜택 자격 확인", NotificationManager.IMPORTANCE_DEFAULT));
        }
        Intent open = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                .putExtra(MainActivity.EXTRA_OPEN_PAGE, "home");
        PendingIntent pending = PendingIntent.getActivity(this, NOTICE_ID, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL)
                : new Notification.Builder(this);
        builder.setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("받을 수 있는 혜택을 확인할까요?")
                .setContentText("최소 자격 프로필로 후보를 찾고 실제 제출 전에는 확인을 받습니다.")
                .setContentIntent(pending)
                .setAutoCancel(true)
                .setOnlyAlertOnce(true);
        manager.notify(NOTICE_ID, builder.build());
    }

    private static long parseLong(String raw) {
        try {
            return Long.parseLong(raw);
        } catch (Exception ignored) {
            return 0L;
        }
    }
}
