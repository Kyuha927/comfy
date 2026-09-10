package com.lifeagent.unified;

import android.app.Activity;
import android.os.Bundle;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Safe landing surface when a goal has not resolved to one specific skill yet. */
public final class GeneralTaskActivity extends Activity {
    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(AgentUi.dp(this, 24), AgentUi.dp(this, 32), AgentUi.dp(this, 24), AgentUi.dp(this, 32));
        root.setBackgroundColor(AgentUi.CANVAS);
        root.addView(AgentUi.text(this, "LIFE AGENT OS", 12, true, AgentUi.SAGE_DARK), AgentUi.matchWrap());
        TextView title = AgentUi.text(this, "업무를 작업 그래프에 담았습니다", 26, true, AgentUi.INK);
        title.setPadding(0, AgentUi.dp(this, 10), 0, AgentUi.dp(this, 12));
        root.addView(title, AgentUi.matchWrap());
        String command = getIntent().getStringExtra(AgentOsCore.EXTRA_COMMAND);
        String summary = getIntent().getStringExtra(AgentOsCore.EXTRA_CONTEXT);
        TextView body = AgentUi.text(this,
                (command == null || command.trim().isEmpty() ? "맡긴 업무" : command.trim())
                        + (summary == null || summary.trim().isEmpty() ? "" : "\n\n현재 문맥\n" + summary)
                        + "\n\n현재는 안전한 계획 단계입니다. 외부 제출이나 인증이 필요한 시점에는 작업함에서 다시 확인을 요청합니다.",
                16, false, AgentUi.INK_SOFT);
        body.setLineSpacing(0, 1.25f);
        root.addView(AgentUi.card(this, body, AgentUi.SURFACE), AgentUi.matchWrap());
        root.addView(AgentUi.primary(this, "작업함으로 돌아가기", view -> finish()), AgentUi.spaced(this, 14, 0));
        setContentView(root, new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }
}
