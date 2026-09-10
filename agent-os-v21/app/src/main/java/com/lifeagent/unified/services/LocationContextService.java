package com.lifeagent.unified.services;

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
import android.os.IBinder;
import android.os.Looper;

import com.lifeagent.unified.MainActivity;
import com.lifeagent.unified.R;
import com.lifeagent.unified.core.AgentCore;
import com.lifeagent.unified.core.AgentRuntime;

import java.util.Locale;
import java.util.Map;

/** Explicitly enabled foreground service that retains only coarse, short-lived location context. */
public final class LocationContextService extends Service implements LocationListener {
    private static final String CHANNEL = "life_agent_location_context";
    private static final int NOTIFICATION_ID = 2101;
    private static final long MIN_TIME_MS = 5L * 60 * 1000;
    private static final float MIN_DISTANCE_METERS = 250f;
    private LocationManager locationManager;

    public static void start(Context context) {
        AgentRuntime.get(context).repository().setPlainSetting("location_service_enabled", true);
        Intent intent = new Intent(context, LocationContextService.class);
        try {
            if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(intent);
            else context.startService(intent);
        } catch (RuntimeException error) {
            AgentRuntime.get(context).repository().setPlainSetting("location_service_enabled", false);
        }
    }

    public static void stop(Context context) {
        AgentRuntime.get(context).repository().setPlainSetting("location_service_enabled", false);
        context.stopService(new Intent(context, LocationContextService.class));
    }

    public static boolean isEnabled(Context context) {
        return AgentRuntime.get(context).repository().getPlainSetting("location_service_enabled", false);
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createChannel();
        startForeground(NOTIFICATION_ID, buildNotification());
        locationManager = getSystemService(LocationManager.class);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        AgentRuntime runtime = AgentRuntime.get(this);
        boolean consent = "true".equalsIgnoreCase(runtime.repository().loadContextGraph(AgentCore.now())
                .value("consent.location", AgentCore.now()));
        if (!consent || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            runtime.repository().setPlainSetting("location_service_enabled", false);
            stopSelf();
            return START_NOT_STICKY;
        }
        requestUpdates();
        return START_STICKY;
    }

    private void requestUpdates() {
        if (locationManager == null) return;
        if (checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) return;
        try {
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER,
                        MIN_TIME_MS, MIN_DISTANCE_METERS, this, Looper.getMainLooper());
            }
            if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                    && locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER,
                        MIN_TIME_MS, MIN_DISTANCE_METERS, this, Looper.getMainLooper());
            }
            Location last = locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER);
            if (last != null && System.currentTimeMillis() - last.getTime() < 30L * 60 * 1000) {
                onLocationChanged(last);
            }
        } catch (SecurityException | IllegalArgumentException ignored) {
            // Permission or provider state changed after the explicit enable action.
        }
    }

    @Override
    public void onLocationChanged(Location location) {
        if (location == null) return;
        double coarseLat = Math.round(location.getLatitude() * 1000d) / 1000d;
        double coarseLon = Math.round(location.getLongitude() * 1000d) / 1000d;
        String coarse = String.format(Locale.ROOT, "%.3f,%.3f", coarseLat, coarseLon);
        AgentRuntime runtime = AgentRuntime.get(this);
        String previous = runtime.repository().loadContextGraph(AgentCore.now())
                .value("location.coarse", AgentCore.now());
        long now = AgentCore.now();
        runtime.repository().putFact(new AgentCore.ContextFact(
                "location.coarse",
                coarse,
                AgentCore.Sensitivity.SENSITIVE,
                now + 2L * 60 * 60 * 1000,
                true,
                false
        ));
        if (!coarse.equals(previous)) {
            runtime.handleAmbientEvent(new AgentCore.AmbientEvent(
                    null,
                    "location",
                    "location.changed",
                    "대략적 위치가 의미 있게 바뀌었습니다.",
                    getPackageName(),
                    now,
                    Map.of("coarse", "stored_on_device"),
                    AgentCore.Sensitivity.SENSITIVE,
                    true
            ));
        }
    }

    @Override
    public void onProviderEnabled(String provider) {
        requestUpdates();
    }

    @Override
    public void onProviderDisabled(String provider) {
        // Keep the foreground service visible; Android may restore the provider later.
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onStatusChanged(String provider, int status, Bundle extras) {
        // Required for compatibility with older LocationListener contracts.
    }

    @Override
    public void onDestroy() {
        if (locationManager != null) {
            try {
                locationManager.removeUpdates(this);
            } catch (SecurityException ignored) {
                // Permission may have been revoked while active.
            }
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createChannel() {
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager != null && Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(CHANNEL,
                    getString(R.string.location_channel), NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("위치 원문을 외부 광고망에 보내지 않고 대략적 위치만 기기에 저장합니다.");
            manager.createNotificationChannel(channel);
        }
    }

    private Notification buildNotification() {
        Intent open = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                .putExtra(MainActivity.EXTRA_OPEN_PAGE, "home");
        PendingIntent pending = PendingIntent.getActivity(this, 2101, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL)
                : new Notification.Builder(this);
        builder.setSmallIcon(android.R.drawable.ic_menu_mylocation)
                .setContentTitle(getString(R.string.location_active))
                .setContentText("약 100m 단위의 위치를 최대 2시간 동안 기기에만 보관합니다.")
                .setContentIntent(pending)
                .setOnlyAlertOnce(true)
                .setOngoing(true)
                .setCategory(Notification.CATEGORY_SERVICE);
        if (Build.VERSION.SDK_INT < 26) builder.setPriority(Notification.PRIORITY_LOW);
        return builder.build();
    }
}
