package com.lifeagent.unified.services;

import android.Manifest;
import android.app.ActivityOptions;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import com.lifeagent.unified.MainActivity;
import com.lifeagent.unified.core.AgentCore;
import com.lifeagent.unified.core.AgentRuntime;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Ambient notification adapter. It ignores ordinary conversations and stores only actionable,
 * sanitized event summaries after explicit consent.
 */
public final class UnifiedNotificationListener extends NotificationListenerService {
    private static final String CHANNEL = "life_agent_actionable_context";
    private static final String DEDUP = "life_agent_notification_dedup_v21";
    private static final long DEDUP_MS = 10L * 60 * 1000;
    private static final String CHZZK = "com.navercorp.game.android.community";
    private static final String SOOP = "kr.co.nowcom.mobile.afreeca";

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null || getPackageName().equals(sbn.getPackageName())) return;
        AgentRuntime runtime = AgentRuntime.get(this);
        if (!"true".equalsIgnoreCase(runtime.repository()
                .loadContextGraph(AgentCore.now()).value("consent.notifications", AgentCore.now()))) {
            return;
        }
        Notification notification = sbn.getNotification();
        if (notification == null) return;
        String raw = notificationText(notification);
        if (raw.isBlank() || containsAuthenticationSecret(raw)) return;

        Classification classification = classify(sbn.getPackageName(), raw);
        if (classification == null) return;
        String summary = AgentCore.sanitizeIncoming(raw);
        if (summary.length() > 520) summary = summary.substring(0, 520) + "…";
        String id = sha256(sbn.getPackageName() + "|" + sbn.getKey() + "|" + summary);
        if (!markFirst(id)) return;

        AgentCore.AmbientEvent event = new AgentCore.AmbientEvent(
                id,
                "notification",
                classification.type,
                summary,
                sbn.getPackageName(),
                AgentCore.now(),
                classification.entities,
                classification.sensitivity,
                true
        );
        List<String> created = runtime.handleAmbientEvent(event);

        boolean autoOpened = false;
        if (classification.type.equals("notification.stream_live")) {
            autoOpened = maybeOpenExactStream(notification, summary, sbn.getPackageName(), runtime);
        }
        if (!autoOpened && (!created.isEmpty() || classification.urgent)) {
            postActionableNotice(classification.title, summary);
        }
    }

    private Classification classify(String packageName, String raw) {
        String text = AgentCore.normalize(raw);
        if ((CHZZK.equals(packageName) || SOOP.equals(packageName))
                && containsAny(text, "방송시작", "방송을시작", "라이브시작", "생방송", "isnowlive", "startedstreaming")) {
            return new Classification("notification.stream_live", "선택 방송이 시작됐습니다",
                    AgentCore.Sensitivity.PERSONAL, false, Map.of("platform", CHZZK.equals(packageName) ? "chzzk" : "soop"));
        }
        if (containsAny(text, "보험금", "삼성화재", "모니모", "보험청구")
                && containsAny(text, "추가서류", "보완", "처리결과", "접수", "지급", "부지급")) {
            return new Classification("notification.insurance_followup", "보험 청구에 확인할 일이 있습니다",
                    AgentCore.Sensitivity.SENSITIVE, true, Map.of("category", "insurance"));
        }
        if (containsAny(text, "예약", "방문", "진료") && containsAny(text, "취소", "변경", "불가", "마감")) {
            return new Classification("notification.reservation_cancelled", "예약 변경 또는 취소가 감지됐습니다",
                    AgentCore.Sensitivity.PERSONAL, true, Map.of("category", "reservation"));
        }
        if (containsAny(text, "지원금", "보조금", "복지", "정부24", "복지로", "지원사업", "혜택")
                && containsAny(text, "신청", "대상", "마감", "가능", "선정", "보완")) {
            return new Classification("notification.benefit", "혜택 또는 지원 안내가 도착했습니다",
                    AgentCore.Sensitivity.PERSONAL, false, Map.of("category", "benefit"));
        }
        if (containsAny(text, "rustdesk", "러스트데스크")
                && containsAny(text, "update", "업데이트", "새버전", "release", "릴리스")) {
            return new Classification("notification.update", "RustDesk 업데이트가 감지됐습니다",
                    AgentCore.Sensitivity.PUBLIC, false, Map.of("software", "rustdesk"));
        }
        if (containsAny(text, "예약확정", "접수완료", "신청완료")
                && !containsAny(text, "인증번호", "otp", "보안코드")) {
            return new Classification("notification.actionable", "완료 확인 알림이 도착했습니다",
                    AgentCore.Sensitivity.PERSONAL, false, Map.of("category", "confirmation"));
        }
        return null;
    }

    private boolean maybeOpenExactStream(Notification notification, String summary,
                                         String packageName, AgentRuntime runtime) {
        List<AgentCore.Recipe> exact = new ArrayList<>();
        for (AgentCore.Recipe recipe : runtime.repository().listRecipes()) {
            if (!recipe.enabled || !recipe.skillId.equals("stream.autoplay")
                    || !recipe.triggerType.equals("notification.stream_live")) continue;
            String expected = recipe.conditions.getOrDefault("summary_contains", "").trim();
            if (expected.isEmpty()) continue;
            if (AgentCore.normalize(summary).contains(AgentCore.normalize(expected))) exact.add(recipe);
        }
        if (exact.size() != 1) return false;
        if (!CHZZK.equals(packageName) && !SOOP.equals(packageName)) return false;
        PendingIntent pendingIntent = notification.contentIntent;
        if (pendingIntent == null) return false;
        wakeScreen();
        try {
            if (Build.VERSION.SDK_INT >= 34) {
                ActivityOptions options = ActivityOptions.makeBasic();
                options.setPendingIntentBackgroundActivityStartMode(
                        ActivityOptions.MODE_BACKGROUND_ACTIVITY_START_ALLOWED);
                pendingIntent.send(this, 0, null, null, null, null, options.toBundle());
            } else {
                pendingIntent.send();
            }
            return true;
        } catch (PendingIntent.CanceledException | SecurityException | IllegalArgumentException ignored) {
            return false;
        }
    }

    @SuppressWarnings("deprecation")
    private void wakeScreen() {
        PowerManager manager = getSystemService(PowerManager.class);
        if (manager == null || manager.isInteractive()) return;
        try {
            PowerManager.WakeLock wakeLock = manager.newWakeLock(
                    PowerManager.SCREEN_BRIGHT_WAKE_LOCK
                            | PowerManager.ACQUIRE_CAUSES_WAKEUP
                            | PowerManager.ON_AFTER_RELEASE,
                    "LifeAgentOS:ExactStream");
            wakeLock.setReferenceCounted(false);
            wakeLock.acquire(5_000L);
        } catch (SecurityException ignored) {
            // Android or the device vendor may decline; a visible notification remains available.
        }
    }

    private void postActionableNotice(String title, String summary) {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            return;
        }
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) return;
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(new NotificationChannel(
                    CHANNEL, "Life Agent가 찾은 할 일", NotificationManager.IMPORTANCE_HIGH));
        }
        Intent open = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                .putExtra(MainActivity.EXTRA_OPEN_PAGE, "home");
        PendingIntent tap = PendingIntent.getActivity(this, title.hashCode(), open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL)
                : new Notification.Builder(this);
        builder.setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(title)
                .setContentText(summary.length() > 90 ? summary.substring(0, 90) + "…" : summary)
                .setStyle(new Notification.BigTextStyle().bigText(summary))
                .setContentIntent(tap)
                .setAutoCancel(true)
                .setOnlyAlertOnce(true)
                .setCategory(Notification.CATEGORY_RECOMMENDATION);
        if (Build.VERSION.SDK_INT < 26) builder.setPriority(Notification.PRIORITY_HIGH);
        manager.notify(title.hashCode(), builder.build());
    }

    private String notificationText(Notification notification) {
        Bundle extras = notification.extras;
        StringBuilder out = new StringBuilder();
        append(out, extras.getCharSequence(Notification.EXTRA_TITLE));
        append(out, extras.getCharSequence(Notification.EXTRA_TEXT));
        append(out, extras.getCharSequence(Notification.EXTRA_BIG_TEXT));
        append(out, extras.getCharSequence(Notification.EXTRA_SUB_TEXT));
        CharSequence[] lines = extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES);
        if (lines != null) for (CharSequence line : lines) append(out, line);
        return out.toString().trim();
    }

    private void append(StringBuilder builder, CharSequence value) {
        if (value != null && value.length() > 0) builder.append(value).append(' ');
    }

    private boolean containsAuthenticationSecret(String raw) {
        String text = AgentCore.normalize(raw);
        return containsAny(text, "otp", "인증번호", "보안코드", "verificationcode",
                "로그인코드", "일회용비밀번호", "승인번호")
                || AgentCore.looksSensitive(raw);
    }

    private boolean markFirst(String id) {
        SharedPreferences prefs = getSharedPreferences(DEDUP, Context.MODE_PRIVATE);
        long now = System.currentTimeMillis();
        long previous = prefs.getLong(id, 0L);
        SharedPreferences.Editor editor = prefs.edit();
        for (Map.Entry<String, ?> entry : prefs.getAll().entrySet()) {
            if (entry.getValue() instanceof Long && now - (Long) entry.getValue() > DEDUP_MS) {
                editor.remove(entry.getKey());
            }
        }
        if (previous > 0 && now - previous <= DEDUP_MS) {
            editor.apply();
            return false;
        }
        editor.putLong(id, now).apply();
        return true;
    }

    private static boolean containsAny(String text, String... tokens) {
        for (String token : tokens) if (text.contains(AgentCore.normalize(token))) return true;
        return false;
    }

    private static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder();
            for (byte item : digest) out.append(String.format(Locale.ROOT, "%02x", item));
            return out.toString();
        } catch (Exception impossible) {
            return Integer.toHexString(value.hashCode());
        }
    }

    private static final class Classification {
        final String type;
        final String title;
        final AgentCore.Sensitivity sensitivity;
        final boolean urgent;
        final Map<String, String> entities;

        Classification(String type, String title, AgentCore.Sensitivity sensitivity,
                       boolean urgent, Map<String, String> entities) {
            this.type = type;
            this.title = title;
            this.sensitivity = sensitivity;
            this.urgent = urgent;
            this.entities = entities;
        }
    }
}
