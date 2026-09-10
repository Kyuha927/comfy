package com.lifeagent.unified;

import android.Manifest;
import android.app.ActivityOptions;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.text.TextUtils;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * Notification adapter with explicit package allowlisting and local redaction.
 * Raw notification text is never persisted. OTP/password/card notifications are discarded.
 */
public final class CommercialNotificationListener extends NotificationListenerService {
    private static final String CHANNEL_ACTIONS = "life_agent_context_actions";
    private static final String CHANNEL_STREAM = "life_agent_stream_fallback";
    private static final int MAX_PER_PACKAGE_PER_HOUR = 30;
    private static final long RATE_WINDOW_MS = TimeUnit.HOURS.toMillis(1);

    private final Map<String, RateWindow> rateWindows = new HashMap<>();

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null || sbn.getNotification() == null) return;
        if (getPackageName().equals(sbn.getPackageName())) return;
        if (!withinRateLimit(sbn.getPackageName())) return;

        Notification notification = sbn.getNotification();
        String title = text(notification.extras, Notification.EXTRA_TITLE);
        String body = notificationBody(notification.extras);
        try {
            CommercialCore.AppState state = CommercialCore.load(this);
            CommercialCore.NotificationDecision decision =
                    CommercialCore.classifyNotification(state, sbn.getPackageName(), title, body);
            if (!decision.accepted || decision.sensitive) return;

            CommercialCore.OpportunityRecord opportunity = CommercialCore.ingestNotification(
                    this, sbn.getPackageName(), title, body);

            if (decision.type == CommercialCore.EventType.STREAM_LIVE
                    && state.settings.exactStreamAutoOpen
                    && decision.exactStreamRule != null) {
                wakeScreenBriefly();
                boolean opened = sendOriginal(notification.contentIntent);
                if (!opened) {
                    postStreamFallback(decision.exactStreamRule, notification.contentIntent);
                }
                return;
            }

            if (opportunity != null) postOpportunityNotification(opportunity);
        } catch (CommercialCore.StoreException ignored) {
            // Fail closed. Storage failures never trigger actions and are surfaced in app health.
        }
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // Removal is not persisted. It is not reliable proof that an external task completed.
    }

    private boolean withinRateLimit(String packageName) {
        long now = System.currentTimeMillis();
        RateWindow window = rateWindows.get(packageName);
        if (window == null || now - window.startedAt >= RATE_WINDOW_MS) {
            window = new RateWindow(now, 0);
            rateWindows.put(packageName, window);
        }
        window.count += 1;
        return window.count <= MAX_PER_PACKAGE_PER_HOUR;
    }

    @SuppressWarnings("deprecation")
    private boolean sendOriginal(PendingIntent pendingIntent) {
        if (pendingIntent == null) return false;
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
        } catch (PendingIntent.CanceledException | SecurityException | IllegalArgumentException e) {
            return false;
        }
    }

    private void postOpportunityNotification(CommercialCore.OpportunityRecord opportunity) {
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null || !canPostNotifications()) return;
        createChannel(manager, CHANNEL_ACTIONS, "필요한 일과 혜택", NotificationManager.IMPORTANCE_DEFAULT);

        Intent open = new Intent(this, CommercialMainActivity.class);
        open.putExtra(CommercialMainActivity.EXTRA_OPEN_OPPORTUNITY, opportunity.id);
        open.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pending = PendingIntent.getActivity(
                this,
                opportunity.id.hashCode(),
                open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL_ACTIONS)
                : new Notification.Builder(this);
        builder.setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(opportunity.title)
                .setContentText(opportunity.reason)
                .setStyle(new Notification.BigTextStyle().bigText(opportunity.reason))
                .setContentIntent(pending)
                .setAutoCancel(true)
                .setOnlyAlertOnce(true)
                .setCategory(Notification.CATEGORY_RECOMMENDATION);
        if (Build.VERSION.SDK_INT < 26) builder.setPriority(Notification.PRIORITY_DEFAULT);
        manager.notify(opportunity.id.hashCode(), builder.build());
    }

    private void postStreamFallback(
            CommercialCore.StreamRule rule, PendingIntent original) {
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null || !canPostNotifications()) return;
        createChannel(manager, CHANNEL_STREAM, "방송 자동 실행 확인", NotificationManager.IMPORTANCE_HIGH);

        PendingIntent action = original;
        if (action == null) {
            Intent open = new Intent(Intent.ACTION_VIEW, android.net.Uri.parse(rule.channelUrl));
            open.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            action = PendingIntent.getActivity(this, rule.alias.hashCode(), open,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        }
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL_STREAM)
                : new Notification.Builder(this);
        builder.setSmallIcon(android.R.drawable.ic_media_play)
                .setContentTitle(rule.alias + " 방송 시작")
                .setContentText("Android가 자동 실행을 막았습니다. 눌러서 엽니다.")
                .setContentIntent(action)
                .setAutoCancel(true)
                .setOnlyAlertOnce(true)
                .setCategory(Notification.CATEGORY_EVENT);
        if (Build.VERSION.SDK_INT < 26) builder.setPriority(Notification.PRIORITY_HIGH);
        manager.notify(rule.alias.hashCode(), builder.build());
    }

    @SuppressWarnings({"deprecation", "WakelockTimeout"})
    private void wakeScreenBriefly() {
        PowerManager manager = getSystemService(PowerManager.class);
        if (manager == null || manager.isInteractive()) return;
        try {
            PowerManager.WakeLock lock = manager.newWakeLock(
                    PowerManager.SCREEN_BRIGHT_WAKE_LOCK
                            | PowerManager.ACQUIRE_CAUSES_WAKEUP
                            | PowerManager.ON_AFTER_RELEASE,
                    "LifeAgent:ExactStreamRule");
            lock.setReferenceCounted(false);
            lock.acquire(5_000L);
        } catch (SecurityException ignored) {
            // Fallback notification remains available.
        }
    }

    private boolean canPostNotifications() {
        return Build.VERSION.SDK_INT < 33
                || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                == PackageManager.PERMISSION_GRANTED;
    }

    private static void createChannel(
            NotificationManager manager, String id, String name, int importance) {
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(new NotificationChannel(id, name, importance));
        }
    }

    private static String text(Bundle extras, String key) {
        if (extras == null) return "";
        CharSequence value = extras.getCharSequence(key);
        return value == null ? "" : value.toString();
    }

    private static String notificationBody(Bundle extras) {
        if (extras == null) return "";
        StringBuilder result = new StringBuilder();
        append(result, extras.getCharSequence(Notification.EXTRA_TEXT));
        append(result, extras.getCharSequence(Notification.EXTRA_BIG_TEXT));
        append(result, extras.getCharSequence(Notification.EXTRA_SUB_TEXT));
        CharSequence[] lines = extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES);
        if (lines != null) for (CharSequence line : lines) append(result, line);
        return result.toString().trim();
    }

    private static void append(StringBuilder target, CharSequence value) {
        if (!TextUtils.isEmpty(value)) target.append(value).append(' ');
    }

    private static final class RateWindow {
        final long startedAt;
        int count;

        RateWindow(long startedAt, int count) {
            this.startedAt = startedAt;
            this.count = count;
        }
    }
}
