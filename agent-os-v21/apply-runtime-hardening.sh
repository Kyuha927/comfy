#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?project root required}"
python3 - "$ROOT" <<'PY'
from pathlib import Path
import re, sys
root = Path(sys.argv[1])
java_root = root / "app/src/main/java"

# Android 11 compatibility: avoid calling String.isBlank(), which is not uniformly available
# on all Android 11 builds. All uses here are non-null or explicitly null-guarded strings.
for path in java_root.rglob("*.java"):
    text = path.read_text(encoding="utf-8")
    text = text.replace(".isBlank()", ".trim().isEmpty()")
    path.write_text(text, encoding="utf-8")

# ShareReceiverActivity: use the version-safe Parcelable API on Android 11/12.
share = java_root / "com/lifeagent/unified/ShareReceiverActivity.java"
text = share.read_text(encoding="utf-8")
text = text.replace(
    '            Uri stream = incoming.getParcelableExtra(Intent.EXTRA_STREAM, Uri.class);',
    '''            Uri stream;
            if (android.os.Build.VERSION.SDK_INT >= 33) {
                stream = incoming.getParcelableExtra(Intent.EXTRA_STREAM, Uri.class);
            } else {
                @SuppressWarnings("deprecation")
                Uri legacyStream = incoming.getParcelableExtra(Intent.EXTRA_STREAM);
                stream = legacyStream;
            }''')
share.write_text(text, encoding="utf-8")

# Autofill: Dataset.Builder takes the menu presentation in the constructor. This works from
# API 26 onward and avoids the non-existent setPresentation call.
autofill = java_root / "com/lifeagent/unified/services/LifeAgentAutofillService.java"
text = autofill.read_text(encoding="utf-8")
text = text.replace(
    '            Dataset.Builder dataset = new Dataset.Builder();\n            int filled = 0;',
    '''            RemoteViews responsePresentation = new RemoteViews(getPackageName(), android.R.layout.simple_list_item_1);
            responsePresentation.setTextViewText(android.R.id.text1, "Life Agent 개인정보 금고");
            Dataset.Builder dataset = new Dataset.Builder(responsePresentation);
            int filled = 0;''')
text = text.replace(
    '''            RemoteViews responsePresentation = new RemoteViews(getPackageName(), android.R.layout.simple_list_item_1);
            responsePresentation.setTextViewText(android.R.id.text1, "Life Agent 개인정보 금고");
            dataset.setPresentation(responsePresentation);
            FillResponse response = new FillResponse.Builder().addDataset(dataset.build()).build();''',
    '''            FillResponse response = new FillResponse.Builder().addDataset(dataset.build()).build();''')
autofill.write_text(text, encoding="utf-8")

# Vault: reject exact PIN concepts, not innocent words such as "shopping" containing p-i-n.
vault = java_root / "com/lifeagent/unified/security/SecureVault.java"
text = vault.read_text(encoding="utf-8")
text = text.replace(
    '                || combined.contains("pin")\n',
    '                || normalizedKey.equals("pin")\n                || normalizedKey.endsWith(".pin")\n                || normalizedKey.endsWith("_pin")\n                || normalizedValue.matches("(?i).*\\\\bpin\\\\b.*")\n')
vault.write_text(text, encoding="utf-8")

# Opportunity feed: honor snooze and per-skill hide decisions.
runtime = java_root / "com/lifeagent/unified/core/AgentRuntime.java"
text = runtime.read_text(encoding="utf-8")
old = '''    public List<AgentCore.Opportunity> opportunities() {
        long now = AgentCore.now();
        AgentCore.PersonalContextGraph graph = repository.loadContextGraph(now);
        AgentCore.AmbientEvent event = repository.latestEvent(now);
        return opportunityEngine.evaluate(graph, event, now);
    }'''
