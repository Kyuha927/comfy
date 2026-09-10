package com.lifeagent.unified;

import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;

import com.lifeagent.unified.core.AgentCore;
import com.lifeagent.unified.core.AgentRuntime;

import java.util.Map;

/** Share and selected-text entry point. It stores only a sanitized summary and content reference. */
public final class ShareReceiverActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        handle(getIntent());
        finish();
    }

    private void handle(Intent incoming) {
        if (incoming == null) return;
        String action = incoming.getAction();
        String mime = incoming.getType() == null ? "" : incoming.getType();
        String summary = "";
        String eventType = "share.text";

        if (Intent.ACTION_PROCESS_TEXT.equals(action)) {
            CharSequence text = incoming.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT);
            summary = text == null ? "선택한 텍스트" : text.toString();
        } else if (Intent.ACTION_SEND.equals(action)) {
            CharSequence text = incoming.getCharSequenceExtra(Intent.EXTRA_TEXT);
            Uri stream = incoming.getParcelableExtra(Intent.EXTRA_STREAM, Uri.class);
            if (stream != null) {
                eventType = "document.shared";
                String displayName = displayName(stream);
                summary = "공유 문서: " + (displayName.isBlank() ? mime : displayName);
                AgentRuntime.get(this).repository().setPlainString("pending_shared_uri", stream.toString());
                AgentRuntime.get(this).repository().setPlainString("pending_shared_mime", mime);
            } else if (text != null) {
                summary = text.toString();
            }
        }

        summary = AgentCore.sanitizeIncoming(summary);
        if (summary.length() > 800) summary = summary.substring(0, 800) + "…";
        long now = AgentCore.now();
        AgentRuntime runtime = AgentRuntime.get(this);
        runtime.repository().putFact(new AgentCore.ContextFact(
                "context.shared.summary",
                summary,
                eventType.equals("document.shared") ? AgentCore.Sensitivity.SENSITIVE : AgentCore.Sensitivity.PERSONAL,
                now + 24L * 60 * 60 * 1000,
                true,
                false
        ));
        runtime.handleAmbientEvent(new AgentCore.AmbientEvent(
                null,
                "share",
                eventType,
                summary,
                getCallingPackage() == null ? "" : getCallingPackage(),
                now,
                Map.of("mime", mime),
                eventType.equals("document.shared") ? AgentCore.Sensitivity.SENSITIVE : AgentCore.Sensitivity.PERSONAL,
                true
        ));

        Intent launch = new Intent(this, MainActivity.class);
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        launch.putExtra(MainActivity.EXTRA_PREFILL,
                eventType.equals("document.shared") ? "이 문서를 확인해서 필요한 일을 처리해줘" : "이 내용을 처리해줘");
        startActivity(launch);
    }

    private String displayName(Uri uri) {
        try (Cursor cursor = getContentResolver().query(uri,
                new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int column = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (column >= 0) return cursor.getString(column);
            }
        } catch (RuntimeException ignored) {
            // A content provider may decline metadata. The URI itself is not exposed in the UI.
        }
        return "";
    }
}
