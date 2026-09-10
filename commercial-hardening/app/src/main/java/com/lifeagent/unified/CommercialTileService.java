package com.lifeagent.unified;

import android.app.PendingIntent;
import android.content.Intent;
import android.os.Build;
import android.service.quicksettings.TileService;

/** Quick Settings entry to the single goal-first shell. */
public final class CommercialTileService extends TileService {
    @Override
    public void onClick() {
        super.onClick();
        Intent intent = new Intent(this, CommercialMainActivity.class);
        intent.putExtra("lifeagent.os.source", "QUICK_TILE");
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        if (Build.VERSION.SDK_INT >= 34) {
            PendingIntent pendingIntent = PendingIntent.getActivity(
                    this, 3290, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            startActivityAndCollapse(pendingIntent);
        } else {
            @SuppressWarnings("deprecation") Intent legacy = intent;
            startActivityAndCollapse(legacy);
        }
    }
}