new = '''    public List<AgentCore.Opportunity> opportunities() {
        long now = AgentCore.now();
        AgentCore.PersonalContextGraph graph = repository.loadContextGraph(now);
        AgentCore.AmbientEvent event = repository.latestEvent(now);
        List<AgentCore.Opportunity> visible = new ArrayList<>();
        for (AgentCore.Opportunity opportunity : opportunityEngine.evaluate(graph, event, now)) {
            if (repository.getPlainSetting("disabled_opportunity_" + opportunity.skillId, false)) continue;
            long snoozeUntil = parseLong(repository.getPlainString("snooze_" + opportunity.id, "0"));
            if (snoozeUntil > now) continue;
            visible.add(opportunity);
        }
        return Collections.unmodifiableList(visible);
    }'''
if old not in text:
    raise SystemExit("AgentRuntime opportunities block not found")
text = text.replace(old, new)
text = text.replace(
    '''    private static int parseInt(String raw) {
        try {
            return Integer.parseInt(raw);
        } catch (Exception ignored) {
            return 0;
        }
    }''',
    '''    private static int parseInt(String raw) {
        try {
            return Integer.parseInt(raw);
        } catch (Exception ignored) {
            return 0;
        }
    }

    private static long parseLong(String raw) {
        try {
            return Long.parseLong(raw);
        } catch (Exception ignored) {
            return 0L;
        }
    }''')
runtime.write_text(text, encoding="utf-8")

# Opportunity card: expose the four recurring decisions without hiding them in a submenu.
main = java_root / "com/lifeagent/unified/MainActivity.java"
text = main.read_text(encoding="utf-8")
needle = '''        card.addView(actions, Ui.withMargins(this, 12, 0));
        return card;
    }

    private LinearLayout taskCard'''
replacement = '''        card.addView(actions, Ui.withMargins(this, 12, 0));
        LinearLayout preferenceActions = Ui.horizontal(this);
        Button automate = Ui.ghostButton(this, "다음부터 자동");
        automate.setEnabled(!opportunity.commercial
                && opportunity.kind != AgentCore.OpportunityKind.URGENT);
        automate.setOnClickListener(v -> {
            AgentCore.SkillManifest skill = runtime.skills().get(opportunity.skillId);
            if (skill == null) return;
            AgentCore.PolicyDecision maximum = skill.risk == AgentCore.Risk.LOW
                    ? AgentCore.PolicyDecision.AUTO : AgentCore.PolicyDecision.CONFIRM;
            repository.saveRecipe(new AgentCore.Recipe(UUID.randomUUID().toString(),
                    opportunity.title + " 자동화", "goal", Map.of("summary_contains", opportunity.title),
                    skill.id, maximum, skill.verificationEvidence, true));
            toast(maximum == AgentCore.PolicyDecision.AUTO
                    ? "저위험 범위에서 다음부터 자동으로 처리합니다."
                    : "다음부터 준비하되 실행 전 확인을 받습니다.");
        });
        preferenceActions.addView(automate, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        Button hide = Ui.ghostButton(this, "이런 추천 끄기");
        hide.setOnClickListener(v -> {
            repository.setPlainSetting("disabled_opportunity_" + opportunity.skillId, true);
            toast("같은 종류의 추천을 숨겼습니다.");
            showPage(Page.HOME);
        });
        LinearLayout.LayoutParams hideParams = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        hideParams.leftMargin = Ui.dp(this, 6);
        preferenceActions.addView(hide, hideParams);
        card.addView(preferenceActions, Ui.withMargins(this, 6, 0));
        return card;
    }

    private LinearLayout taskCard'''
if needle not in text:
    raise SystemExit("MainActivity opportunity card insertion point not found")
text = text.replace(needle, replacement)
main.write_text(text, encoding="utf-8")
PY

grep -R -q 'Dataset.Builder(responsePresentation)' "$ROOT/app/src/main/java"
! grep -R -q '\.isBlank()' "$ROOT/app/src/main/java"
grep -R -q 'disabled_opportunity_' "$ROOT/app/src/main/java"
grep -R -q '다음부터 자동' "$ROOT/app/src/main/java"
