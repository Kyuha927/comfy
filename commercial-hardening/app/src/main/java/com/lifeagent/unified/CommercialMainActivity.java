package com.lifeagent.unified;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.NotificationManager;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.location.Location;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.speech.RecognizerIntent;
import android.text.InputType;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.TimeUnit;

/**
 * Goal-first shell for the commercialization hardening build.
 * Features remain skills underneath one task, policy and evidence surface.
 */
public final class CommercialMainActivity extends Activity {
    public static final String EXTRA_OPEN_OPPORTUNITY = "lifeagent.commercial.open_opportunity";
    private static final int REQUEST_NOTIFICATIONS = 320;
    private static final int REQUEST_LOCATION = 321;
    private static final int REQUEST_VOICE = 322;
    private static final int REQUEST_DEVICE_CREDENTIAL = 323;

    private static final int BG = Color.rgb(247, 244, 238);
    private static final int CARD = Color.rgb(255, 253, 249);
    private static final int INK = Color.rgb(36, 38, 34);
    private static final int MUTED = Color.rgb(104, 105, 98);
    private static final int SAGE = Color.rgb(83, 110, 93);
    private static final int SAGE_SOFT = Color.rgb(226, 234, 226);
    private static final int TERRACOTTA = Color.rgb(169, 93, 69);
    private static final int TERRACOTTA_SOFT = Color.rgb(244, 226, 218);
    private static final int AMBER_SOFT = Color.rgb(249, 238, 205);
    private static final int BORDER = Color.rgb(224, 219, 209);
    private static final int DANGER = Color.rgb(151, 54, 46);

    private enum Tab { HOME, TASKS, AUTOMATIONS, PROFILE }

    private LinearLayout page;
    private LinearLayout nav;
    private EditText commandInput;
    private Tab currentTab = Tab.HOME;
    private CommercialCore.AppState state;
    private CommercialCore.Plan pendingCredentialPlan;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window window = getWindow();
        window.setStatusBarColor(BG);
        window.setNavigationBarColor(CARD);
        if (Build.VERSION.SDK_INT >= 23) {
            window.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        }
        loadStateOrShowRecovery();
        buildShell();
        ingestEntryIntent(getIntent());
        String opportunityId = getIntent().getStringExtra(EXTRA_OPEN_OPPORTUNITY);
        if (!TextUtils.isEmpty(opportunityId)) {
            currentTab = Tab.HOME;
            render();
            showOpportunity(opportunityId);
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        ingestEntryIntent(intent);
        String opportunityId = intent.getStringExtra(EXTRA_OPEN_OPPORTUNITY);
        if (!TextUtils.isEmpty(opportunityId)) showOpportunity(opportunityId);
    }

