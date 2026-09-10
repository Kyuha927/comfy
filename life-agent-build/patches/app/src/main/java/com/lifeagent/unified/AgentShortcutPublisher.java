package com.lifeagent.unified;

import android.content.Context;
import android.content.Intent;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.drawable.Icon;
import android.os.Build;

import java.util.ArrayList;
import java.util.List;

/** Home-screen shortcuts are entry points into the same app, not separate feature apps. */
final class AgentShortcutPublisher {
    private AgentShortcutPublisher() {}

    static void publish(Context context) {
        if (Build.VERSION.SDK_INT < 25) return;
        ShortcutManager manager = context.getSystemService(ShortcutManager.class);
        if (manager == null) return;
        List<ShortcutInfo> shortcuts = new ArrayList<>();
        shortcuts.add(item(context, "delegate", "업무 맡기기", "목표 바로 말하기", "home", ""));
        shortcuts.add(item(context, "document", "문서 처리", "공유한 문서에서 시작", "home", "이 문서를 확인해서 필요한 일을 처리해줘"));
        shortcuts.add(item(context, "automation", "자동화", "내 규칙과 스킬", "automations", ""));
        manager.setDynamicShortcuts(shortcuts);
    }

    private static ShortcutInfo item(Context context, String id, String shortLabel,
                                     String longLabel, String tab, String command) {
        Intent intent = new Intent(context, MainActivity.class)
                .setAction(Intent.ACTION_VIEW)
                .putExtra(AgentOsCore.EXTRA_SOURCE, AgentOsCore.Source.SHORTCUT.name())
                .putExtra(AgentOsCore.EXTRA_TAB, tab)
                .putExtra(AgentOsCore.EXTRA_COMMAND, command);
        return new ShortcutInfo.Builder(context, id)
                .setShortLabel(shortLabel)
                .setLongLabel(longLabel)
                .setIcon(Icon.createWithResource(context, android.R.drawable.ic_menu_send))
                .setIntent(intent)
                .build();
    }
}
