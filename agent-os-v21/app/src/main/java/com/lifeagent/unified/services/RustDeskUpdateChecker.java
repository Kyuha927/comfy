package com.lifeagent.unified.services;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class RustDeskUpdateChecker {
    public interface Callback { void onResult(Result result); }

    public static final class Result {
        public final boolean installed;
        public final String installedVersion;
        public final String latestVersion;
        public final boolean updateAvailable;
        public final String releaseUrl;
        public final String error;

        Result(boolean installed, String installedVersion, String latestVersion,
               boolean updateAvailable, String releaseUrl, String error) {
            this.installed = installed;
            this.installedVersion = installedVersion;
            this.latestVersion = latestVersion;
            this.updateAvailable = updateAvailable;
            this.releaseUrl = releaseUrl;
            this.error = error;
        }

        public String summary() {
            if (!error.isBlank()) return "확인 실패: " + error;
            if (!installed) return "RustDesk가 설치되어 있지 않습니다. 최신 안정판: " + latestVersion;
            if (updateAvailable) return "업데이트 있음: " + installedVersion + " → " + latestVersion;
            return "최신 상태: " + installedVersion;
        }
    }

    private static final String PACKAGE = "com.carriez.flutter_hbb";
    private static final String API = "https://api.github.com/repos/rustdesk/rustdesk/releases/latest";
    private static final int MAX_BYTES = 128 * 1024;
    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor();
    private static final Handler MAIN = new Handler(Looper.getMainLooper());

    private RustDeskUpdateChecker() {}

    public static void checkAsync(Context context, Callback callback) {
        Context app = context.getApplicationContext();
        EXECUTOR.execute(() -> {
            Result result = checkBlocking(app);
            MAIN.post(() -> callback.onResult(result));
        });
    }

    static Result checkBlocking(Context context) {
        String installed = installedVersion(context);
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(API).openConnection();
            connection.setConnectTimeout(12_000);
            connection.setReadTimeout(12_000);
            connection.setInstanceFollowRedirects(false);
            connection.setRequestProperty("Accept", "application/vnd.github+json");
            connection.setRequestProperty("User-Agent", "LifeAgentOS/2.1");
            int code = connection.getResponseCode();
            if (code != 200) return new Result(!installed.isBlank(), installed, "", false, "", "GitHub HTTP " + code);
            byte[] bytes;
            try (BufferedInputStream in = new BufferedInputStream(connection.getInputStream());
                 ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[4096];
                int total = 0;
                int read;
                while ((read = in.read(buffer)) != -1) {
                    total += read;
                    if (total > MAX_BYTES) throw new SecurityException("응답 크기 제한 초과");
                    out.write(buffer, 0, read);
                }
                bytes = out.toByteArray();
            }
            JSONObject json = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
            if (json.optBoolean("draft", true) || json.optBoolean("prerelease", true)) {
                return new Result(!installed.isBlank(), installed, "", false, "", "안정판 응답이 아닙니다");
            }
            String latest = normalizeVersion(json.optString("tag_name", ""));
            String release = json.optString("html_url", "");
            if (latest.isBlank() || !isOfficialRelease(release)) {
                return new Result(!installed.isBlank(), installed, latest, false, "", "공식 릴리스 검증 실패");
            }
            boolean update = !installed.isBlank() && compare(installed, latest) < 0;
            return new Result(!installed.isBlank(), installed, latest, update, release, "");
        } catch (Exception error) {
            return new Result(!installed.isBlank(), installed, "", false, "", error.getClass().getSimpleName());
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static String installedVersion(Context context) {
        try {
            PackageInfo info = context.getPackageManager().getPackageInfo(PACKAGE, 0);
            return normalizeVersion(info.versionName == null ? "" : info.versionName);
        } catch (PackageManager.NameNotFoundException ignored) {
            return "";
        }
    }

    private static boolean isOfficialRelease(String raw) {
        try {
            Uri uri = Uri.parse(raw);
            return "https".equalsIgnoreCase(uri.getScheme())
                    && "github.com".equalsIgnoreCase(uri.getHost())
                    && uri.getPath() != null
                    && uri.getPath().startsWith("/rustdesk/rustdesk/releases/");
        } catch (RuntimeException ignored) {
            return false;
        }
    }

    private static String normalizeVersion(String raw) {
        if (raw == null) return "";
        return raw.trim().toLowerCase(Locale.ROOT)
                .replaceFirst("^[vV]", "")
                .replaceAll("[^0-9.].*$", "");
    }

    private static int compare(String left, String right) {
        List<Integer> a = components(left);
        List<Integer> b = components(right);
        int size = Math.max(a.size(), b.size());
        for (int i = 0; i < size; i++) {
            int x = i < a.size() ? a.get(i) : 0;
            int y = i < b.size() ? b.get(i) : 0;
            if (x != y) return Integer.compare(x, y);
        }
        return 0;
    }

    private static List<Integer> components(String version) {
        List<Integer> values = new ArrayList<>();
        for (String part : version.split("\\.")) {
            try { values.add(Integer.parseInt(part)); }
            catch (NumberFormatException ignored) { values.add(0); }
        }
        return values;
    }
}
