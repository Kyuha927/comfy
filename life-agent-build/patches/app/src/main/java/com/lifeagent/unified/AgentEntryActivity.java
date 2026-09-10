package com.lifeagent.unified;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;

/** Converges share, selected text and deep-link calls onto the one Agent OS shell. */
public final class AgentEntryActivity extends Activity {
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        forward(getIntent());
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        forward(intent);
    }

    private void forward(Intent source) {
        Intent target = new Intent(this, MainActivity.class);
        if (source != null) {
            target.setAction(source.getAction());
            target.setType(source.getType());
            target.setData(source.getData());
            if (source.getExtras() != null) target.putExtras(source.getExtras());
            if (source.getClipData() != null) target.setClipData(source.getClipData());
            target.addFlags(source.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION);
        }
        target.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        startActivity(target);
        finish();
    }
}
