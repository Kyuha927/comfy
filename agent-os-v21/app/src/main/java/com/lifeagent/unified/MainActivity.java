package com.lifeagent.unified;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.KeyguardManager;
import android.app.NotificationManager;
import android.content.ActivityNotFoundException;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.speech.RecognizerIntent;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodManager;
import android.view.autofill.AutofillManager;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import com.lifeagent.unified.core.AgentCore;
import com.lifeagent.unified.core.AgentRuntime;
import com.lifeagent.unified.data.AgentRepository;
import com.lifeagent.unified.services.LocationContextService;
import com.lifeagent.unified.services.UnifiedNotificationListener;
import com.lifeagent.unified.ui.Ui;

import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class MainActivity extends Activity {
    public static final String EXTRA_PREFILL = "life_agent_prefill";
    public static final String EXTRA_OPEN_PAGE = "life_agent_open_page";

    private static final int REQUEST_VOICE = 401;
    private static final int REQUEST_LOCATION = 402;
    private static final int REQUEST_NOTIFICATIONS = 403;
    private static final int REQUEST_DEVICE_CREDENTIAL = 404;

    private enum Page { HOME, TASKS, AUTOMATIONS, ME }

    private AgentRuntime runtime;
    private AgentRepository repository;
    private LinearLayout pageHost;
    private LinearLayout bottomNav;
    private EditText commandInput;
    private Page currentPage = Page.HOME;
    private String pendingCredentialTaskId = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        runtime = AgentRuntime.get(this);
        repository = runtime.repository();
        buildShell();
        consumeIntent(getIntent());
        showPage(currentPage);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        consumeIntent(intent);
        showPage(Page.HOME);
    }

    @Override
    protected void onResume() {
        super.onResume();
        showPage(currentPage);
    }

    private void buildShell() {
        getWindow().setStatusBarColor(Ui.CANVAS);
        getWindow().setNavigationBarColor(Ui.SURFACE);
        if (Build.VERSION.SDK_INT >= 23) {
            getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        }

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Ui.CANVAS);

        pageHost = new LinearLayout(this);
        pageHost.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams hostParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
        root.addView(pageHost, hostParams);

        bottomNav = Ui.horizontal(this);
        bottomNav.setPadding(Ui.dp(this, 6), Ui.dp(this, 5), Ui.dp(this, 6), Ui.dp(this, 7));
        bottomNav.setBackground(Ui.rounded(Ui.SURFACE, 0, Ui.DIVIDER, 1, this));
        root.addView(bottomNav, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        setContentView(root);
    }

    private void consumeIntent(Intent intent) {
        if (intent == null) return;
        String open = intent.getStringExtra(EXTRA_OPEN_PAGE);
        if (open != null) {
            try {
                currentPage = Page.valueOf(open.toUpperCase(Locale.ROOT));
            } catch (IllegalArgumentException ignored) {
                currentPage = Page.HOME;
            }
        }
        String prefill = intent.getStringExtra(EXTRA_PREFILL);
        if ((prefill == null || prefill.isBlank()) && intent.getData() != null
                && "lifeagent".equals(intent.getData().getScheme())) {
            prefill = intent.getData().getQueryParameter("q");
        }
        if (prefill != null && !prefill.isBlank()) {
            repository.setPlainString("pending_goal", AgentCore.sanitizeIncoming(prefill));
            currentPage = Page.HOME;
        }
    }

    private void showPage(Page page) {
        currentPage = page;
        pageHost.removeAllViews();
        bottomNav.removeAllViews();
        View body;
        switch (page) {
            case TASKS:
                body = buildTasksPage();
                break;
            case AUTOMATIONS:
                body = buildAutomationsPage();
                break;
            case ME:
                body = buildMePage();
                break;
            case HOME:
            default:
                body = buildHomePage();
                break;
        }
        pageHost.addView(body, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        addNavButton("홈", Page.HOME, "⌂");
        addNavButton("작업함", Page.TASKS, "☷");
        addNavButton("자동화", Page.AUTOMATIONS, "⚡");
        addNavButton("내 정보", Page.ME, "●");
    }

    private void addNavButton(String label, Page page, String icon) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(icon + "\n" + label);
        button.setTextSize(11.5f);
        button.setMinHeight(Ui.dp(this, 58));
        button.setGravity(Gravity.CENTER);
        button.setStateListAnimator(null);
        button.setTextColor(currentPage == page ? Ui.TERRA : Ui.MUTED);
        button.setTypeface(Typeface.DEFAULT, currentPage == page ? Typeface.BOLD : Typeface.NORMAL);
        button.setBackgroundColor(Color.TRANSPARENT);
        button.setContentDescription(label + (currentPage == page ? ", 선택됨" : ""));
        button.setOnClickListener(v -> showPage(page));
        bottomNav.addView(button, new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
    }

    private View buildHomePage() {
        LinearLayout body = pageBody();
        LinearLayout header = Ui.horizontal(this);
        LinearLayout heading = new LinearLayout(this);
        heading.setOrientation(LinearLayout.VERTICAL);
        heading.addView(Ui.title(this, "Life Agent OS"));
        heading.addView(Ui.text(this, "앱이 아니라, 내 일을 이어서 처리하는 개인 실행 레이어", 13f, false));
        header.addView(heading, Ui.weighted());
        TextView privacy = Ui.chip(this, "기기 중심", Ui.SAGE_SOFT);
        privacy.setContentDescription("개인정보는 기기 중심으로 처리됩니다");
        header.addView(privacy);
        body.addView(header, Ui.matchWrap());

        LinearLayout commandCard = Ui.card(this);
        commandCard.setBackground(Ui.rounded(Color.WHITE, 22, Ui.SAGE, 1, this));
        TextView prompt = Ui.text(this, "무엇을 맡길까요?", 18f, true);
        commandCard.addView(prompt, Ui.matchWrap());
        commandInput = new EditText(this);
        commandInput.setHint("예: 금요일 오후 정형외과 예약하고 결과를 일정에 넣어줘");
        commandInput.setTextSize(16f);
        commandInput.setTextColor(Ui.INK);
        commandInput.setHintTextColor(Ui.MUTED);
        commandInput.setMinHeight(Ui.dp(this, 92));
        commandInput.setGravity(Gravity.TOP | Gravity.START);
        commandInput.setPadding(0, Ui.dp(this, 10), 0, Ui.dp(this, 8));
        commandInput.setBackgroundColor(Color.TRANSPARENT);
        commandInput.setSingleLine(false);
        String pending = repository.getPlainString("pending_goal", "");
        if (!pending.isBlank()) {
            commandInput.setText(pending);
            repository.setPlainString("pending_goal", "");
        }
        commandCard.addView(commandInput, Ui.matchWrap());

        LinearLayout commandActions = Ui.horizontal(this);
        Button voice = Ui.ghostButton(this, "음성");
        voice.setContentDescription("음성으로 목표 입력");
        voice.setOnClickListener(v -> startVoiceInput());
        commandActions.addView(voice, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        commandActions.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
        Button plan = Ui.primaryButton(this, "처리 계획 보기");
        plan.setContentDescription("목표에 대한 처리 계획 보기");
        plan.setOnClickListener(v -> planGoal());
        commandActions.addView(plan, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        commandCard.addView(commandActions, Ui.withMargins(this, 2, 0));
        body.addView(commandCard, Ui.withMargins(this, 18, 0));

        body.addView(Ui.section(this, "현재 문맥"));
        LinearLayout contextRow = Ui.horizontal(this);
        contextRow.setBaselineAligned(false);
        contextRow.addView(statusChip("알림", notificationAccessEnabled()),
                new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        contextRow.addView(statusChip("위치", LocationContextService.isEnabled(this)),
                spacedWeight());
        AgentCore.PersonalContextGraph graph = repository.loadContextGraph(AgentCore.now());
        boolean shared = graph.get("context.shared.summary", AgentCore.now()) != null;
        contextRow.addView(statusChip("공유 문맥", shared), spacedWeight());
        body.addView(contextRow, Ui.matchWrap());

        List<AgentRepository.StoredTask> tasks = repository.listTasks();
        List<AgentRepository.StoredTask> needsUser = filterTasks(tasks, true);
        if (!needsUser.isEmpty()) {
            body.addView(Ui.section(this, "내 확인이 필요한 일"));
            for (int i = 0; i < Math.min(3, needsUser.size()); i++) {
                body.addView(taskCard(needsUser.get(i), true), Ui.withMargins(this, 0, 9));
            }
        }

        body.addView(Ui.section(this, "지금 발견한 기회"));
        List<AgentCore.Opportunity> opportunities = runtime.opportunities();
        if (opportunities.isEmpty()) {
            body.addView(emptyCard("아직 조용합니다",
                    "위치·알림·자격 프로필은 모두 사용자가 켠 범위에서만 기회를 만듭니다."),
                    Ui.matchWrap());
        } else {
            for (int i = 0; i < Math.min(4, opportunities.size()); i++) {
                body.addView(opportunityCard(opportunities.get(i)), Ui.withMargins(this, 0, 9));
            }
        }

        List<AgentRepository.StoredTask> active = filterTasks(tasks, false);
        if (!active.isEmpty()) {
            body.addView(Ui.section(this, "진행 중"));
            for (int i = 0; i < Math.min(3, active.size()); i++) {
                body.addView(taskCard(active.get(i), false), Ui.withMargins(this, 0, 9));
            }
            Button all = Ui.ghostButton(this, "작업함 전체 보기");
            all.setOnClickListener(v -> showPage(Page.TASKS));
            body.addView(all, Ui.withMargins(this, 2, 16));
        }

        body.addView(Ui.space(this, 20));
        return Ui.scrollPage(this, body);
    }

    private View buildTasksPage() {
        LinearLayout body = pageBody();
        body.addView(Ui.title(this, "작업함"));
        TextView subtitle = Ui.text(this,
                "앱이 닫혀도 목표·단계·실패 원인·다음 행동을 이어서 보관합니다.", 13.5f, false);
        subtitle.setPadding(0, Ui.dp(this, 5), 0, 0);
        body.addView(subtitle, Ui.matchWrap());

        List<AgentRepository.StoredTask> tasks = repository.listTasks();
        if (tasks.isEmpty()) {
            body.addView(Ui.space(this, 24));
            body.addView(emptyCard("아직 맡긴 일이 없습니다",
                    "홈에서 목표를 입력하면 먼저 계획과 승인 범위를 보여드립니다."), Ui.matchWrap());
        } else {
            String lastGroup = "";
            for (AgentRepository.StoredTask task : tasks) {
                String group = taskGroup(task.status);
                if (!group.equals(lastGroup)) {
                    body.addView(Ui.section(this, group));
                    lastGroup = group;
                }
                body.addView(taskCard(task, true), Ui.withMargins(this, 0, 9));
            }
        }
        body.addView(Ui.space(this, 24));
        return Ui.scrollPage(this, body);
    }

    private View buildAutomationsPage() {
        LinearLayout body = pageBody();
        body.addView(Ui.title(this, "스킬과 자동화"));
        TextView subtitle = Ui.text(this,
                "개별 앱 기능이 아니라 Trigger → 조건 → 스킬 → 검증을 조합합니다.", 13.5f, false);
        subtitle.setPadding(0, Ui.dp(this, 5), 0, 0);
        body.addView(subtitle, Ui.matchWrap());

        LinearLayout explanation = Ui.card(this);
        explanation.setBackground(Ui.rounded(Ui.SAGE_SOFT, 18, Ui.SAGE, 1, this));
        explanation.addView(Ui.text(this, "자동 실행 원칙", 16f, true));
        explanation.addView(Ui.text(this,
                "검증된 저위험 반복 작업은 모델 없이 실행합니다. 화면 변화·실패가 있을 때만 더 강한 실행기로 올리고, 송금·인증·외부 제출은 정책 커널이 확인을 유지합니다.",
                13.5f, false), Ui.withMargins(this, 6, 0));
        body.addView(explanation, Ui.withMargins(this, 18, 0));

        body.addView(Ui.section(this, "내 자동화"));
        List<AgentCore.Recipe> recipes = repository.listRecipes();
        for (AgentCore.Recipe recipe : recipes) {
            body.addView(recipeCard(recipe), Ui.withMargins(this, 0, 8));
        }
        Button addRecipe = Ui.primaryButton(this, "새 자동화 만들기");
        addRecipe.setOnClickListener(v -> showRecipeBuilder());
        body.addView(addRecipe, Ui.withMargins(this, 3, 6));

        body.addView(Ui.section(this, "설치된 스킬"));
        for (AgentCore.SkillManifest skill : runtime.skills().all()) {
            body.addView(skillCard(skill), Ui.withMargins(this, 0, 8));
        }
        body.addView(Ui.space(this, 20));
        return Ui.scrollPage(this, body);
    }

    private View buildMePage() {
        LinearLayout body = pageBody();
        body.addView(Ui.title(this, "내 정보와 권한"));
        TextView subtitle = Ui.text(this,
                "어떤 문맥을 기억하고 어디까지 자동화할지 직접 정합니다.", 13.5f, false);
        subtitle.setPadding(0, Ui.dp(this, 5), 0, 0);
        body.addView(subtitle, Ui.matchWrap());

        body.addView(Ui.section(this, "개인정보 금고"));
        LinearLayout profileCard = Ui.card(this);
        EditText name = field("이름", graphValue("profile.name"));
        EditText email = field("이메일", graphValue("profile.email"));
        EditText phone = field("전화번호", graphValue("profile.phone"));
        EditText address = field("주소", graphValue("profile.address"));
        EditText region = field("거주 지역", graphValue("profile.region"));
        EditText ageBand = field("연령대 예: 30대", graphValue("profile.age_band"));
        EditText healthInterest = field("최근 관심 문맥 예: 영양제, 비타민", graphValue("context.health_interest"));
        EditText shoppingInterest = field("직접 저장한 쇼핑 관심사", graphValue("interest.shopping"));
        for (EditText field : List.of(name, email, phone, address, region, ageBand, healthInterest, shoppingInterest)) {
            profileCard.addView(field, Ui.withMargins(this, 0, 8));
        }
        Button save = Ui.primaryButton(this, "암호화하여 저장");
        save.setOnClickListener(v -> {
            try {
                putFact("profile.name", name.getText().toString(), AgentCore.Sensitivity.SENSITIVE, false);
                putFact("profile.email", email.getText().toString(), AgentCore.Sensitivity.SENSITIVE, false);
                putFact("profile.phone", phone.getText().toString(), AgentCore.Sensitivity.SENSITIVE, false);
                putFact("profile.address", address.getText().toString(), AgentCore.Sensitivity.SENSITIVE, false);
                putFact("profile.region", region.getText().toString(), AgentCore.Sensitivity.PERSONAL, false);
                putFact("profile.age_band", ageBand.getText().toString(), AgentCore.Sensitivity.PERSONAL, false);
                putFact("context.health_interest", healthInterest.getText().toString(), AgentCore.Sensitivity.SENSITIVE, false);
                putFact("interest.shopping", shoppingInterest.getText().toString(), AgentCore.Sensitivity.PERSONAL, true);
                toast("개인정보 금고에 암호화하여 저장했습니다.");
                hideKeyboard();
                showPage(Page.ME);
            } catch (SecurityException error) {
                alert("저장하지 않았습니다", error.getMessage());
            }
        });
        profileCard.addView(save, Ui.withMargins(this, 3, 0));
        profileCard.addView(Ui.text(this,
                "비밀번호·OTP·PIN·CVV·복구코드·개인키는 입력해도 저장되지 않습니다.", 12.5f, false),
                Ui.withMargins(this, 8, 0));
        body.addView(profileCard, Ui.matchWrap());

        body.addView(Ui.section(this, "상시 문맥"));
        LinearLayout consentCard = Ui.card(this);
        CheckBox notificationConsent = consentToggle("메시지·알림에서 필요한 일 찾기",
                factBoolean("consent.notifications"));
        notificationConsent.setOnCheckedChangeListener((button, checked) -> {
            setConsent("consent.notifications", checked);
            if (checked && !notificationAccessEnabled()) openNotificationSettings();
        });
        consentCard.addView(notificationConsent, Ui.matchWrap());
        TextView notificationHelp = Ui.text(this,
                "원문 전체를 장기 저장하지 않고 기기에서 의미를 추출한 뒤 민감 문자열을 가립니다.", 12.5f, false);
        notificationHelp.setPadding(Ui.dp(this, 34), 0, 0, Ui.dp(this, 10));
        consentCard.addView(notificationHelp, Ui.matchWrap());

        CheckBox locationConsent = consentToggle("이동 중 위치 기반 기회 찾기",
                factBoolean("consent.location"));
        locationConsent.setOnCheckedChangeListener((button, checked) -> {
            if (checked) enableLocationContext();
            else {
                setConsent("consent.location", false);
                LocationContextService.stop(this);
                toast("위치 기반 기회 감지를 껐습니다.");
            }
        });
        consentCard.addView(locationConsent, Ui.matchWrap());
        TextView locationHelp = Ui.text(this,
                "사용자가 켠 동안 포그라운드 서비스로 작동하며 약 100m 단위의 대략적 위치만 짧게 보관합니다.",
                12.5f, false);
        locationHelp.setPadding(Ui.dp(this, 34), 0, 0, Ui.dp(this, 10));
        consentCard.addView(locationHelp, Ui.matchWrap());

        CheckBox commercialConsent = consentToggle("상업 추천 허용", factBoolean("consent.commercial"));
        commercialConsent.setOnCheckedChangeListener((button, checked) -> {
            if (checked) {
                new AlertDialog.Builder(this)
                        .setTitle("상업 추천을 켤까요?")
                        .setMessage("건강·보험·금융·가족·메시지 원문·정확한 위치는 광고에 사용하지 않습니다. 직접 저장한 비민감 관심사만 사용할 수 있습니다.")
                        .setNegativeButton("취소", (dialog, which) -> commercialConsent.setChecked(false))
                        .setPositiveButton("허용", (dialog, which) -> setConsent("consent.commercial", true))
                        .show();
            } else {
                setConsent("consent.commercial", false);
            }
        });
        consentCard.addView(commercialConsent, Ui.matchWrap());
        body.addView(consentCard, Ui.matchWrap());

        body.addView(Ui.section(this, "시스템 연결"));
        LinearLayout systemCard = Ui.card(this);
        systemCard.addView(connectionRow("알림 접근", notificationAccessEnabled(), this::openNotificationSettings));
        systemCard.addView(Ui.divider(this));
        systemCard.addView(connectionRow("개인정보 자동입력", autofillEnabled(), this::openAutofillSettings));
        systemCard.addView(Ui.divider(this));
        systemCard.addView(connectionRow("위치 문맥", LocationContextService.isEnabled(this), () -> {
            if (LocationContextService.isEnabled(this)) {
                LocationContextService.stop(this);
                setConsent("consent.location", false);
            } else enableLocationContext();
            showPage(Page.ME);
        }));
        body.addView(systemCard, Ui.matchWrap());

        body.addView(Ui.section(this, "AI·PC 실행기"));
        LinearLayout connectorCard = Ui.card(this);
        connectorCard.addView(Ui.text(this, "공식 구독 클라이언트", 15.5f, true));
        connectorCard.addView(Ui.text(this,
                "Claude Code·Kimi Code·CodeBuddy 등은 토큰을 빼내지 않고 PC Companion이 공식 클라이언트를 호출하는 방식으로 연결합니다.",
                13f, false), Ui.withMargins(this, 5, 8));
        EditText companion = field("PC·Mac Companion HTTPS 주소",
                repository.getPlainString("companion_endpoint", ""));
        connectorCard.addView(companion, Ui.matchWrap());
        Button saveConnection = Ui.secondaryButton(this, "연결 주소 저장");
        saveConnection.setOnClickListener(v -> {
            String endpoint = companion.getText().toString().trim();
            if (!endpoint.isEmpty() && !endpoint.startsWith("https://")) {
                alert("저장하지 않았습니다", "Companion은 HTTPS 주소만 허용합니다.");
                return;
            }
            repository.setPlainString("companion_endpoint", endpoint);
            toast(endpoint.isEmpty() ? "Companion 연결을 비웠습니다." : "HTTPS 연결 주소를 저장했습니다.");
        });
        connectorCard.addView(saveConnection, Ui.withMargins(this, 8, 0));
        body.addView(connectorCard, Ui.matchWrap());

        body.addView(Ui.section(this, "투명성 및 삭제"));
        LinearLayout dataCard = Ui.card(this);
        Button inspect = Ui.ghostButton(this, "기억한 문맥과 사용 이유 보기");
        inspect.setOnClickListener(v -> showContextTransparency());
        dataCard.addView(inspect, Ui.matchWrap());
        Button wipe = Ui.ghostButton(this, "기기 데이터 전체 삭제");
        wipe.setTextColor(Color.rgb(145, 54, 45));
        wipe.setOnClickListener(v -> confirmWipe());
        dataCard.addView(wipe, Ui.withMargins(this, 8, 0));
        body.addView(dataCard, Ui.matchWrap());
        body.addView(Ui.space(this, 24));
        return Ui.scrollPage(this, body);
    }

    private void planGoal() {
        String goal = commandInput == null ? "" : commandInput.getText().toString().trim();
        if (goal.isBlank()) {
            toast("먼저 맡길 일을 적어주세요.");
            return;
        }
        hideKeyboard();
        try {
            AgentCore.ActionPlan plan = runtime.plan(goal);
            showPlanDialog(plan);
        } catch (Exception error) {
            alert("계획을 만들지 못했습니다", error.getMessage());
        }
    }

    private void showPlanDialog(AgentCore.ActionPlan plan) {
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(Ui.dp(this, 4), Ui.dp(this, 4), Ui.dp(this, 4), Ui.dp(this, 4));
        content.addView(Ui.text(this, plan.primarySkill.name, 20f, true));
        content.addView(Ui.text(this, plan.primarySkill.description, 13.5f, false), Ui.withMargins(this, 5, 10));
        LinearLayout chips = Ui.horizontal(this);
        chips.addView(Ui.chip(this, policyLabel(plan.policy), policyColor(plan.policy)));
        TextView executor = Ui.chip(this, executorLabel(plan.primaryExecutor), Ui.SAGE_SOFT);
        LinearLayout.LayoutParams executorParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        executorParams.leftMargin = Ui.dp(this, 7);
        chips.addView(executor, executorParams);
        content.addView(chips, Ui.matchWrap());

        content.addView(Ui.section(this, "실행 단계"));
        int number = 1;
        for (AgentCore.PlanStep step : plan.steps) {
            TextView row = Ui.text(this, number + ". " + step.title + "\n   "
                    + executorLabel(step.executor) + " · 검증: " + step.verification,
                    13.5f, false);
            row.setPadding(0, Ui.dp(this, 3), 0, Ui.dp(this, 7));
            content.addView(row, Ui.matchWrap());
            number++;
        }
        content.addView(Ui.section(this, "왜 이 계획인가요?"));
        for (String reason : plan.reasons) {
            content.addView(Ui.text(this, "• " + reason, 13f, false), Ui.withMargins(this, 1, 3));
        }
        if (plan.connectorRequired) {
            TextView warning = Ui.text(this,
                    "외부 연결이 없는 단계는 완료로 꾸미지 않고 ‘연결 필요’ 또는 ‘사용자 인증 필요’ 상태로 남습니다.",
                    12.5f, true);
            warning.setPadding(Ui.dp(this, 11), Ui.dp(this, 9), Ui.dp(this, 11), Ui.dp(this, 9));
            warning.setBackground(Ui.rounded(Ui.AMBER_SOFT, 12, Ui.DIVIDER, 1, this));
            content.addView(warning, Ui.withMargins(this, 10, 0));
        }

        ScrollView scroll = new ScrollView(this);
        scroll.addView(content);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("처리 계획")
                .setView(scroll)
                .setNegativeButton("수정", null)
                .setPositiveButton("작업으로 시작", null)
                .create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(v -> {
                    String taskId = runtime.acceptPlan(plan);
                    dialog.dismiss();
                    toast("작업함에 저장했습니다.");
                    executePlannedTask(taskId);
                }));
        dialog.show();
    }

    private void executePlannedTask(String taskId) {
        AgentRepository.StoredTask task = findTask(taskId);
        if (task == null) {
            showPage(Page.TASKS);
            return;
        }
        if (task.status == AgentCore.TaskStatus.WAITING_USER) {
            showTaskDialog(task);
            return;
        }
        continueTask(task);
    }

    private void continueTask(AgentRepository.StoredTask task) {
        long now = AgentCore.now();
        switch (task.skillId) {
            case "nearby.local":
                repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_EXTERNAL,
                        "지도에서 장소를 선택하고 방문 여부를 확인하세요", "", "", now);
                openGeoQuery(nearbyQuery(task.goal));
                break;
            case "stream.autoplay":
                repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_EXTERNAL,
                        "자동화 탭에서 대상 스트리머 규칙을 확인하세요", "", "", now);
                showPage(Page.AUTOMATIONS);
                break;
            case "software.update.monitor":
                repository.updateTaskState(task.id, AgentCore.TaskStatus.VERIFYING,
                        "공식 릴리스와 설치 버전을 비교하세요", "", "", now);
                openWeb("https://github.com/rustdesk/rustdesk/releases/latest");
                break;
            case "reservation.orchestrator":
                handleReservation(task);
                break;
            case "insurance.monimo.claim":
                repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_USER,
                        "병원 서류 확인 후 모니모 본인인증을 진행하세요", "", "MANUAL_AUTH", now);
                alert("보험 청구 준비",
                        "서류 판독과 작업 연결은 준비됐습니다. 실제 모니모 제출은 설치된 앱 화면과 본인인증을 확인한 뒤 진행해야 하며, 접수번호가 있어야 완료됩니다.");
                showPage(Page.TASKS);
                break;
            case "transfer.safe":
                requestDeviceCredential(task);
                break;
            case "signup.autofill":
                repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_USER,
                        "자동입력 서비스를 켜고 대상 서비스에서 가입을 계속하세요", "", "", now);
                openAutofillSettings();
                break;
            case "benefits.autopilot":
                repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_EXTERNAL,
                        "공식 혜택 서비스에서 자격 후보를 확인하고 신청서를 준비하세요", "", "PROVIDER_REQUIRED", now);
                openWeb("https://www.gov.kr");
                break;
            case "vault.manage":
            case "connections.manage":
                showPage(Page.ME);
                break;
            case "automation.recipe":
                showRecipeBuilder();
                break;
            default:
                repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_EXTERNAL,
                        "공식 AI 구독 실행기 또는 PC Companion 연결이 필요합니다", "", "CONNECTOR_REQUIRED", now);
                showPage(Page.TASKS);
                break;
        }
    }

    private void handleReservation(AgentRepository.StoredTask task) {
        Matcher matcher = Pattern.compile("(?<!\\d)(0\\d{1,2})[- ]?(\\d{3,4})[- ]?(\\d{4})(?!\\d)")
                .matcher(task.goal);
        if (matcher.find()) {
            String phone = matcher.group(1) + matcher.group(2) + matcher.group(3);
            repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_USER,
                    "전화 앱에서 예약 내용을 확인하세요", "", "", AgentCore.now());
            try {
                startActivity(new Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + phone)));
            } catch (ActivityNotFoundException error) {
                alert("전화 앱을 열 수 없습니다", "이 기기에 전화 앱이 없습니다.");
            }
        } else {
            repository.updateTaskState(task.id, AgentCore.TaskStatus.WAITING_EXTERNAL,
                    "예약 대상의 공식 웹·앱·전화번호를 연결하세요", "", "CONNECTOR_REQUIRED", AgentCore.now());
            alert("예약 실행 경로가 필요합니다",
                    "목표는 작업 그래프로 저장했습니다. 전화번호나 공식 예약 주소가 없어서 임의로 추측하지 않았습니다.");
            showPage(Page.TASKS);
        }
    }

    private void requestDeviceCredential(AgentRepository.StoredTask task) {
        KeyguardManager manager = getSystemService(KeyguardManager.class);
        if (manager == null || !manager.isDeviceSecure()) {
            repository.updateTaskState(task.id, AgentCore.TaskStatus.BLOCKED,
                    "기기 화면 잠금 또는 생체인증을 먼저 설정하세요", "", "DEVICE_NOT_SECURE", AgentCore.now());
            alert("송금 초안을 진행하지 않았습니다",
                    "송금 작업은 안전한 화면 잠금이 설정된 기기에서만 다음 단계로 이동합니다.");
            return;
        }
        Intent intent = manager.createConfirmDeviceCredentialIntent(
                "송금 초안 확인", "수취인과 금액을 확인하기 위해 기기 인증이 필요합니다.");
        if (intent == null) {
            alert("기기 인증을 열 수 없습니다", "시스템 인증 화면을 시작하지 못했습니다.");
            return;
        }
        pendingCredentialTaskId = task.id;
        startActivityForResult(intent, REQUEST_DEVICE_CREDENTIAL);
    }

    private LinearLayout opportunityCard(AgentCore.Opportunity opportunity) {
        LinearLayout card = Ui.card(this);
        LinearLayout top = Ui.horizontal(this);
        TextView kind = Ui.chip(this, opportunityKindLabel(opportunity.kind),
                opportunity.kind == AgentCore.OpportunityKind.URGENT ? Ui.RED_SOFT
                        : opportunity.kind == AgentCore.OpportunityKind.BENEFIT ? Ui.AMBER_SOFT
                        : opportunity.kind == AgentCore.OpportunityKind.COMMERCIAL ? Ui.TERRA_SOFT
                        : Ui.SAGE_SOFT);
        top.addView(kind);
        top.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
        if (opportunity.commercial) top.addView(Ui.chip(this, "광고", Ui.TERRA_SOFT));
        card.addView(top, Ui.matchWrap());
        card.addView(Ui.text(this, opportunity.title, 17f, true), Ui.withMargins(this, 10, 0));
        card.addView(Ui.text(this, opportunity.summary, 13.5f, false), Ui.withMargins(this, 5, 0));
        LinearLayout actions = Ui.horizontal(this);
        Button why = Ui.ghostButton(this, "왜 추천?");
        why.setOnClickListener(v -> showReasons(opportunity));
        actions.addView(why, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        Button later = Ui.ghostButton(this, "나중에");
        later.setOnClickListener(v -> {
            repository.setPlainString("snooze_" + opportunity.id,
                    Long.toString(AgentCore.now() + 6L * 60 * 60 * 1000));
            toast("6시간 뒤 다시 볼 수 있습니다.");
            showPage(Page.HOME);
        });
        LinearLayout.LayoutParams laterParams = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        laterParams.leftMargin = Ui.dp(this, 6);
        actions.addView(later, laterParams);
        Button act = Ui.primaryButton(this, "지금 실행");
        act.setOnClickListener(v -> {
            AgentCore.ActionPlan plan = runtime.planOpportunity(opportunity);
            showPlanDialog(plan);
        });
        LinearLayout.LayoutParams actParams = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1.2f);
        actParams.leftMargin = Ui.dp(this, 6);
        actions.addView(act, actParams);
        card.addView(actions, Ui.withMargins(this, 12, 0));
        return card;
    }

    private LinearLayout taskCard(AgentRepository.StoredTask task, boolean includeButton) {
        LinearLayout card = Ui.card(this);
        LinearLayout top = Ui.horizontal(this);
        top.addView(Ui.chip(this, statusLabel(task.status), statusColor(task.status)));
        top.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
        TextView time = Ui.text(this, shortTime(task.updatedAt), 11.5f, false);
        time.setTextColor(Ui.MUTED);
        top.addView(time);
        card.addView(top, Ui.matchWrap());
        card.addView(Ui.text(this, task.goal, 16.5f, true), Ui.withMargins(this, 9, 0));
        card.addView(Ui.text(this, task.skillName, 12.5f, false), Ui.withMargins(this, 4, 0));
        TextView next = Ui.text(this, "다음: " + task.nextAction, 13.5f, true);
        next.setPadding(Ui.dp(this, 11), Ui.dp(this, 8), Ui.dp(this, 11), Ui.dp(this, 8));
        next.setBackground(Ui.rounded(Ui.SAGE_SOFT, 11, Color.TRANSPARENT, 0, this));
        card.addView(next, Ui.withMargins(this, 10, 0));
        if (includeButton) {
            Button open = Ui.ghostButton(this, "단계와 증거 보기");
            open.setOnClickListener(v -> showTaskDialog(task));
            card.addView(open, Ui.withMargins(this, 9, 0));
        }
        return card;
    }

    private void showTaskDialog(AgentRepository.StoredTask task) {
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.addView(Ui.text(this, task.goal, 18f, true));
        content.addView(Ui.text(this, task.skillName + " · " + statusLabel(task.status), 13f, false),
                Ui.withMargins(this, 4, 12));
        int index = 1;
        for (AgentRepository.StoredNode node : task.nodes) {
            String marker = node.status == AgentCore.TaskStatus.COMPLETED ? "✓" : index - 1 == task.activeNodeIndex ? "▶" : "○";
            String details = marker + " " + index + ". " + node.title
                    + "\n   " + executorLabel(node.executor) + " · " + policyLabel(node.policy)
                    + "\n   검증: " + node.verification;
            if (!node.evidence.isBlank()) details += "\n   증거: " + node.evidence;
            TextView row = Ui.text(this, details, 13f, node.status == AgentCore.TaskStatus.RUNNING);
            row.setPadding(0, Ui.dp(this, 4), 0, Ui.dp(this, 8));
            content.addView(row, Ui.matchWrap());
            index++;
        }
        TextView evidence = Ui.text(this, "완료 인정 기준: " + task.completionEvidence, 12.5f, true);
        evidence.setPadding(Ui.dp(this, 10), Ui.dp(this, 8), Ui.dp(this, 10), Ui.dp(this, 8));
        evidence.setBackground(Ui.rounded(Ui.AMBER_SOFT, 10, Color.TRANSPARENT, 0, this));
        content.addView(evidence, Ui.withMargins(this, 8, 0));
        ScrollView scroll = new ScrollView(this);
        scroll.addView(content);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("작업 상세")
                .setView(scroll)
                .setNegativeButton("닫기", null)
                .setNeutralButton("문제 기록", null)
                .setPositiveButton(task.status == AgentCore.TaskStatus.COMPLETED ? "확인" : "계속", null)
                .create();
        dialog.setOnShowListener(ignored -> {
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> {
                repository.updateTaskState(task.id, AgentCore.TaskStatus.FAILED,
                        "실패 원인을 확인하고 다른 실행기로 재계획하세요", "", "USER_REPORTED", AgentCore.now());
                runtime.recordSkillFailure(task.skillId);
                dialog.dismiss();
                showPage(Page.TASKS);
            });
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                dialog.dismiss();
                if (task.status != AgentCore.TaskStatus.COMPLETED) continueTask(task);
            });
        });
        dialog.show();
    }

    private LinearLayout recipeCard(AgentCore.Recipe recipe) {
        LinearLayout card = Ui.card(this);
        LinearLayout top = Ui.horizontal(this);
        top.addView(Ui.chip(this, recipe.enabled ? "켜짐" : "꺼짐",
                recipe.enabled ? Ui.SAGE_SOFT : Ui.RED_SOFT));
        top.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
        top.addView(Ui.chip(this, policyLabel(recipe.maximumAutomation), Ui.AMBER_SOFT));
        card.addView(top, Ui.matchWrap());
        card.addView(Ui.text(this, recipe.name, 16f, true), Ui.withMargins(this, 8, 0));
        card.addView(Ui.text(this,
                "Trigger: " + recipe.triggerType + "\nAction: " + recipe.skillId
                        + "\nVerification: " + recipe.verification,
                12.5f, false), Ui.withMargins(this, 5, 0));
        return card;
    }

    private LinearLayout skillCard(AgentCore.SkillManifest skill) {
        LinearLayout card = Ui.card(this);
        LinearLayout top = Ui.horizontal(this);
        top.addView(Ui.chip(this, riskLabel(skill.risk), riskColor(skill.risk)));
        top.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
        top.addView(Ui.chip(this, skill.connectorRequired ? "연결 필요" : "기기 실행", Ui.SAGE_SOFT));
        card.addView(top, Ui.matchWrap());
        card.addView(Ui.text(this, skill.name, 16f, true), Ui.withMargins(this, 8, 0));
        card.addView(Ui.text(this, skill.description, 12.8f, false), Ui.withMargins(this, 4, 0));
        TextView evidence = Ui.text(this, "완료 증거: " + skill.verificationEvidence, 11.8f, false);
        evidence.setTextColor(Ui.MUTED);
        card.addView(evidence, Ui.withMargins(this, 5, 0));
        card.setOnClickListener(v -> alert(skill.name,
                skill.description + "\n\nCapabilities\n• " + String.join("\n• ", skill.capabilities)
                        + "\n\nExecutors\n• " + joinExecutors(skill)));
        return card;
    }

    private void showRecipeBuilder() {
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(Ui.dp(this, 2), Ui.dp(this, 4), Ui.dp(this, 2), 0);
        EditText name = field("자동화 이름", "");
        content.addView(name, Ui.withMargins(this, 0, 8));
        Spinner trigger = spinner(List.of(
                "notification.insurance_followup",
                "notification.reservation_cancelled",
                "notification.stream_live",
                "notification.benefit",
                "location.changed",
                "document.shared"
        ));
        content.addView(label("Trigger"));
        content.addView(trigger, Ui.withMargins(this, 2, 8));
        EditText contains = field("조건: 알림에 포함될 말, 선택사항", "");
        content.addView(contains, Ui.withMargins(this, 0, 8));
        List<AgentCore.SkillManifest> skills = runtime.skills().all();
        List<String> skillLabels = new ArrayList<>();
        for (AgentCore.SkillManifest skill : skills) skillLabels.add(skill.name + " | " + skill.id);
        Spinner skillSpinner = spinner(skillLabels);
        content.addView(label("실행할 스킬"));
        content.addView(skillSpinner, Ui.withMargins(this, 2, 8));
        Spinner policy = spinner(List.of("AUTO", "CONFIRM", "BIOMETRIC", "MANUAL_AUTH"));
        content.addView(label("최대 자동화 범위"));
        content.addView(policy, Ui.withMargins(this, 2, 0));
        TextView note = Ui.text(this,
                "실제 정책 커널은 여기서 AUTO를 골라도 송금·인증·외부 제출의 확인 관문을 낮추지 않습니다.",
                12f, false);
        note.setPadding(0, Ui.dp(this, 8), 0, 0);
        content.addView(note, Ui.matchWrap());

        new AlertDialog.Builder(this)
                .setTitle("Trigger → Action")
                .setView(content)
                .setNegativeButton("취소", null)
                .setPositiveButton("저장", (dialog, which) -> {
                    String recipeName = name.getText().toString().trim();
                    if (recipeName.isBlank()) recipeName = "새 자동화";
                    AgentCore.SkillManifest selected = skills.get(skillSpinner.getSelectedItemPosition());
                    Map<String, String> conditions = contains.getText().toString().trim().isEmpty()
                            ? Map.of() : Map.of("summary_contains", contains.getText().toString().trim());
                    AgentCore.PolicyDecision selectedPolicy = AgentCore.PolicyDecision.valueOf(
                            policy.getSelectedItem().toString());
                    if (selected.risk == AgentCore.Risk.CRITICAL && selectedPolicy == AgentCore.PolicyDecision.AUTO) {
                        selectedPolicy = AgentCore.PolicyDecision.BIOMETRIC;
                    } else if (selected.risk == AgentCore.Risk.HIGH && selectedPolicy == AgentCore.PolicyDecision.AUTO) {
                        selectedPolicy = AgentCore.PolicyDecision.CONFIRM;
                    }
                    repository.saveRecipe(new AgentCore.Recipe(UUID.randomUUID().toString(), recipeName,
                            trigger.getSelectedItem().toString(), conditions, selected.id,
                            selectedPolicy, selected.verificationEvidence, true));
                    toast("자동화를 저장했습니다.");
                    showPage(Page.AUTOMATIONS);
                })
                .show();
    }

    private void showReasons(AgentCore.Opportunity opportunity) {
        StringBuilder text = new StringBuilder();
        for (String reason : opportunity.reasons) text.append("• ").append(reason).append('\n');
        if (opportunity.commercial) {
            text.append("\n상업 추천은 건강·보험·금융·가족·메시지 원문·정확한 위치를 사용하지 않습니다.");
        } else {
            text.append("\n이 추천은 광고가 아닙니다.");
        }
        new AlertDialog.Builder(this)
                .setTitle("왜 이 추천이 보이나요?")
                .setMessage(text.toString().trim())
                .setNegativeButton("이런 추천 끄기", (dialog, which) -> {
                    repository.setPlainSetting("disabled_opportunity_" + opportunity.skillId, true);
                    toast("같은 종류의 추천을 숨겼습니다.");
                })
                .setPositiveButton("확인", null)
                .show();
    }

    private void showContextTransparency() {
        long now = AgentCore.now();
        List<AgentCore.ContextFact> facts = repository.loadContextGraph(now).snapshot(now);
        if (facts.isEmpty()) {
            alert("기억한 문맥", "현재 저장된 개인 문맥이 없습니다.");
            return;
        }
        StringBuilder text = new StringBuilder();
        for (AgentCore.ContextFact fact : facts) {
            text.append("• ").append(fact.key).append("\n  ")
                    .append(maskValue(fact.key, fact.value)).append("\n  민감도 ")
                    .append(fact.sensitivity.name()).append(" · 자동화 ")
                    .append(fact.mayDriveAutomation ? "허용" : "제한").append("\n\n");
        }
        ScrollView scroll = new ScrollView(this);
        TextView view = Ui.text(this, text.toString().trim(), 13f, false);
        view.setTextIsSelectable(true);
        scroll.addView(view);
        new AlertDialog.Builder(this)
                .setTitle("기억한 문맥과 범위")
                .setView(scroll)
                .setPositiveButton("확인", null)
                .show();
    }

    private void confirmWipe() {
        new AlertDialog.Builder(this)
                .setTitle("기기 데이터를 모두 삭제할까요?")
                .setMessage("개인정보 금고, 문맥 그래프, 작업, 자동화, 연결 설정이 삭제됩니다. 되돌릴 수 없습니다.")
                .setNegativeButton("취소", null)
                .setPositiveButton("전체 삭제", (dialog, which) -> {
                    LocationContextService.stop(this);
                    repository.wipeAll();
                    toast("Life Agent의 기기 데이터를 삭제했습니다.");
                    showPage(Page.HOME);
                })
                .show();
    }

    private void enableLocationContext() {
        if (checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.ACCESS_COARSE_LOCATION,
                    Manifest.permission.ACCESS_FINE_LOCATION}, REQUEST_LOCATION);
            return;
        }
        requestNotificationPermissionIfNeeded();
        setConsent("consent.location", true);
        LocationContextService.start(this);
        toast("대략적 위치 기반 기회 감지를 켰습니다.");
    }

    private void requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQUEST_NOTIFICATIONS);
        }
    }

    private void startVoiceInput() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.KOREA.toLanguageTag());
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "맡길 일을 말하세요");
        try {
            startActivityForResult(intent, REQUEST_VOICE);
        } catch (ActivityNotFoundException error) {
            toast("이 기기에 음성 입력 서비스가 없습니다.");
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_VOICE && resultCode == RESULT_OK && data != null) {
            ArrayList<String> results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
            if (results != null && !results.isEmpty() && commandInput != null) {
                commandInput.setText(AgentCore.sanitizeIncoming(results.get(0)));
                commandInput.setSelection(commandInput.length());
            }
        } else if (requestCode == REQUEST_DEVICE_CREDENTIAL && !pendingCredentialTaskId.isBlank()) {
            if (resultCode == RESULT_OK) {
                repository.updateTaskState(pendingCredentialTaskId, AgentCore.TaskStatus.WAITING_EXTERNAL,
                        "은행 앱에서 수취인·금액을 다시 확인하고 거래 결과를 가져오세요",
                        "기기 인증 통과", "BANK_PROVIDER_REQUIRED", AgentCore.now());
                toast("기기 인증을 확인했습니다. 실제 송금은 은행 인증 뒤에만 완료됩니다.");
            } else {
                repository.updateTaskState(pendingCredentialTaskId, AgentCore.TaskStatus.WAITING_USER,
                        "기기 인증이 필요합니다", "", "AUTH_CANCELLED", AgentCore.now());
            }
            pendingCredentialTaskId = "";
            showPage(Page.TASKS);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_LOCATION) {
            boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
            if (granted) {
                setConsent("consent.location", true);
                requestNotificationPermissionIfNeeded();
                LocationContextService.start(this);
                toast("대략적 위치 기반 기회 감지를 켰습니다.");
            } else {
                setConsent("consent.location", false);
                toast("위치 권한이 없어 위치 기반 추천을 켜지 않았습니다.");
            }
        }
    }

    private void openNotificationSettings() {
        try {
            startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));
        } catch (ActivityNotFoundException error) {
            openAppSettings();
        }
    }

    private void openAutofillSettings() {
        try {
            Intent intent = new Intent("android.settings.REQUEST_SET_AUTOFILL_SERVICE");
            intent.setData(Uri.parse("package:" + getPackageName()));
            startActivity(intent);
        } catch (ActivityNotFoundException error) {
            try {
                startActivity(new Intent(Settings.ACTION_SETTINGS));
            } catch (ActivityNotFoundException ignored) {
                toast("자동입력 설정을 열 수 없습니다.");
            }
        }
    }

    private void openAppSettings() {
        startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + getPackageName())));
    }

    private boolean notificationAccessEnabled() {
        String enabled = Settings.Secure.getString(getContentResolver(), "enabled_notification_listeners");
        if (enabled == null) return false;
        ComponentName expected = new ComponentName(this, UnifiedNotificationListener.class);
        for (String component : enabled.split(":")) {
            ComponentName found = ComponentName.unflattenFromString(component);
            if (expected.equals(found)) return true;
        }
        return false;
    }

    private boolean autofillEnabled() {
        AutofillManager manager = getSystemService(AutofillManager.class);
        return manager != null && manager.hasEnabledAutofillServices();
    }

    private void openGeoQuery(String query) {
        try {
            Uri uri = Uri.parse("geo:0,0?q=" + Uri.encode(query));
            Intent intent = new Intent(Intent.ACTION_VIEW, uri);
            startActivity(intent);
        } catch (ActivityNotFoundException error) {
            openWeb("https://www.google.com/maps/search/?api=1&query=" + Uri.encode(query));
        }
    }

    private void openWeb(String url) {
        try {
            Uri uri = Uri.parse(url);
            if (!"https".equalsIgnoreCase(uri.getScheme())) throw new SecurityException("HTTPS only");
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (RuntimeException error) {
            alert("공식 페이지를 열 수 없습니다", "브라우저 또는 안전한 HTTPS 연결을 확인하세요.");
        }
    }

    private String nearbyQuery(String goal) {
        String normalized = AgentCore.normalize(goal);
        if (normalized.contains("약국") || normalized.contains("영양제") || normalized.contains("비타민")) return "약국";
        if (normalized.contains("식당") || normalized.contains("밥")) return "식당";
        if (normalized.contains("주차")) return "주차장";
        if (normalized.contains("편의점")) return "편의점";
        return "주변 상점";
    }

    private LinearLayout pageBody() {
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(Ui.dp(this, 18), Ui.dp(this, 18), Ui.dp(this, 18), Ui.dp(this, 30));
        body.setBackgroundColor(Ui.CANVAS);
        return body;
    }

    private LinearLayout statusChip(String label, boolean enabled) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setGravity(Gravity.CENTER);
        card.setPadding(Ui.dp(this, 8), Ui.dp(this, 9), Ui.dp(this, 8), Ui.dp(this, 9));
        card.setBackground(Ui.rounded(enabled ? Ui.SAGE_SOFT : Ui.SURFACE, 14,
                enabled ? Ui.SAGE : Ui.DIVIDER, 1, this));
        TextView title = Ui.text(this, label, 12.5f, true);
        title.setGravity(Gravity.CENTER);
        card.addView(title);
        TextView state = Ui.text(this, enabled ? "사용 중" : "꺼짐", 11.5f, false);
        state.setTextColor(enabled ? Ui.SAGE : Ui.MUTED);
        state.setGravity(Gravity.CENTER);
        card.addView(state);
        return card;
    }

    private LinearLayout.LayoutParams spacedWeight() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0,
                ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        params.leftMargin = Ui.dp(this, 7);
        return params;
    }

    private LinearLayout emptyCard(String title, String subtitle) {
        LinearLayout card = Ui.card(this);
        card.addView(Ui.text(this, title, 16f, true));
        card.addView(Ui.text(this, subtitle, 13f, false), Ui.withMargins(this, 5, 0));
        return card;
    }

    private LinearLayout connectionRow(String title, boolean connected, Runnable action) {
        LinearLayout row = Ui.horizontal(this);
        row.setPadding(0, Ui.dp(this, 7), 0, Ui.dp(this, 7));
        LinearLayout text = new LinearLayout(this);
        text.setOrientation(LinearLayout.VERTICAL);
        text.addView(Ui.text(this, title, 15f, true));
        TextView state = Ui.text(this, connected ? "연결됨" : "설정 필요", 12f, false);
        state.setTextColor(connected ? Ui.SAGE : Ui.TERRA);
        text.addView(state);
        row.addView(text, Ui.weighted());
        Button button = Ui.ghostButton(this, connected ? "관리" : "설정");
        button.setOnClickListener(v -> action.run());
        row.addView(button, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return row;
    }

    private CheckBox consentToggle(String label, boolean checked) {
        CheckBox box = new CheckBox(this);
        box.setText(label);
        box.setTextSize(15.5f);
        box.setTextColor(Ui.INK);
        box.setMinHeight(Ui.dp(this, 48));
        box.setChecked(checked);
        return box;
    }

    private EditText field(String hint, String value) {
        EditText field = new EditText(this);
        field.setHint(hint);
        field.setText(value == null ? "" : value);
        field.setTextSize(14.5f);
        field.setTextColor(Ui.INK);
        field.setHintTextColor(Ui.MUTED);
        field.setMinHeight(Ui.dp(this, 50));
        field.setPadding(Ui.dp(this, 12), Ui.dp(this, 7), Ui.dp(this, 12), Ui.dp(this, 7));
        field.setBackground(Ui.rounded(Color.WHITE, 12, Ui.DIVIDER, 1, this));
        return field;
    }

    private TextView label(String value) {
        TextView label = Ui.text(this, value, 12.5f, true);
        label.setPadding(0, Ui.dp(this, 7), 0, 0);
        return label;
    }

    private Spinner spinner(List<String> values) {
        Spinner spinner = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_dropdown_item, values);
        spinner.setAdapter(adapter);
        spinner.setMinimumHeight(Ui.dp(this, 48));
        return spinner;
    }

    private List<AgentRepository.StoredTask> filterTasks(List<AgentRepository.StoredTask> tasks, boolean needsUser) {
        List<AgentRepository.StoredTask> out = new ArrayList<>();
        for (AgentRepository.StoredTask task : tasks) {
            boolean user = task.status == AgentCore.TaskStatus.WAITING_USER
                    || task.status == AgentCore.TaskStatus.BLOCKED
                    || task.status == AgentCore.TaskStatus.FAILED;
            boolean active = task.status != AgentCore.TaskStatus.COMPLETED && !user;
            if ((needsUser && user) || (!needsUser && active)) out.add(task);
        }
        return out;
    }

    private AgentRepository.StoredTask findTask(String id) {
        for (AgentRepository.StoredTask task : repository.listTasks()) {
            if (task.id.equals(id)) return task;
        }
        return null;
    }

    private String graphValue(String key) {
        return repository.loadContextGraph(AgentCore.now()).value(key, AgentCore.now());
    }

    private boolean factBoolean(String key) {
        return "true".equalsIgnoreCase(graphValue(key));
    }

    private void setConsent(String key, boolean value) {
        repository.putFact(new AgentCore.ContextFact(key, Boolean.toString(value),
                AgentCore.Sensitivity.PERSONAL, 0L, value, false));
    }

    private void putFact(String key, String value, AgentCore.Sensitivity sensitivity, boolean commercial) {
        String cleaned = value == null ? "" : value.trim();
        if (cleaned.isEmpty()) {
            repository.removeFact(key);
            return;
        }
        repository.putFact(new AgentCore.ContextFact(key, cleaned, sensitivity, 0L, true, commercial));
    }

    private String joinExecutors(AgentCore.SkillManifest skill) {
        List<String> values = new ArrayList<>();
        for (AgentCore.ExecutorType executor : skill.executors) values.add(executorLabel(executor));
        return String.join("\n• ", values);
    }

    private String maskValue(String key, String value) {
        if (value == null || value.isBlank()) return "(비어 있음)";
        if (key.contains("phone") && value.length() >= 4) return "***-****-" + value.substring(value.length() - 4);
        if (key.contains("email") && value.contains("@")) {
            int at = value.indexOf('@');
            return value.substring(0, Math.min(2, at)) + "***" + value.substring(at);
        }
        if (key.contains("address")) return value.length() <= 6 ? "***" : value.substring(0, 6) + "…";
        if (key.contains("name")) return value.substring(0, 1) + "**";
        if (key.contains("location")) return "대략적 위치 저장됨";
        return value.length() > 70 ? value.substring(0, 70) + "…" : value;
    }

    private String taskGroup(AgentCore.TaskStatus status) {
        switch (status) {
            case WAITING_USER:
            case BLOCKED:
            case FAILED:
                return "내 확인이 필요함";
            case COMPLETED:
                return "완료";
            default:
                return "진행 중";
        }
    }

    private String statusLabel(AgentCore.TaskStatus status) {
        switch (status) {
            case PLANNED: return "계획됨";
            case READY: return "준비됨";
            case RUNNING: return "실행 중";
            case WAITING_USER: return "내 확인 필요";
            case WAITING_EXTERNAL: return "외부 결과 대기";
            case VERIFYING: return "증거 확인 중";
            case COMPLETED: return "완료";
            case BLOCKED: return "차단됨";
            case FAILED: return "문제 발생";
            default: return status.name();
        }
    }

    private int statusColor(AgentCore.TaskStatus status) {
        switch (status) {
            case COMPLETED: return Ui.SAGE_SOFT;
            case WAITING_USER:
            case VERIFYING: return Ui.AMBER_SOFT;
            case BLOCKED:
            case FAILED: return Ui.RED_SOFT;
            default: return Ui.TERRA_SOFT;
        }
    }

    private String policyLabel(AgentCore.PolicyDecision policy) {
        switch (policy) {
            case AUTO: return "자동 실행";
            case CONFIRM: return "확인 후 실행";
            case BIOMETRIC: return "기기 인증";
            case MANUAL_AUTH: return "직접 인증";
            case BLOCK: return "실행 차단";
            default: return policy.name();
        }
    }

    private int policyColor(AgentCore.PolicyDecision policy) {
        switch (policy) {
            case AUTO: return Ui.SAGE_SOFT;
            case CONFIRM:
            case BIOMETRIC:
            case MANUAL_AUTH: return Ui.AMBER_SOFT;
            case BLOCK: return Ui.RED_SOFT;
            default: return Ui.TERRA_SOFT;
        }
    }

    private String executorLabel(AgentCore.ExecutorType executor) {
        switch (executor) {
            case MODEL_FREE: return "모델 없이";
            case ANDROID_INTENT: return "Android 공식 실행";
            case LOCAL_OCR: return "기기 OCR";
            case AUTOFILL: return "보안 자동입력";
            case NOTIFICATION_ACTION: return "원본 알림 실행";
            case LOCATION_CONTEXT: return "위치 문맥";
            case OFFICIAL_WEB: return "공식 웹";
            case PHONE: return "전화";
            case SUBSCRIPTION_AI: return "AI 구독 실행기";
            case MOBILE_CU: return "모바일 Computer Use";
            case DESKTOP_COMPANION: return "PC·Mac Companion";
            case HUMAN: return "사용자 직접 확인";
            default: return executor.name();
        }
    }

    private String opportunityKindLabel(AgentCore.OpportunityKind kind) {
        switch (kind) {
            case URGENT: return "긴급 대응";
            case BENEFIT: return "받을 수 있는 혜택";
            case NEARBY: return "근처에서 해결";
            case CONVENIENCE: return "생활 편의";
            case UPDATE: return "업데이트";
            case COMMERCIAL: return "상업 추천";
            default: return kind.name();
        }
    }

    private String riskLabel(AgentCore.Risk risk) {
        switch (risk) {
            case LOW: return "저위험";
            case MEDIUM: return "중간 위험";
            case HIGH: return "높은 위험";
            case CRITICAL: return "핵심 승인";
            default: return risk.name();
        }
    }

    private int riskColor(AgentCore.Risk risk) {
        switch (risk) {
            case LOW: return Ui.SAGE_SOFT;
            case MEDIUM: return Ui.TERRA_SOFT;
            case HIGH: return Ui.AMBER_SOFT;
            case CRITICAL: return Ui.RED_SOFT;
            default: return Ui.SURFACE;
        }
    }

    private String shortTime(long time) {
        if (time <= 0L) return "";
        return DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date(time));
    }

    private void hideKeyboard() {
        View focus = getCurrentFocus();
        if (focus == null) return;
        InputMethodManager manager = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
        if (manager != null) manager.hideSoftInputFromWindow(focus.getWindowToken(), 0);
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    private void alert(String title, String message) {
        new AlertDialog.Builder(this)
                .setTitle(title)
                .setMessage(message == null || message.isBlank() ? "알 수 없는 오류입니다." : message)
                .setPositiveButton("확인", null)
                .show();
    }
}
