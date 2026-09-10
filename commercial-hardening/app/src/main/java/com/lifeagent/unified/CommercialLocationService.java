package com.lifeagent.unified;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

/**
 * Foreground-only location session. The app never requests background location permission.
 * Coordinates are held in memory, and only a coarse rounded dedup marker is persisted by the core.
 */
public final class CommercialLocationService extends Service implements LocationListener {
    static final String ACTION_START = "com.lifeagent.unified.action.START_LOCATION_SESSION";
    static final String ACTION_STOP = "com.lifeagent.unified.action.STOP_LOCATION_SESSION";
    private static final String CHANNEL_ID = "life_agent_location_session";
    private static final int NOTIFICATION_ID = 3201;
    private static final long DEFAULT_SESSION_MS = 2L * 60L * 60L * 1000L;
    private static final long MAX_SESSION_MS = 8L * 60L * 60L * 1000L;
    private static final long MIN_TIME_MS = 10L * 60L * 1000L;
    private static final float MIN_DISTANCE_M = 500f;

    private static volatile Location lastLocation;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private LocationManager locationManager;
    private long sessionEndMs;

    static Location lastKnownLocation() {
        Location value = lastLocation;
        return value == null ? null : new Location(value);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopSelfSafely();
            return START_NOT_STICKY;
        }
        if (checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            stopSelfSafely();
            return START_NOT_STICKY;
        }
        try {
            CommercialCore.AppState state = CommercialCore.load(this);
            if (!state.settings.nearbyOpportunities) {
                stopSelfSafely();
                return START_NOT_STICKY;
            }
            long now = System.currentTimeMillis();
            sessionEndMs = state.settings.locationSessionEndMs;
            if (sessionEndMs <= now || sessionEndMs - now > MAX_SESSION_MS) {
                sessionEndMs = now + DEFAULT_SESSION_MS;
                state.settings.locationSessionEndMs = sessionEndMs;
                CommercialCore.save(this, state);
            }
        } catch (CommercialCore.StoreException error) {
            stopSelfSafely();
            return START_NOT_STICKY;
        }

        createChannel();
        startForeground(NOTIFICATION_ID, buildNotification());
        startUpdates();
        handler.removeCallbacks(stopRunnable);
        handler.postDelayed(stopRunnable, Math.max(1_000L, sessionEndMs - System.currentTimeMillis()));
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (locationManager != null) {
            try {
                locationManager.removeUpdates(this);
            } catch (SecurityException ignored) {
                // Permission may have been revoked while the session was active.
            }
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onLocationChanged(Location location) {
        if (location == null || location.getAccuracy() < 0f || location.getAccuracy() > 5000f) return;
        lastLocation = new Location(location);
        try {
            CommercialCore.addNearbyPharmacyOpportunity(this, location);
        } catch (CommercialCore.StoreException ignored) {
            // Do not keep running actions after a persistence failure.
            stopSelfSafely();
        }
    }

    @Override
    public void onProviderEnabled(String provider) {}

    @Override
    public void onProviderDisabled(String provider) {}

    @Override
    @SuppressWarnings("deprecation")
    public void onStatusChanged(String provider, int status, Bundle extras) {}

    private void startUpdates() {
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        if (locationManager == null) {
            stopSelfSafely();
            return;
        }
        boolean requested = false;
        try {
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                locationManager.requestLocationUpdates(
                        LocationManager.NETWORK_PROVIDER, MIN_TIME_MS, MIN_DISTANCE_M, this, Looper.getMainLooper());
                requested = true;
                Location cached = locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER);
                if (cached != null) onLocationChanged(cached);
            }
            if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                    == PackageManager.PERMISSION_GRANTED
                    && locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                locationManager.requestLocationUpdates(
                        LocationManager.GPS_PROVIDER, MIN_TIME_MS, MIN_DISTANCE_M, this, Looper.getMainLooper());
                requested = true;
            }
        } catch (SecurityException ignored) {
            requested = false;
        }
        if (!requested) stopSelfSafely();
    }

    private Notification buildNotification() {
        Intent open = new Intent(this, CommercialMainActivity.class);
        open.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent openPending = PendingIntent.getActivity(this, 3201, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Intent stop = new Intent(this, CommercialLocationService.class);
        stop.setAction(ACTION_STOP);
        PendingIntent stopPending = PendingIntent.getService(this, 3202, stop,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        builder.setSmallIcon(android.R.drawable.ic_menu_mylocation)
                .setContentTitle("주변 기회 감지 중")
                .setContentText("대략적 위치만 사용하며 최대 2시간 뒤 자동 종료됩니다")
                .setContentIntent(openPending)
                .addAction(new Notification.Action.Builder(
                        android.R.drawable.ic_menu_close_clear_cancel, "중지", stopPending).build())
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setCategory(Notification.CATEGORY_SERVICE);
        if (Build.VERSION.SDK_INT < 26) builder.setPriority(Notification.PRIORITY_LOW);
        return builder.build();
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) return;
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "주변 기회 감지", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("사용자가 켠 시간 동안 대략적 위치로 주변 기회를 찾습니다");
        manager.createNotificationChannel(channel);
    }

    private final Runnable stopRunnable = this::stopSelfSafely;

    private void stopSelfSafely() {
        try {
            CommercialCore.AppState state = CommercialCore.load(this);
            state.settings.locationSessionEndMs = 0L;
            CommercialCore.save(this, state);
        } catch (CommercialCore.StoreException ignored) {
            // Service termination must not be blocked by a storage fault.
        }
        stopForeground(true);
        stopSelf();
    }
}
