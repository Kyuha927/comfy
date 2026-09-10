package com.lifeagent.unified;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.pdf.PdfRenderer;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.korean.KoreanTextRecognizerOptions;
import com.lifeagent.unified.core.AgentCore;
import com.lifeagent.unified.core.AgentRuntime;
import com.lifeagent.unified.ui.Ui;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Local document intake for insurance preparation. OCR text remains encrypted on the device. */
public final class DocumentIntakeActivity extends Activity {
    private static final int PICK_DOCUMENT = 501;
    private TextView status;
    private TextView preview;
    private Button createTask;
    private Uri selectedUri;
    private String extractedText = "";
    private final TextRecognizer recognizer = TextRecognition.getClient(
            new KoreanTextRecognizerOptions.Builder().build());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        Uri incoming = getIntent().getData();
        if (incoming != null) processUri(incoming, getIntent().getType());
    }

    @Override
    protected void onDestroy() {
        recognizer.close();
        super.onDestroy();
    }

    private void buildUi() {
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(Ui.dp(this, 18), Ui.dp(this, 18), Ui.dp(this, 18), Ui.dp(this, 28));
        body.setBackgroundColor(Ui.CANVAS);
        body.addView(Ui.title(this, "병원 서류 확인"));
        body.addView(Ui.text(this,
                "기기에서 한국어 OCR을 수행하고, 제출 전에 병원·진료일·금액을 사용자가 검토합니다.",
                13.5f, false), Ui.withMargins(this, 5, 14));

        LinearLayout safety = Ui.card(this);
        safety.setBackground(Ui.rounded(Ui.SAGE_SOFT, 18, Ui.SAGE, 1, this));
        safety.addView(Ui.text(this, "의료 문서 보호", 15.5f, true));
        safety.addView(Ui.text(this,
                "클라우드 OCR을 사용하지 않습니다. 주민번호·계좌·인증번호로 보이는 문자열은 미리보기에서 가리고, 실제 모니모 제출은 본인인증과 접수번호 확인이 필요합니다.",
                12.8f, false), Ui.withMargins(this, 5, 0));
        body.addView(safety, Ui.matchWrap());

        Button pick = Ui.primaryButton(this, "사진 또는 PDF 선택");
        pick.setOnClickListener(v -> pickDocument());
        body.addView(pick, Ui.withMargins(this, 15, 8));

        status = Ui.text(this, "아직 선택한 서류가 없습니다.", 14f, true);
        status.setPadding(Ui.dp(this, 12), Ui.dp(this, 10), Ui.dp(this, 12), Ui.dp(this, 10));
        status.setBackground(Ui.rounded(Ui.SURFACE, 12, Ui.DIVIDER, 1, this));
        body.addView(status, Ui.matchWrap());

        body.addView(Ui.section(this, "추출 결과"));
        preview = Ui.text(this, "서류를 선택하면 검토용 요약이 표시됩니다.", 13f, false);
        preview.setTextIsSelectable(true);
        preview.setPadding(Ui.dp(this, 12), Ui.dp(this, 11), Ui.dp(this, 12), Ui.dp(this, 11));
        preview.setBackground(Ui.rounded(Color.WHITE, 14, Ui.DIVIDER, 1, this));
        body.addView(preview, Ui.matchWrap());

        createTask = Ui.primaryButton(this, "보험금 청구 준비 작업 만들기");
        createTask.setEnabled(false);
        createTask.setOnClickListener(v -> createInsuranceTask());
        body.addView(createTask, Ui.withMargins(this, 14, 7));

        Button close = Ui.ghostButton(this, "닫기");
        close.setOnClickListener(v -> finish());
        body.addView(close, Ui.matchWrap());

        ScrollView scroll = new ScrollView(this);
        scroll.addView(body, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        setContentView(scroll);
    }

    private void pickDocument() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"image/*", "application/pdf"});
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        try {
            startActivityForResult(intent, PICK_DOCUMENT);
        } catch (ActivityNotFoundException error) {
            toast("이 기기에서 문서 선택기를 열 수 없습니다.");
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_DOCUMENT && resultCode == RESULT_OK && data != null && data.getData() != null) {
            Uri uri = data.getData();
            try {
                getContentResolver().takePersistableUriPermission(uri,
                        data.getFlags() & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION));
            } catch (SecurityException ignored) {
                // Some providers grant only a temporary read lease, which is sufficient for immediate OCR.
            }
            processUri(uri, getContentResolver().getType(uri));
        }
    }

    private void processUri(Uri uri, String mime) {
        selectedUri = uri;
        createTask.setEnabled(false);
        extractedText = "";
        status.setText("기기에서 문서를 읽는 중입니다…");
        preview.setText("OCR 진행 중");
        String type = mime == null ? "" : mime;
        if (type.equals("application/pdf") || displayName(uri).toLowerCase(Locale.ROOT).endsWith(".pdf")) {
            processPdf(uri);
        } else {
            try {
                InputImage image = InputImage.fromFilePath(this, uri);
                recognize(image, this::finishRecognition, this::showOcrFailure);
            } catch (IOException error) {
                showOcrFailure(error);
            }
        }
    }

    private void processPdf(Uri uri) {
        try {
            ParcelFileDescriptor descriptor = getContentResolver().openFileDescriptor(uri, "r");
            if (descriptor == null) throw new IOException("PDF를 열 수 없습니다");
            PdfRenderer renderer = new PdfRenderer(descriptor);
            if (renderer.getPageCount() == 0) {
                renderer.close();
                descriptor.close();
                throw new IOException("빈 PDF입니다");
            }
            processPdfPage(renderer, descriptor, 0, Math.min(3, renderer.getPageCount()), new StringBuilder());
        } catch (Exception error) {
            showOcrFailure(error);
        }
    }

    private void processPdfPage(PdfRenderer renderer, ParcelFileDescriptor descriptor,
                                int index, int max, StringBuilder accumulated) {
        if (index >= max) {
            renderer.close();
            try { descriptor.close(); } catch (IOException ignored) {}
            finishRecognition(accumulated.toString());
            return;
        }
        PdfRenderer.Page page = renderer.openPage(index);
        int width = Math.min(1800, Math.max(900, page.getWidth() * 2));
        int height = Math.max(1, Math.round((float) width * page.getHeight() / page.getWidth()));
        Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        bitmap.eraseColor(Color.WHITE);
        page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
        InputImage image = InputImage.fromBitmap(bitmap, 0);
        recognize(image, text -> {
            if (accumulated.length() > 0) accumulated.append("\n--- 다음 페이지 ---\n");
            accumulated.append(text);
            bitmap.recycle();
            page.close();
            processPdfPage(renderer, descriptor, index + 1, max, accumulated);
        }, error -> {
            bitmap.recycle();
            page.close();
            renderer.close();
            try { descriptor.close(); } catch (IOException ignored) {}
            showOcrFailure(error);
        });
    }

    private void recognize(InputImage image, TextConsumer success, ErrorConsumer failure) {
        recognizer.process(image)
                .addOnSuccessListener(result -> success.accept(result.getText()))
                .addOnFailureListener(failure::accept);
    }

    private void finishRecognition(String rawText) {
        extractedText = redactMedicalPreview(rawText == null ? "" : rawText);
        if (extractedText.isBlank()) {
            status.setText("문자를 충분히 읽지 못했습니다.");
            preview.setText("사진이 흐리거나 문서가 잘렸을 수 있습니다. 다시 촬영하거나 선명한 PDF를 선택하세요.");
            createTask.setEnabled(false);
            return;
        }
        Summary summary = parseSummary(extractedText);
        status.setText("OCR 완료 · " + displayName(selectedUri));
        preview.setText("병원/기관: " + summary.provider
                + "\n진료일: " + summary.date
                + "\n금액: " + summary.amount
                + "\n\n검토용 OCR 미리보기\n" + truncate(extractedText, 1800));
        createTask.setEnabled(true);
    }

    private void showOcrFailure(Exception error) {
        status.setText("문서를 읽지 못했습니다.");
        preview.setText("다른 파일을 선택하거나 사진을 다시 촬영하세요. 오류: " + error.getClass().getSimpleName());
        createTask.setEnabled(false);
    }

    private void createInsuranceTask() {
        if (extractedText.isBlank()) return;
        Summary summary = parseSummary(extractedText);
        String compact = "병원/기관=" + summary.provider + "; 진료일=" + summary.date
                + "; 금액=" + summary.amount + "; 파일=" + displayName(selectedUri);
        long now = AgentCore.now();
        AgentRuntime runtime = AgentRuntime.get(this);
        runtime.repository().putFact(new AgentCore.ContextFact(
                "insurance.document.summary",
                compact,
                AgentCore.Sensitivity.SENSITIVE,
                now + 30L * 24 * 60 * 60 * 1000,
                true,
                false
        ));
        runtime.handleAmbientEvent(new AgentCore.AmbientEvent(
                null,
                "document",
                "document.shared",
                "병원 서류 OCR 완료: " + compact,
                getPackageName(),
                now,
                Map.of("provider", summary.provider, "date", summary.date, "amount", summary.amount),
                AgentCore.Sensitivity.SENSITIVE,
                true
        ));
        AgentCore.ActionPlan plan = runtime.plan("이 병원 서류로 보험금 청구 준비해줘");
        runtime.acceptPlan(plan);
        new AlertDialog.Builder(this)
                .setTitle("보험금 청구 준비 작업을 만들었습니다")
                .setMessage("OCR 결과는 기기에 암호화했습니다. 다음 단계에서 서류 내용과 수령 계좌를 확인하고, 모니모 본인인증 뒤 실제 접수번호를 받아야 완료됩니다.")
                .setPositiveButton("작업함 보기", (dialog, which) -> {
                    Intent intent = new Intent(this, MainActivity.class)
                            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP)
                            .putExtra(MainActivity.EXTRA_OPEN_PAGE, "tasks");
                    startActivity(intent);
                    finish();
                })
                .show();
    }

    private String redactMedicalPreview(String raw) {
        String cleaned = AgentCore.sanitizeIncoming(raw);
        cleaned = cleaned.replaceAll("(?<!\\d)\\d{6}[- ]?[1-4]\\d{6}(?!\\d)", "[주민번호 숨김]");
        cleaned = cleaned.replaceAll("(?i)(비밀번호|password|otp|인증번호)[^\\n]{0,30}", "$1 [숨김]");
        return cleaned.trim();
    }

    private Summary parseSummary(String text) {
        String provider = "확인 필요";
        String date = "확인 필요";
        String amount = "확인 필요";
        for (String line : text.split("\\R")) {
            String trimmed = line.trim();
            if (trimmed.length() > 1 && trimmed.length() < 60
                    && (trimmed.contains("병원") || trimmed.contains("의원")
                    || trimmed.contains("클리닉") || trimmed.contains("약국"))) {
                provider = trimmed;
                break;
            }
        }
        Matcher dateMatcher = Pattern.compile("20\\d{2}[./-]\\s?\\d{1,2}[./-]\\s?\\d{1,2}").matcher(text);
        if (dateMatcher.find()) date = dateMatcher.group();
        Matcher amountMatcher = Pattern.compile("(?:합계|총액|수납금액|본인부담금)?\\s*([0-9][0-9,]{2,})\\s*원?")
                .matcher(text);
        while (amountMatcher.find()) amount = amountMatcher.group(1) + "원";
        return new Summary(provider, date, amount);
    }

    private String displayName(Uri uri) {
        if (uri == null) return "문서";
        try (android.database.Cursor cursor = getContentResolver().query(uri,
                new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) return cursor.getString(index);
            }
        } catch (RuntimeException ignored) {}
        return "문서";
    }

    private String truncate(String value, int max) {
        return value.length() <= max ? value : value.substring(0, max) + "…";
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    private interface TextConsumer { void accept(String value); }
    private interface ErrorConsumer { void accept(Exception error); }

    private static final class Summary {
        final String provider;
        final String date;
        final String amount;

        Summary(String provider, String date, String amount) {
            this.provider = provider;
            this.date = date;
            this.amount = amount;
        }
    }
}
