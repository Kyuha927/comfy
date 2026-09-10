package com.lifeagent.unified;

import android.app.PendingIntent;
import android.content.Intent;
import android.os.Build;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;

/** OS-level one-tap entry from Android Quick Settings. */
public final class LifeAgentTileService extends TileService {
    @Override public void onStartListening() {
        super.onStartListening();
        Tile tile = getQsTile();
        if (tile != null) {
            tile.setLabel("Life Agent");
            if (Build.VERSION.SDK_INT >= 29) tile.setSubtitle("업무 맡기기");
            tile.setState(Tile.STATE_ACTIVE);
            tile.updateTile();
        }
    }

    @Override public void onClick() {
        super.onClick();
        Intent intent = new Intent(this, MainActivity.class)
                .putExtra(AgentOsCore.EXTRA_SOURCE, AgentOsCore.Source.QUICK_TILE.name())
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        if (Build.VERSION.SDK_INT >= 34) {
            PendingIntent pending = PendingIntent.getActivity(this, 2201, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            startActivityAndCollapse(pending);
        } else {
            @SuppressWarnings("deprecation") Intent legacy = intent;
            startActivityAndCollapse(legacy);
        }
    }
}