    @Override
    protected void onResume() {
        super.onResume();
        reloadState();
        render();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_VOICE && resultCode == RESULT_OK && data != null) {
            ArrayList<String> results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
            if (results != null && !results.isEmpty() && commandInput != null) {
                commandInput.setText(results.get(0));
                commandInput.setSelection(commandInput.length());
            }
        } else if (requestCode == REQUEST_DEVICE_CREDENTIAL) {
            if (resultCode == RESULT_OK && pendingCredentialPlan != null) {
                createTaskFromPlan(pendingCredentialPlan, true);
            } else {
                toast("기기 인증이 취소되었습니다.");
            }
            pendingCredentialPlan = null;
        }
    }

    @Override
    public void onRequestPermissionsResult(
            int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_LOCATION) {
            boolean granted = grantResults.length > 0
                    && grantResults[0] == PackageManager.PERMISSION_GRANTED;
            if (granted) startLocationSession();
            else toast("위치 권한이 없어 주변 기회를 시작하지 않았습니다.");
        }
        render();
    }

    private void buildShell() {
        LinearLayout shell = new LinearLayout(this);
        shell.setOrientation(LinearLayout.VERTICAL);
        shell.setBackgroundColor(BG);

        page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setClipToPadding(false);
        scroll.addView(page, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        shell.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setGravity(Gravity.CENTER);
        nav.setPadding(dp(8), dp(6), dp(8), dp(8));
        nav.setBackgroundColor(CARD);
        shell.addView(nav, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(68)));
        setContentView(shell);
        render();
    }

    private void render() {
        if (page == null || nav == null) return;
        page.removeAllViews();
        page.setPadding(dp(18), dp(18), dp(18), dp(32));
        nav.removeAllViews();
        renderTopBar();
        switch (currentTab) {
            case TASKS:
                renderTasks();
                break;
            case AUTOMATIONS:
                renderAutomations();
                break;
            case PROFILE:
                renderProfile();
                break;
            default:
                renderHome();
                break;
        }
        renderBottomNavigation();
    }

    private void renderTopBar() {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        TextView brand = text("LIFE AGENT", 12, true, SAGE);
        brand.setLetterSpacing(0.12f);
        row.addView(brand, new LinearLayout.LayoutParams(0, dp(34), 1f));
        CommercialCore.HealthSnapshot health = CommercialCore.health(this);
        TextView status = pill(
                health.corePass() ? "코어 정상" : "점검 필요",
                health.corePass() ? SAGE_SOFT : TERRACOTTA_SOFT,
                health.corePass() ? SAGE : DANGER);
        status.setOnClickListener(v -> showHealth());
        row.addView(status);
        page.addView(row, matchWrap());
    }

    private void renderHome() {
        TextView heading = text("원하는 결과만 말하세요", 29, true, INK);
        heading.setPadding(0, dp(8), 0, dp(4));
        page.addView(heading, matchWrap());
        TextView sub = text(
                "Life Agent가 문맥과 권한을 확인하고 가장 안전한 실행 경로를 먼저 보여드립니다.",
                15, false, MUTED);
        page.addView(sub, matchWrap());

        LinearLayout composer = card();
        composer.setPadding(dp(16), dp(14), dp(16), dp(14));
        commandInput = new EditText(this);
        commandInput.setHint("예: 금요일 오후 정형외과 예약해줘");
        commandInput.setTextColor(INK);
        commandInput.setHintTextColor(Color.rgb(141, 139, 131));
        commandInput.setTextSize(17);
        commandInput.setMinLines(2);
        commandInput.setMaxLines(5);
        commandInput.setGravity(Gravity.TOP | Gravity.START);
        commandInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE
                | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        commandInput.setBackgroundColor(Color.TRANSPARENT);
        composer.addView(commandInput, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout composerActions = new LinearLayout(this);
        composerActions.setOrientation(LinearLayout.HORIZONTAL);
        composerActions.setGravity(Gravity.CENTER_VERTICAL);
        Button voice = secondaryButton("음성");
        voice.setOnClickListener(v -> startVoice());
        composerActions.addView(voice, new LinearLayout.LayoutParams(dp(78), dp(48)));
        Space spacer = new Space(this);
        composerActions.addView(spacer, new LinearLayout.LayoutParams(0, 1, 1f));
        Button plan = primaryButton("처리 계획 보기");
        plan.setOnClickListener(v -> previewCommand());
        composerActions.addView(plan, new LinearLayout.LayoutParams(dp(154), dp(48)));
        composer.addView(composerActions, matchWrapWithTop(dp(8)));
        page.addView(composer, matchWrapWithTop(dp(18)));

        CommercialCore.HealthSnapshot health = CommercialCore.health(this);
        if (!health.corePass() || health.providerConnectionsNeeded > 0) {
            LinearLayout readiness = tintedCard(AMBER_SOFT);
            readiness.addView(text("상용화 준비 상태", 15, true, INK));
            readiness.addView(text(
                    health.corePass()
                            ? "앱 코어는 정상입니다. 실송금·실전화·모니모 제출·AI 실행기는 정식 제공자 연결이 필요합니다."
                            : "암호화 저장소·화면 잠금·알림 권한을 먼저 점검해야 합니다.",
                    14, false, MUTED), matchWrapWithTop(dp(5)));
            Button inspect = inlineButton("상태 자세히 보기");
            inspect.setOnClickListener(v -> showHealth());
            readiness.addView(inspect, matchWrapWithTop(dp(8)));
            page.addView(readiness, matchWrapWithTop(dp(14)));
        }

        List<CommercialCore.OpportunityRecord> visible = visibleOpportunities();
        sectionTitle("지금 필요한 일", visible.isEmpty() ? "새로운 기회가 없습니다" : visible.size() + "건");
        if (visible.isEmpty()) {
            LinearLayout empty = card();
            empty.addView(text("조용한 상태입니다", 17, true, INK));
            empty.addView(text(
                    "허용한 알림, 공유한 문서, 사용자가 켠 위치 세션에서만 필요한 일을 찾습니다.",
                    14, false, MUTED), matchWrapWithTop(dp(5)));
            page.addView(empty, matchWrap());
        } else {
            int count = Math.min(5, visible.size());
            for (int i = 0; i < count; i++) addOpportunityCard(visible.get(i));
        }

        sectionTitle("빠르게 맡기기", "스킬은 메뉴가 아니라 실행 능력입니다");
        addPromptChip("병원 서류 보험 청구해줘");
        addPromptChip("받을 수 있는 지원 혜택 확인해줘");
        addPromptChip("주변 약국을 찾아줘");
        addPromptChip("감스트 방송 켜지면 자동으로 열어줘");
    }

    private void renderTasks() {
        page.addView(text("작업함", 29, true, INK), matchWrapWithTop(dp(8)));
        page.addView(text(
                "앱이 중단돼도 다음 행동과 완료 증거를 이어갑니다.",
                15, false, MUTED), matchWrapWithTop(dp(4)));
        if (state.tasks.isEmpty()) {
            LinearLayout empty = card();
            empty.addView(text("아직 만든 작업이 없습니다", 17, true, INK));
            empty.addView(text("홈에서 목표를 입력하고 처리 계획을 확인하세요.", 14, false, MUTED),
                    matchWrapWithTop(dp(5)));
            page.addView(empty, matchWrapWithTop(dp(20)));
            return;
        }
        for (CommercialCore.TaskRecord task : state.tasks) addTaskCard(task);
    }

    private void renderAutomations() {
        page.addView(text("자동화와 감지", 29, true, INK), matchWrapWithTop(dp(8)));
        page.addView(text(
                "모든 감지는 기본 꺼짐입니다. 허용 앱과 시간을 직접 선택하세요.",
                15, false, MUTED), matchWrapWithTop(dp(4)));

        LinearLayout settingsCard = card();
        CheckBox analyze = checkBox("허용한 앱의 새 알림에서 필요한 일 찾기",
                state.settings.notificationAnalysis);
        settingsCard.addView(analyze);
        CheckBox nearby = checkBox("대략적 위치로 주변 기회 찾기",
                state.settings.nearbyOpportunities);
        settingsCard.addView(nearby);
        CheckBox updates = checkBox("요청했을 때 소프트웨어 업데이트 확인",
                state.settings.updateChecks);
        settingsCard.addView(updates);
        CheckBox commerce = checkBox("상업 추천 허용", state.settings.commercialRecommendations);
        settingsCard.addView(commerce);
        TextView commerceNote = text(
                "건강·보험·금융·메시지 원문·정확한 위치는 상업 추천에 사용하지 않습니다.",
                12, false, MUTED);
        commerceNote.setPadding(dp(30), 0, 0, dp(5));
        settingsCard.addView(commerceNote);

        Button saveGeneral = primaryButton("감지 설정 저장");
        saveGeneral.setOnClickListener(v -> {
            state.settings.notificationAnalysis = analyze.isChecked();
            state.settings.nearbyOpportunities = nearby.isChecked();
            state.settings.updateChecks = updates.isChecked();
            state.settings.commercialRecommendations = commerce.isChecked();
            if (!persistState()) return;
            if (nearby.isChecked()) ensureLocationSession();
            else stopLocationSession();
            render();
        });
        settingsCard.addView(saveGeneral, matchWrapWithTop(dp(10)));
        page.addView(settingsCard, matchWrapWithTop(dp(20)));

        sectionTitle("알림 허용 앱", "선택하지 않은 앱의 알림은 즉시 무시됩니다");
        LinearLayout allowCard = card();
        List<AppToggle> toggles = Arrays.asList(
                new AppToggle("카카오톡", CommercialCore.PKG_KAKAO),
                new AppToggle("Google 메시지", CommercialCore.PKG_GOOGLE_MESSAGES),
                new AppToggle("Samsung 메시지", CommercialCore.PKG_SAMSUNG_MESSAGES),
                new AppToggle("모니모", CommercialCore.PKG_MONIMO),
                new AppToggle("SOOP", CommercialCore.PKG_SOOP),
                new AppToggle("치지직", CommercialCore.PKG_CHZZK)
        );
        for (AppToggle toggle : toggles) {
            toggle.box = checkBox(toggle.label + installedSuffix(toggle.packageName),
                    state.settings.allowedPackages.contains(toggle.packageName));
            allowCard.addView(toggle.box);
        }
        Button saveApps = secondaryButton("허용 앱 저장");
        saveApps.setOnClickListener(v -> {
            state.settings.allowedPackages.clear();
            for (AppToggle toggle : toggles) if (toggle.box.isChecked()) {
                state.settings.allowedPackages.add(toggle.packageName);
            }
            if (persistState()) render();
        });
        allowCard.addView(saveApps, matchWrapWithTop(dp(8)));
        Button notificationAccess = inlineButton("Android 알림 접근 설정 열기");
        notificationAccess.setOnClickListener(v -> openSettingsAction(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));
        allowCard.addView(notificationAccess, matchWrapWithTop(dp(8)));
        page.addView(allowCard, matchWrap());

        sectionTitle("방송 무탭 자동 실행", "정확한 규칙 한 건이 일치할 때만 실행");
        LinearLayout streamCard = card();
        CheckBox streamAuto = checkBox("SOOP·치지직 방송 알림을 탭 없이 열기",
                state.settings.exactStreamAutoOpen);
        streamCard.addView(streamAuto);
        EditText rules = editText(
                "한 줄에 플랫폼|별칭|공식 채널 URL\n예: chzzk|스트리머명|https://chzzk.naver.com/채널ID",
                formatStreamRules(), 4);
        streamCard.addView(rules, matchWrapWithTop(dp(8)));
        Button saveRules = primaryButton("방송 규칙 저장");
        saveRules.setOnClickListener(v -> {
            try {
                state.settings.streamRules.clear();
                state.settings.streamRules.addAll(parseStreamRules(rules.getText().toString()));
                state.settings.exactStreamAutoOpen = streamAuto.isChecked();
                state.settings.allowedPackages.add(CommercialCore.PKG_SOOP);
                state.settings.allowedPackages.add(CommercialCore.PKG_CHZZK);
                state.settings.notificationAnalysis = true;
                if (persistState()) render();
            } catch (IllegalArgumentException error) {
                showMessage("규칙을 저장할 수 없습니다", error.getMessage());
            }
        });
        streamCard.addView(saveRules, matchWrapWithTop(dp(10)));
        page.addView(streamCard, matchWrap());
    }

    private void renderProfile() {
        page.addView(text("내 정보와 연결", 29, true, INK), matchWrapWithTop(dp(8)));
        page.addView(text(
                "민감정보는 기기 키로 암호화합니다. OTP·비밀번호·PIN·CVV는 저장하지 않습니다.",
                15, false, MUTED), matchWrapWithTop(dp(4)));

        LinearLayout profileCard = card();
        EditText name = field("이름", state.profile.displayName, InputType.TYPE_CLASS_TEXT);
        EditText email = field("이메일", state.profile.email,
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText phone = field("전화번호", state.profile.phone, InputType.TYPE_CLASS_PHONE);
        EditText address = field("주소", state.profile.address, InputType.TYPE_CLASS_TEXT);
        EditText interests = field("관심 주제", state.profile.interestTags, InputType.TYPE_CLASS_TEXT);
        EditText health = editText("건강·영양제 관련 주의와 관심", state.profile.healthNotes, 3);
        EditText benefit = editText("혜택 검토에 필요한 비민감 조건 메모", state.profile.benefitNotes, 3);
        for (View view : Arrays.asList(name, email, phone, address, interests, health, benefit)) {
            profileCard.addView(view, matchWrapWithTop(dp(8)));
        }
        Button save = primaryButton("암호화해 저장");
        save.setOnClickListener(v -> {
            String joined = name.getText() + " " + email.getText() + " " + phone.getText()
                    + " " + address.getText() + " " + interests.getText() + " "
                    + health.getText() + " " + benefit.getText();
            if (CommercialCore.looksSensitive(joined)) {
                showMessage("저장할 수 없는 정보가 있습니다",
                        "비밀번호, OTP, PIN, 카드 보안정보는 Life Agent에 저장하지 않습니다.");
                return;
            }
            state.profile.displayName = CommercialCore.clipped(name.getText().toString(), 80);
            state.profile.email = CommercialCore.clipped(email.getText().toString(), 160);
            state.profile.phone = CommercialCore.clipped(phone.getText().toString(), 40);
            state.profile.address = CommercialCore.clipped(address.getText().toString(), 240);
            state.profile.interestTags = CommercialCore.clipped(interests.getText().toString(), 600);
            state.profile.healthNotes = CommercialCore.clipped(health.getText().toString(), 1200);
            state.profile.benefitNotes = CommercialCore.clipped(benefit.getText().toString(), 1200);
            if (persistState()) toast("암호화해 저장했습니다.");
        });
        profileCard.addView(save, matchWrapWithTop(dp(12)));
        page.addView(profileCard, matchWrapWithTop(dp(20)));

        sectionTitle("안전 자동입력", "브라우저의 이름·이메일·전화·주소만");
        LinearLayout autofillCard = card();
        CommercialCore.HealthSnapshot healthSnapshot = CommercialCore.health(this);
        autofillCard.addView(text(
                healthSnapshot.autofillService ? "안전 자동입력 사용 중" : "안전 자동입력 꺼짐",
                17, true, healthSnapshot.autofillService ? SAGE : TERRACOTTA));
        autofillCard.addView(text(
                "비밀번호·아이디·OTP·계좌·카드 필드는 항상 제외하며 필드 의미가 모호하면 아무것도 채우지 않습니다.",
                14, false, MUTED), matchWrapWithTop(dp(5)));
        Button autofill = secondaryButton("Android 자동입력 설정 열기");
        autofill.setOnClickListener(v -> openSettingsAction(Settings.ACTION_SETTINGS));
        autofillCard.addView(autofill, matchWrapWithTop(dp(10)));
        page.addView(autofillCard, matchWrap());

        sectionTitle("외부 실행기", "정식 연결 전에는 성공으로 표시하지 않습니다");
        LinearLayout providerCard = card();
        addProviderRow(providerCard, "모니모", CommercialCore.isPackageInstalled(this, CommercialCore.PKG_MONIMO)
                ? "앱 연결 가능 · 실접수 검증 필요" : "설치 필요");
        addProviderRow(providerCard, "은행·오픈뱅킹", "정식 제공자 연결 필요");
        addProviderRow(providerCard, "AI 전화 예약", "전화 제공자 또는 Companion 필요");
        addProviderRow(providerCard, "AI 구독 모델", "공식 클라이언트 실행기 필요");
        addProviderRow(providerCard, "PC·Mac Companion", "기기 페어링 필요");
        page.addView(providerCard, matchWrap());

        sectionTitle("개인정보 제어", "언제든 기기에서 삭제할 수 있습니다");
        LinearLayout dangerCard = tintedCard(TERRACOTTA_SOFT);
        Button wipe = secondaryButton("모든 Life Agent 데이터 삭제");
        wipe.setTextColor(DANGER);
        wipe.setOnClickListener(v -> confirmWipe());
        dangerCard.addView(wipe, matchWrap());
        page.addView(dangerCard, matchWrap());
    }

    private void renderBottomNavigation() {
        addNav("홈", Tab.HOME);
        addNav("작업함", Tab.TASKS);
        addNav("자동화", Tab.AUTOMATIONS);
        addNav("내 정보", Tab.PROFILE);
    }

    private void addNav(String label, Tab tab) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(label);
        button.setTextSize(13);
        button.setTextColor(currentTab == tab ? SAGE : MUTED);
        button.setTypeface(Typeface.DEFAULT, currentTab == tab ? Typeface.BOLD : Typeface.NORMAL);
        button.setBackgroundColor(Color.TRANSPARENT);
        button.setMinHeight(dp(48));
        button.setOnClickListener(v -> {
            currentTab = tab;
            render();
        });
        nav.addView(button, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f));
    }

    private void addOpportunityCard(CommercialCore.OpportunityRecord opportunity) {
        LinearLayout card = card();
        TextView category = pill(categoryLabel(opportunity.category), SAGE_SOFT, SAGE);
        card.addView(category, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        card.addView(text(opportunity.title, 18, true, INK), matchWrapWithTop(dp(9)));
        card.addView(text(cleanReason(opportunity.reason), 14, false, MUTED), matchWrapWithTop(dp(5)));
        if (opportunity.sponsored) {
            card.addView(text("광고", 12, true, TERRACOTTA), matchWrapWithTop(dp(5)));
        }
        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setGravity(Gravity.CENTER_VERTICAL);
        Button primary = primaryButton(opportunity.actionLabel);
        primary.setOnClickListener(v -> acceptOpportunity(opportunity));
        actions.addView(primary, new LinearLayout.LayoutParams(0, dp(46), 1f));
        Button why = secondaryButton("왜?");
        why.setOnClickListener(v -> showMessage("이 추천을 보여드린 이유", cleanReason(opportunity.reason)));
        LinearLayout.LayoutParams whyParams = new LinearLayout.LayoutParams(dp(72), dp(46));
        whyParams.leftMargin = dp(8);
        actions.addView(why, whyParams);
        card.addView(actions, matchWrapWithTop(dp(12)));

        LinearLayout quietActions = new LinearLayout(this);
        quietActions.setOrientation(LinearLayout.HORIZONTAL);
        Button later = textButton("나중에");
        later.setOnClickListener(v -> updateOpportunity(opportunity.id,
                CommercialCore.OpportunityState.SNOOZED,
                System.currentTimeMillis() + TimeUnit.HOURS.toMillis(3)));
        quietActions.addView(later, new LinearLayout.LayoutParams(0, dp(42), 1f));
        Button auto = textButton("다음부터 자동");
        auto.setOnClickListener(v -> createSafeRuleFromOpportunity(opportunity));
        quietActions.addView(auto, new LinearLayout.LayoutParams(0, dp(42), 1f));
        Button stop = textButton("이런 추천 끄기");
        stop.setOnClickListener(v -> disableCategory(opportunity.category));
        quietActions.addView(stop, new LinearLayout.LayoutParams(0, dp(42), 1.3f));
        card.addView(quietActions, matchWrapWithTop(dp(3)));
        page.addView(card, matchWrapWithTop(dp(10)));
    }

    private void addTaskCard(CommercialCore.TaskRecord task) {
        LinearLayout card = card();
        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.addView(pill(statusLabel(task.status), statusColor(task.status), statusTextColor(task.status)));
        Space space = new Space(this);
        top.addView(space, new LinearLayout.LayoutParams(0, 1, 1f));
        top.addView(text(task.executor.name(), 11, true, MUTED));
        card.addView(top, matchWrap());
        card.addView(text(task.goal, 18, true, INK), matchWrapWithTop(dp(9)));
        card.addView(text(task.nextAction, 14, false, MUTED), matchWrapWithTop(dp(5)));
        card.setOnClickListener(v -> showTask(task.id));
        page.addView(card, matchWrapWithTop(dp(12)));
    }

    private void previewCommand() {
        if (commandInput == null) return;
        String goal = commandInput.getText().toString().trim();
        if (goal.isEmpty()) {
            commandInput.setError("처리할 목표를 입력하세요.");
            return;
        }
        hideKeyboard();
        CommercialCore.Plan plan = CommercialCore.Planner.plan(this, goal, state);
        showPlan(plan);
    }

    private void showPlan(CommercialCore.Plan plan) {
        LinearLayout body = dialogBody();
        body.addView(text(plan.title, 22, true, INK));
        body.addView(text(plan.subtitle, 14, false, MUTED), matchWrapWithTop(dp(5)));
        body.addView(pill(integrationLabel(plan.integration), integrationColor(plan.integration), INK),
                new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(32)));
        body.addView(text("실행기  " + plan.executor.name(), 13, true, SAGE), matchWrapWithTop(dp(12)));
        body.addView(text("확인 정책  " + gateLabel(plan.gate), 13, true, SAGE), matchWrapWithTop(dp(4)));
        body.addView(text("완료 증거  " + plan.verificationType, 13, false, MUTED), matchWrapWithTop(dp(4)));
        body.addView(text("실행 계획", 16, true, INK), matchWrapWithTop(dp(15)));
        for (int i = 0; i < plan.steps.size(); i++) {
            body.addView(text((i + 1) + ". " + plan.steps.get(i), 14, false, INK), matchWrapWithTop(dp(5)));
        }
        body.addView(text("다음 행동: " + plan.nextAction, 14, false, MUTED), matchWrapWithTop(dp(14)));

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setView(body)
                .setNegativeButton("취소", null)
                .setPositiveButton(plan.gate == CommercialCore.Gate.BLOCK ? "확인" : "작업 만들기", null)
                .create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(v -> {
                    if (plan.gate == CommercialCore.Gate.BLOCK) {
                        dialog.dismiss();
                        return;
                    }
                    if (plan.gate == CommercialCore.Gate.DEVICE_CREDENTIAL) {
                        Intent credential = CommercialCore.deviceCredentialIntent(
                                this, "Life Agent 확인", "민감한 작업 초안을 만들기 전에 기기를 인증하세요.");
                        if (credential == null) {
                            showMessage("기기 잠금이 필요합니다",
                                    "PIN·패턴·비밀번호 또는 생체인증을 먼저 설정하세요.");
                            return;
                        }
                        pendingCredentialPlan = plan;
                        startActivityForResult(credential, REQUEST_DEVICE_CREDENTIAL);
                        dialog.dismiss();
                        return;
                    }
                    createTaskFromPlan(plan, false);
                    dialog.dismiss();
                }));
        dialog.show();
    }

    private void createTaskFromPlan(CommercialCore.Plan plan, boolean authenticated) {
        try {
            CommercialCore.TaskRecord task = CommercialCore.createTask(this, plan);
            reloadState();
            toast("작업함에 안전하게 저장했습니다.");
            if (plan.integration == CommercialCore.Integration.READY
                    || plan.integration == CommercialCore.Integration.PARTIAL) {
                if (plan.gate == CommercialCore.Gate.AUTO
                        || authenticated
                        || plan.gate == CommercialCore.Gate.CONFIRM) {
                    launchTask(task);
                }
            } else {
                currentTab = Tab.TASKS;
                render();
            }
        } catch (CommercialCore.StoreException error) {
            showStoreError(error);
        }
    }

    private void launchTask(CommercialCore.TaskRecord task) {
        Intent intent = CommercialCore.launchSkillIntent(this, task);
        if (intent == null) {
            showMessage("실행기를 열 수 없습니다", "이 작업에 필요한 정식 제공자 연결이 없습니다.");
            return;
        }
        try {
            startActivity(intent);
        } catch (ActivityNotFoundException | SecurityException error) {
            try {
                CommercialCore.markTaskProblem(this, task.id, "EXECUTOR_UNAVAILABLE",
                        "필요한 앱 또는 제공자 연결을 확인하세요.");
                reloadState();
            } catch (CommercialCore.StoreException storeError) {
                showStoreError(storeError);
                return;
            }
            showMessage("실행기를 열 수 없습니다", "필요한 앱 또는 제공자 연결을 확인하세요.");
        }
    }

    private void acceptOpportunity(CommercialCore.OpportunityRecord opportunity) {
        updateOpportunity(opportunity.id, CommercialCore.OpportunityState.ACCEPTED, 0L);
        if ("nearby_pharmacy".equals(opportunity.category)) {
            Location location = CommercialLocationService.lastKnownLocation();
            Intent map = CommercialCore.openNearbyPharmacyIntent(location);
            if (map == null) {
                showMessage("현재 위치가 아직 없습니다", "주변 기회 세션을 켜고 위치가 갱신될 때까지 잠시 기다리세요.");
                return;
            }
            try {
                startActivity(map);
            } catch (ActivityNotFoundException e) {
                showMessage("지도 앱이 없습니다", "지도 검색을 처리할 앱을 설치해야 합니다.");
            }
            return;
        }
        String goal;
        switch (opportunity.skillId) {
            case "insurance.claim.monimo":
                goal = "보험 추가서류와 청구 상태를 확인해줘";
                break;
            case "benefit.autopilot":
                goal = "도착한 지원 혜택 후보를 검토해줘";
                break;
            case "reservation.orchestrator":
                goal = "변경된 예약 상태를 확인하고 해결해줘";
                break;
            case "stream.autoopen":
                goal = "도착한 방송 알림을 열어줘";
                break;
            default:
                goal = opportunity.title;
                break;
        }
        showPlan(CommercialCore.Planner.plan(this, goal, state));
    }

    private void showOpportunity(String id) {
        CommercialCore.OpportunityRecord opportunity = CommercialCore.findOpportunity(state, id);
        if (opportunity == null) return;
        new AlertDialog.Builder(this)
                .setTitle(opportunity.title)
                .setMessage(cleanReason(opportunity.reason))
                .setNegativeButton("나중에", (d, w) -> updateOpportunity(id,
                        CommercialCore.OpportunityState.SNOOZED,
                        System.currentTimeMillis() + TimeUnit.HOURS.toMillis(3)))
                .setPositiveButton(opportunity.actionLabel, (d, w) -> acceptOpportunity(opportunity))
                .show();
    }

    private void showTask(String taskId) {
        CommercialCore.TaskRecord task = CommercialCore.findTask(state, taskId);
        if (task == null) return;
        StringBuilder message = new StringBuilder();
        message.append("상태: ").append(statusLabel(task.status)).append('\n');
        message.append("실행기: ").append(task.executor).append('\n');
        message.append("연동: ").append(integrationLabel(task.integration)).append('\n');
        message.append("완료 증거: ").append(task.verificationType).append("\n\n");
        message.append("다음 행동\n").append(task.nextAction);
        if (!TextUtils.isEmpty(task.failureCode)) {
            message.append("\n\n문제 코드: ").append(task.failureCode);
        }
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle(task.goal)
                .setMessage(message.toString())
                .setNegativeButton("닫기", null)
                .setNeutralButton("완료 증거 입력", null)
                .setPositiveButton("계속", null)
                .create();
        dialog.setOnShowListener(ignored -> {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                launchTask(task);
                dialog.dismiss();
            });
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> {
                dialog.dismiss();
                promptEvidence(task);
            });
        });
        dialog.show();
    }

    private void promptEvidence(CommercialCore.TaskRecord task) {
        EditText input = editText(
                "예: 예약 확인번호, 보험 접수번호, 거래 영수증 식별자",
                task.evidence, 2);
        new AlertDialog.Builder(this)
                .setTitle("외부 완료 증거")
                .setMessage("버튼을 눌렀다는 사실만으로 완료 처리하지 않습니다.")
                .setView(input)
                .setNegativeButton("취소", null)
                .setPositiveButton("검증 기록", (dialog, which) -> {
                    try {
                        boolean completed = CommercialCore.completeTask(
                                this, task.id, input.getText().toString().trim());
                        reloadState();
                        render();
                        toast(completed ? "완료 증거와 함께 종료했습니다." : "증거가 부족해 검증 중으로 남겼습니다.");
                    } catch (CommercialCore.StoreException error) {
                        showStoreError(error);
                    }
                })
                .show();
    }

    private void createSafeRuleFromOpportunity(CommercialCore.OpportunityRecord opportunity) {
        if (!("stream".equals(opportunity.category) || "update".equals(opportunity.category))) {
            showMessage("자동화할 수 없는 유형입니다",
                    "보험 제출, 혜택 신청, 예약 변경처럼 외부 결과가 중요한 작업은 사용자 확인을 유지합니다.");
            return;
        }
        updateOpportunity(opportunity.id, CommercialCore.OpportunityState.AUTO_RULE_CREATED, 0L);
        showMessage("안전 자동화로 표시했습니다",
                "저위험이고 정확한 조건이 있는 경우에만 모델 없이 실행됩니다.");
    }

    private void ensureLocationSession() {
        if (checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED) {
            startLocationSession();
            return;
        }
        requestPermissions(new String[]{Manifest.permission.ACCESS_COARSE_LOCATION}, REQUEST_LOCATION);
    }

    private void startLocationSession() {
        state.settings.nearbyOpportunities = true;
        state.settings.locationSessionEndMs = System.currentTimeMillis() + TimeUnit.HOURS.toMillis(2);
        if (!persistState()) return;
        Intent service = new Intent(this, CommercialLocationService.class);
        service.setAction(CommercialLocationService.ACTION_START);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(service);
        else startService(service);
        toast("주변 기회 감지를 2시간 동안 시작했습니다.");
    }

    private void stopLocationSession() {
        Intent stop = new Intent(this, CommercialLocationService.class);
        stop.setAction(CommercialLocationService.ACTION_STOP);
        startService(stop);
    }

    private void showHealth() {
        CommercialCore.HealthSnapshot health = CommercialCore.health(this);
        StringBuilder message = new StringBuilder();
        message.append(line("암호화 저장소", health.encryptedStore));
        message.append(line("기기 화면 잠금", health.deviceSecure));
        message.append(line("앱 알림", health.notificationPermission));
        message.append(line("알림 접근", health.notificationListener));
        message.append(line("안전 자동입력", health.autofillService));
        message.append(line("대략적 위치", health.coarseLocation));
        message.append("\n외부 연결\n");
        message.append("모니모: ").append(health.monimoInstalled ? "설치됨" : "설치 필요").append('\n');
        message.append("SOOP: ").append(health.soopInstalled ? "설치됨" : "설치 안 됨").append('\n');
        message.append("치지직: ").append(health.chzzkInstalled ? "설치됨" : "설치 안 됨").append('\n');
        message.append("RustDesk: ").append(health.rustDeskInstalled ? "설치됨" : "설치 안 됨").append('\n');
        message.append("은행·전화·AI·Companion: 정식 연결 필요");
        if (!health.blockers.isEmpty()) {
            message.append("\n\n차단 항목\n");
            for (String blocker : health.blockers) message.append("• ").append(blocker).append('\n');
        }
        new AlertDialog.Builder(this)
                .setTitle("상용화 상태 점검")
                .setMessage(message.toString())
                .setNegativeButton("닫기", null)
                .setNeutralButton("알림 권한", (d, w) -> requestNotificationPermission())
                .setPositiveButton("알림 접근", (d, w) ->
                        openSettingsAction(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                .show();
    }

    private void confirmWipe() {
        new AlertDialog.Builder(this)
                .setTitle("모든 데이터를 삭제할까요?")
                .setMessage("개인정보, 작업, 추천, 자동화 규칙과 암호화 키가 삭제됩니다. 되돌릴 수 없습니다.")
                .setNegativeButton("취소", null)
                .setPositiveButton("모두 삭제", (dialog, which) -> {
                    Intent credential = CommercialCore.deviceCredentialIntent(
                            this, "Life Agent 데이터 삭제", "삭제 전 기기를 인증하세요.");
                    if (credential == null) {
                        showMessage("기기 잠금이 필요합니다", "먼저 기기 화면 잠금을 설정하세요.");
                        return;
                    }
                    new AlertDialog.Builder(this)
                            .setTitle("마지막 확인")
                            .setMessage("정말 삭제하려면 다시 '삭제'를 누르세요.")
                            .setNegativeButton("취소", null)
                            .setPositiveButton("삭제", (d, w) -> wipeNow())
                            .show();
                })
                .show();
    }

    private void wipeNow() {
        stopLocationSession();
        try {
            CommercialCore.SecureJsonStore.wipe(this);
            state = new CommercialCore.AppState();
            render();
            toast("Life Agent 데이터를 삭제했습니다.");
        } catch (CommercialCore.StoreException error) {
            showStoreError(error);
        }
    }

    private void ingestEntryIntent(Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        String incoming = intent.getStringExtra("lifeagent.os.command");
        if (Intent.ACTION_SEND.equals(action)) {
            String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
            if (!TextUtils.isEmpty(sharedText)) incoming = sharedText;
            else if (intent.getParcelableExtra(Intent.EXTRA_STREAM) != null) {
                incoming = "공유한 문서를 확인해서 필요한 일을 처리해줘";
            }
        } else if (Intent.ACTION_PROCESS_TEXT.equals(action)) {
            CharSequence selected = intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT);
            if (!TextUtils.isEmpty(selected)) incoming = selected.toString();
        }
        if (!TextUtils.isEmpty(incoming)) {
            final String goal = CommercialCore.clipped(CommercialCore.redact(incoming), 600);
            page.post(() -> {
                currentTab = Tab.HOME;
                render();
                if (commandInput != null) {
                    commandInput.setText(goal);
                    commandInput.setSelection(commandInput.length());
                }
            });
        }
    }

    private void startVoice() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.KOREAN.toLanguageTag());
        intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "처리할 목표를 말하세요");
        try {
            startActivityForResult(intent, REQUEST_VOICE);
        } catch (ActivityNotFoundException e) {
            toast("음성 인식 앱을 찾을 수 없습니다.");
        }
    }

    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQUEST_NOTIFICATIONS);
        } else {
            toast("앱 알림 권한이 이미 허용돼 있습니다.");
        }
    }

    private void openSettingsAction(String action) {
        try {
            startActivity(new Intent(action));
        } catch (ActivityNotFoundException e) {
            Intent details = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:" + getPackageName()));
            startActivity(details);
        }
    }

    private boolean persistState() {
        try {
            CommercialCore.save(this, state);
            return true;
        } catch (CommercialCore.StoreException error) {
            showStoreError(error);
            return false;
        }
    }

    private void reloadState() {
        try {
            state = CommercialCore.load(this);
        } catch (CommercialCore.StoreException error) {
            showStoreError(error);
        }
    }

    private void loadStateOrShowRecovery() {
        try {
            state = CommercialCore.load(this);
        } catch (CommercialCore.StoreException error) {
            state = new CommercialCore.AppState();
        }
    }

    private void showStoreError(CommercialCore.StoreException error) {
        showMessage("안전 저장에 실패했습니다",
                "데이터를 성공으로 표시하지 않았습니다. 앱을 다시 열고 상태 점검을 실행하세요.\n\n오류 코드: "
                        + CommercialCore.clipped(error.getMessage(), 100));
    }

    private void updateOpportunity(
            String id, CommercialCore.OpportunityState newState, long snoozeUntil) {
        try {
            CommercialCore.updateOpportunity(this, id, newState, snoozeUntil);
            reloadState();
            render();
        } catch (CommercialCore.StoreException error) {
            showStoreError(error);
        }
    }

    private void disableCategory(String category) {
        new AlertDialog.Builder(this)
                .setTitle("이런 추천을 끌까요?")
                .setMessage("'" + categoryLabel(category) + "' 유형의 추천을 더 이상 표시하지 않습니다.")
                .setNegativeButton("취소", null)
                .setPositiveButton("끄기", (d, w) -> {
                    try {
                        CommercialCore.disableOpportunityCategory(this, category);
                        reloadState();
                        render();
                    } catch (CommercialCore.StoreException error) {
                        showStoreError(error);
                    }
                }).show();
    }

    private List<CommercialCore.OpportunityRecord> visibleOpportunities() {
        long now = System.currentTimeMillis();
        List<CommercialCore.OpportunityRecord> result = new ArrayList<>();
        for (CommercialCore.OpportunityRecord item : state.opportunities) {
            if (item.state == CommercialCore.OpportunityState.DISMISSED) continue;
            if (item.state == CommercialCore.OpportunityState.SNOOZED && item.snoozeUntil > now) continue;
            result.add(item);
        }
        return result;
    }

    private List<CommercialCore.StreamRule> parseStreamRules(String raw) {
        List<CommercialCore.StreamRule> result = new ArrayList<>();
        String[] lines = raw.split("\\r?\\n");
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i].trim();
            if (line.isEmpty()) continue;
            String[] parts = line.split("\\|", -1);
            if (parts.length != 3) throw new IllegalArgumentException(
                    (i + 1) + "번째 줄은 플랫폼|별칭|공식URL 형식이어야 합니다.");
            CommercialCore.StreamRule rule = new CommercialCore.StreamRule();
            rule.platform = parts[0].trim().toLowerCase(Locale.ROOT);
            rule.alias = CommercialCore.normalize(parts[1]);
            rule.channelUrl = parts[2].trim();
            if (!("soop".equals(rule.platform) || "chzzk".equals(rule.platform))) {
                throw new IllegalArgumentException((i + 1) + "번째 플랫폼은 soop 또는 chzzk여야 합니다.");
            }
            if (rule.alias.length() < 2) {
                throw new IllegalArgumentException((i + 1) + "번째 별칭은 두 글자 이상이어야 합니다.");
            }
            if (!CommercialCore.isAllowedChannelUrl(rule.platform, rule.channelUrl)) {
                throw new IllegalArgumentException((i + 1) + "번째 URL이 공식 허용 도메인이 아닙니다.");
            }
            result.add(rule);
        }
        return result;
    }

    private String formatStreamRules() {
        StringBuilder result = new StringBuilder();
        for (CommercialCore.StreamRule rule : state.settings.streamRules) {
            if (result.length() > 0) result.append('\n');
            result.append(rule.platform).append('|').append(rule.alias).append('|').append(rule.channelUrl);
        }
        return result.toString();
    }

    private void addPromptChip(String prompt) {
        Button chip = secondaryButton(prompt);
        chip.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        chip.setPadding(dp(16), 0, dp(16), 0);
        chip.setOnClickListener(v -> {
            if (commandInput == null) {
                currentTab = Tab.HOME;
                render();
            }
            commandInput.setText(prompt);
            commandInput.setSelection(commandInput.length());
        });
        page.addView(chip, matchWrapWithTop(dp(8)));
    }

    private void sectionTitle(String title, String note) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.BOTTOM);
        TextView heading = text(title, 20, true, INK);
        row.addView(heading, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        row.addView(text(note, 12, false, MUTED));
        page.addView(row, matchWrapWithTop(dp(26)));
        Space space = new Space(this);
        page.addView(space, new LinearLayout.LayoutParams(1, dp(9)));
    }

    private LinearLayout card() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(16), dp(16), dp(16));
        card.setBackground(rounded(CARD, BORDER, 18));
        card.setElevation(dp(1));
        return card;
    }

    private LinearLayout tintedCard(int color) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(14), dp(16), dp(14));
        card.setBackground(rounded(color, Color.TRANSPARENT, 16));
        return card;
    }

    private LinearLayout dialogBody() {
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(dp(24), dp(22), dp(24), dp(4));
        ScrollView scroll = new ScrollView(this);
        scroll.addView(body);
        return body;
    }

    private Button primaryButton(String label) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(label);
        button.setTextSize(14);
        button.setTextColor(Color.WHITE);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setBackground(rounded(SAGE, Color.TRANSPARENT, 14));
        button.setMinHeight(dp(48));
        return button;
    }

    private Button secondaryButton(String label) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(label);
        button.setTextSize(14);
        button.setTextColor(INK);
        button.setBackground(rounded(CARD, BORDER, 14));
        button.setMinHeight(dp(48));
        return button;
    }

    private Button inlineButton(String label) {
        Button button = textButton(label);
        button.setTextColor(SAGE);
        button.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        return button;
    }

    private Button textButton(String label) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(label);
        button.setTextSize(12);
        button.setTextColor(MUTED);
        button.setBackgroundColor(Color.TRANSPARENT);
        button.setMinHeight(dp(40));
        button.setPadding(dp(4), 0, dp(4), 0);
        return button;
    }

    private CheckBox checkBox(String label, boolean checked) {
        CheckBox box = new CheckBox(this);
        box.setText(label);
        box.setTextSize(15);
        box.setTextColor(INK);
        box.setChecked(checked);
        box.setMinHeight(dp(48));
        return box;
    }

    private EditText field(String hint, String value, int inputType) {
        EditText field = editText(hint, value, 1);
        field.setInputType(inputType);
        return field;
    }

    private EditText editText(String hint, String value, int lines) {
        EditText edit = new EditText(this);
        edit.setHint(hint);
        edit.setText(value == null ? "" : value);
        edit.setTextSize(15);
        edit.setTextColor(INK);
        edit.setHintTextColor(Color.rgb(142, 139, 131));
        edit.setMinLines(lines);
        edit.setMaxLines(Math.max(lines, 6));
        edit.setPadding(dp(13), dp(11), dp(13), dp(11));
        edit.setBackground(rounded(Color.WHITE, BORDER, 12));
        return edit;
    }

    private TextView text(String value, int size, boolean bold, int color) {
        TextView text = new TextView(this);
        text.setText(value == null ? "" : value);
        text.setTextSize(size);
        text.setTextColor(color);
        text.setLineSpacing(0f, 1.12f);
        if (bold) text.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return text;
    }

    private TextView pill(String value, int background, int foreground) {
        TextView pill = text(value, 12, true, foreground);
        pill.setGravity(Gravity.CENTER);
        pill.setPadding(dp(10), dp(5), dp(10), dp(5));
        pill.setBackground(rounded(background, Color.TRANSPARENT, 30));
        return pill;
    }

    private GradientDrawable rounded(int fill, int stroke, int radiusDp) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fill);
        drawable.setCornerRadius(dp(radiusDp));
        if (stroke != Color.TRANSPARENT) drawable.setStroke(dp(1), stroke);
        return drawable;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams matchWrapWithTop(int top) {
        LinearLayout.LayoutParams params = matchWrap();
        params.topMargin = top;
        return params;
    }

    private void addProviderRow(LinearLayout parent, String name, String status) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.addView(text(name, 15, true, INK), new LinearLayout.LayoutParams(0, dp(44), 1f));
        row.addView(text(status, 13, false, MUTED));
        parent.addView(row, matchWrap());
    }

    private String installedSuffix(String packageName) {
        return CommercialCore.isPackageInstalled(this, packageName) ? " · 설치됨" : " · 설치 안 됨";
    }

    private static String statusLabel(CommercialCore.TaskStatus status) {
        switch (status) {
            case COMPLETED: return "완료";
            case NEEDS_AUTH: return "인증 필요";
            case NEEDS_CONFIRMATION: return "확인 필요";
            case VERIFYING: return "결과 확인 중";
            case PROBLEM: return "문제";
            case CANCELLED: return "취소";
            case RUNNING: return "진행 중";
            case READY: return "준비됨";
            default: return "초안";
        }
    }

    private static int statusColor(CommercialCore.TaskStatus status) {
        switch (status) {
            case COMPLETED: return SAGE_SOFT;
            case PROBLEM: return TERRACOTTA_SOFT;
            case NEEDS_AUTH:
            case NEEDS_CONFIRMATION:
            case VERIFYING: return AMBER_SOFT;
            default: return Color.rgb(236, 234, 229);
        }
    }

    private static int statusTextColor(CommercialCore.TaskStatus status) {
        return status == CommercialCore.TaskStatus.PROBLEM ? DANGER : INK;
    }

    private static String integrationLabel(CommercialCore.Integration integration) {
        switch (integration) {
            case READY: return "실행 가능";
            case PARTIAL: return "일부 연결됨";
            case BLOCKED: return "실행 차단";
            default: return "연결 필요";
        }
    }

    private static int integrationColor(CommercialCore.Integration integration) {
        switch (integration) {
            case READY: return SAGE_SOFT;
            case BLOCKED: return TERRACOTTA_SOFT;
            default: return AMBER_SOFT;
        }
    }

    private static String gateLabel(CommercialCore.Gate gate) {
        switch (gate) {
            case AUTO: return "자동 실행";
            case DEVICE_CREDENTIAL: return "기기 인증";
            case MANUAL_AUTH: return "사용자 직접 인증";
            case BLOCK: return "실행 금지";
            default: return "실행 전 확인";
        }
    }

    private static String categoryLabel(String category) {
        switch (category) {
            case "insurance": return "보험";
            case "benefit": return "혜택 후보";
            case "reservation": return "예약";
            case "stream": return "방송";
            case "update": return "업데이트";
            case "nearby_pharmacy": return "주변 기회";
            default: return "필요한 일";
        }
    }

    private static String cleanReason(String reason) {
        if (reason == null) return "";
        return reason.replaceAll("nearby_pharmacy:[^ ]+", "대략적 위치 구역만 중복 방지에 사용했습니다.");
    }

    private static String line(String title, boolean pass) {
        return (pass ? "✓ " : "✕ ") + title + '\n';
    }

    private void hideKeyboard() {
        View focus = getCurrentFocus();
        if (focus == null) return;
        InputMethodManager manager = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        if (manager != null) manager.hideSoftInputFromWindow(focus.getWindowToken(), 0);
    }

    private void showMessage(String title, String message) {
        new AlertDialog.Builder(this)
                .setTitle(title)
                .setMessage(message)
                .setPositiveButton("확인", null)
                .show();
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private static final class AppToggle {
        final String label;
        final String packageName;
        CheckBox box;

        AppToggle(String label, String packageName) {
            this.label = label;
            this.packageName = packageName;
        }
    }
}
