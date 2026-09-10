package com.lifeagent.unified;

import android.content.Context;
import android.content.SharedPreferences;

/** Stores only short non-PII diagnostic codes so failures are visible instead of swallowed. */
final class CommercialDiagnostics {
    private static final String PREFS = "life_agent_diagnostics_v1";
    private static final String KEY_CODE = "last_code";
    private static final String KEY_TIME = "last_time";

    private CommercialDiagnostics() {}

    static void record(Context context, String code) {
        if (context == null) return;
        String safe = code == null ? "UNKNOWN" : code.replaceAll("[^A-Za-z0-9_.-]", "_");
        if (safe.length() > 80) safe = safe.substring(0, 80);
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString(KEY_CODE, safe)
                .putLong(KEY_TIME, System.currentTimeMillis())
                .commit();
    }

    static String last(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String code = prefs.getString(KEY_CODE, "");
        long time = prefs.getLong(KEY_TIME, 0L);
        if (code == null || code.isEmpty() || time <= 0L) return "";
        return code + " @ " + time;
    }

    static void clear(Context context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().commit();
    }
}
