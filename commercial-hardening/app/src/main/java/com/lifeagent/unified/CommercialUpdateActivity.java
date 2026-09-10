package com.lifeagent.unified;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

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

/** User-initiated, official-source-only RustDesk update checker. */
public final class CommercialUpdateActivity extends Activity {
    private static final String API = "https://api.github.com/repos/rustdesk/rustdesk/releases/latest";
    private static final int MAX_RESPONSE_BYTES = 128 * 1024;
    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor();

    private TextView status;
    private Button releaseButton;
    private String releaseUrl = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(22), dp(26), dp(22), dp(26));
        root.setBackgroundColor(Color.rgb(247, 244, 238));

        TextView title = text("RustDesk 업데이트", 26, true, Color.rgb(36, 38, 34));
        root.addView(title, matchWrap());
        root.addView(text(
                "검사 버튼을 눌렀을 때만 공식 GitHub 안정판 정보를 확인합니다. 자동 다운로드나 설치는 하지 않습니다.",
                15, false, Color.rgb(104, 105, 98)), top(8));

        status = text("설치 버전: " + installedVersion(), 16, true, Color.rgb(36, 38, 34));
        status.setPadding(dp(16), dp(16), dp(16), dp(16));
        root.addView(status, top(24));

        Button check = new Button(this);
        check.setAllCaps(false);
        check.setText("공식 안정판 확인");
        check.setTextSize(15);
        check.setOnClickListener(v -> checkNow(check));
        root.addView(check, top(16));

        releaseButton = new Button(this);
        releaseButton.setAllCaps(false);
        releaseButton.setText("공식 릴리스 페이지 열기");
        releaseButton.setEnabled(false);
        releaseButton.setOnClickListener(v -> openRelease());
        root.addView(releaseButton, top(8));

        setContentView(root);
    }

    private void checkNow(Button checkButton) {
        checkButton.setEnabled(false);
        status.setText("공식 안정판을 확인하는 중입니다…");
        releaseButton.setEnabled(false);
        EXECUTOR.execute(() -> {
            Result result = checkBlocking();
            runOnUiThread(() -> {
                checkButton.setEnabled(true);
                status.setText(result.message);
                releaseUrl = result.releaseUrl;
                releaseButton.setEnabled(!releaseUrl.isEmpty());
            });
        });
    }

    private Result checkBlocking() {
        String installed = installedVersion();
        HttpURLConnection connection = null;
        try {
            URL url = new URL(API);
            if (!"https".equalsIgnoreCase(url.getProtocol())
                    || !"api.github.com".equalsIgnoreCase(url.getHost())) {
                return Result.error("공식 호스트 검증 실패");
            }
            connection = (HttpURLConnection) url.openConnection();
            connection.setConnectTimeout(12_000);
            connection.setReadTimeout(12_000);
            connection.setInstanceFollowRedirects(false);
            connection.setRequestProperty("Accept", "application/vnd.github+json");
            connection.setRequestProperty("User-Agent", "Life-Agent-OS/" + CommercialCore.VERSION);
            int code = connection.getResponseCode();
            if (code != 200) return Result.error("GitHub 응답 오류: HTTP " + code);

            byte[] body;
            try (BufferedInputStream in = new BufferedInputStream(connection.getInputStream());
                 ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[4096];
                int total = 0;
                int read;
                while ((read = in.read(buffer)) != -1) {
                    total += read;
                    if (total > MAX_RESPONSE_BYTES) return Result.error("응답 크기 제한 초과");
                    out.write(buffer, 0, read);
                }
                body = out.toByteArray();
            }
            JSONObject json = new JSONObject(new String(body, StandardCharsets.UTF_8));
            if (json.optBoolean("draft", true) || json.optBoolean("prerelease", true)) {
                return Result.error("안정판 응답이 아닙니다");
            }
            String latest = normalizeVersion(json.optString("tag_name", ""));
            String htmlUrl = json.optString("html_url", "");
            if (latest.isEmpty() || !officialReleaseUrl(htmlUrl)) {
                return Result.error("공식 릴리스 검증 실패");
            }
            if (installed.isEmpty()) {
                return new Result("RustDesk가 설치돼 있지 않습니다. 최신 안정판: " + latest, htmlUrl);
            }
            int compare = compareVersions(installed, latest);
            if (compare < 0) {
                return new Result("업데이트가 있습니다: " + installed + " → " + latest, htmlUrl);
            }
            if (compare == 0) {
                return new Result("최신 상태입니다: " + installed, htmlUrl);
            }
            return new Result("설치 버전 " + installed + "이 공개 안정판 " + latest + "보다 새롭습니다.", htmlUrl);
        } catch (Exception error) {
            return Result.error("확인 실패: " + error.getClass().getSimpleName());
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private void openRelease() {
        if (!officialReleaseUrl(releaseUrl)) return;
        startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(releaseUrl)));
    }

    private String installedVersion() {
        try {
            PackageInfo info = getPackageManager().getPackageInfo(CommercialCore.PKG_RUSTDESK, 0);
            return normalizeVersion(info.versionName == null ? "" : info.versionName);
        } catch (PackageManager.NameNotFoundException e) {
            return "";
        }
    }

    private static boolean officialReleaseUrl(String value) {
        if (TextUtils.isEmpty(value)) return false;
        try {
            Uri uri = Uri.parse(value);
            return "https".equalsIgnoreCase(uri.getScheme())
                    && "github.com".equalsIgnoreCase(uri.getHost())
                    && uri.getPath() != null
                    && uri.getPath().startsWith("/rustdesk/rustdesk/releases/");
        } catch (RuntimeException e) {
            return false;
        }
    }

    private static String normalizeVersion(String raw) {
        if (raw == null) return "";
        return raw.trim().toLowerCase(Locale.ROOT)
                .replaceFirst("^[vV]", "")
                .replaceAll("[^0-9.].*$", "");
    }

    private static int compareVersions(String left, String right) {
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
        List<Integer> result = new ArrayList<>();
        for (String part : version.split("\\.")) {
            try {
                result.add(Integer.parseInt(part));
            } catch (NumberFormatException e) {
                result.add(0);
            }
        }
        return result;
    }

    private TextView text(String value, int size, boolean bold, int color) {
        TextView text = new TextView(this);
        text.setText(value);
        text.setTextSize(size);
        text.setTextColor(color);
        text.setLineSpacing(0f, 1.12f);
        if (bold) text.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return text;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams top(int margin) {
        LinearLayout.LayoutParams params = matchWrap();
        params.topMargin = dp(margin);
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private static final class Result {
        final String message;
        final String releaseUrl;

        Result(String message, String releaseUrl) {
            this.message = message;
            this.releaseUrl = releaseUrl;
        }

        static Result error(String message) {
            return new Result(message, "");
        }
    }
}
