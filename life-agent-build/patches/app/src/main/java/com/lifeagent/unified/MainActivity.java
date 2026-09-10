package com.lifeagent.unified;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ComponentName;
import android.content.Intent;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.speech.RecognizerIntent;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.inputmethod.InputMethodManager;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Goal- and context-centric shell for Life Agent OS. */
public final class MainActivity extends Activity {
    private static final int VOICE_REQUEST = 5201;
    private static final int HOME = 0, TASKS = 1, AUTOMATIONS = 2, ME = 3;

    private final Map<Integer, Button> navButtons = new HashMap<>();
    private FrameLayout host;
    private LinearLayout nav;
    private EditText commandInput;
    private int currentTab = HOME;
    private String commandDraft = "";
    private AgentOsCore.ContextSnapshot currentContext = AgentOsCore.ContextSnapshot.empty();
    private AgentOsCore.Registry registry;
    private AgentOsCore.TaskGraph graph;
    private AgentOsCore.Recipes recipes;
    private AgentOsCore.Planner planner;

    @Override protected void onCreate(Bundle state) {
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        super.onCreate(state);
        getWindow().setStatusBarColor(AgentUi.CANVAS);
        getWindow().setNavigationBarColor(AgentUi.SURFACE);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        registry = AgentOsCore.Registry.get();
        graph = new AgentOsCore.TaskGraph(this);
        recipes = new AgentOsCore.Recipes(this);
        planner = new AgentOsCore.Planner(this);
        currentContext = AgentOsCore.ContextEngine.capture(this, getIntent());
        commandDraft = AgentOsCore.ContextEngine.recommendedPrompt(currentContext);
        AgentShortcutPublisher.publish(this);
        buildShell();
        applyIntent(getIntent());
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        currentContext = AgentOsCore.ContextEngine.capture(this, intent);
        applyIntent(intent);
    }

    @Override protected void onResume() {
        super.onResume();
        if (host != null) showTab(currentTab);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == VOICE_REQUEST && resultCode == RESULT_OK && data != null) {
            ArrayList<String> results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
            if (results != null && !results.isEmpty()) {
                commandDraft = results.get(0);
                showTab(HOME);
                planCommand();
            }
        }
    }

    private void buildShell() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(AgentUi.CANVAS);
        host = new FrameLayout(this);
        root.addView(host, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setGravity(Gravity.CENTER);
        nav.setPadding(dp(8), dp(8), dp(8), dp(10));
        nav.setBackground(AgentUi.round(AgentUi.SURFACE, 0, AgentUi.LINE, 1));
        addNav(HOME, "⌂", "홈");
        addNav(TASKS, "☷", "작업함");
        addNav(AUTOMATIONS, "⌘", "자동화");
        addNav(ME, "●", "내 정보");
        root.addView(nav, AgentUi.matchWrap());
        setContentView(root);
    }

    private void addNav(int tab, String glyph, String label) {
        Button button = new Button(this);
        button.setAllCaps(false);
        button.setText(glyph + "\n" + label);
        button.setTextSize(12);
        button.setGravity(Gravity.CENTER);
        button.setMinHeight(dp(58));
        button.setPadding(dp(4), dp(5), dp(4), dp(5));
        button.setOnClickListener(v -> showTab(tab));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        p.leftMargin = dp(2); p.rightMargin = dp(2);
        nav.addView(button, p);
        navButtons.put(tab, button);
    }

    private void applyIntent(Intent intent) {
        if (intent == null) { showTab(HOME); return; }
        String tab = intent.getStringExtra(AgentOsCore.EXTRA_TAB);
        String command = intent.getStringExtra(AgentOsCore.EXTRA_COMMAND);
        if (command != null && !command.trim().isEmpty()) commandDraft = command.trim();
        if ("automations".equalsIgnoreCase(tab)) currentTab = AUTOMATIONS;
        else if ("tasks".equalsIgnoreCase(tab)) currentTab = TASKS;
        else if ("me".equalsIgnoreCase(tab)) currentTab = ME;
        else currentTab = HOME;
        showTab(currentTab);
        String skillId = intent.getStringExtra(AgentOsCore.EXTRA_SKILL_ID);
        AgentOsCore.Skill skill = registry.find(skillId);
        if (skill != null && !skill.examples.isEmpty()) {
            commandDraft = skill.examples.get(0);
            showTab(HOME);
        }
    }

    private void showTab(int tab) {
        if (currentTab == HOME && commandInput != null) commandDraft = commandInput.getText().toString();
        currentTab = tab;
        host.removeAllViews();
        View content;
        if (tab == TASKS) content = tasksScreen();
        else if (tab == AUTOMATIONS) content = automationsScreen();
        else if (tab == ME) content = meScreen();
        else content = homeScreen();
        host.addView(content, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        updateNav();
    }

    private void updateNav() {
        for (Map.Entry<Integer, Button> entry : navButtons.entrySet()) {
            boolean selected = entry.getKey() == currentTab;
            Button b = entry.getValue();
            b.setTextColor(selected ? AgentUi.SAGE_DARK : AgentUi.INK_SOFT);
            b.setTypeface(Typeface.DEFAULT, selected ? Typeface.BOLD : Typeface.NORMAL);
            b.setBackground(AgentUi.round(selected ? AgentUi.SAGE_PALE : AgentUi.SURFACE, 16, 0, 0));
        }
    }

    private View homeScreen() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout body = body();
        body.addView(topBar("Life Agent", "개인 에이전트 OS"), AgentUi.matchWrap());
        body.addView(commandSurface(), AgentUi.spaced(this, 20, 0));
        addContext(body);

        List<AgentOsCore.Task> attention = graph.attention();
        if (!attention.isEmpty()) {
            body.addView(section("내가 개입할 일", attention.size() + "건"), AgentUi.spaced(this, 22, 10));
            for (int i = 0; i < Math.min(3, attention.size()); i++) body.addView(taskCard(attention.get(i)), AgentUi.spaced(this, 0, 10));
        }
        List<AgentOsCore.Task> running = new ArrayList<>();
        for (AgentOsCore.Task task : graph.active()) if (!task.attention()) running.add(task);
        if (!running.isEmpty()) {
            body.addView(section("진행 중", running.size() + "건"), AgentUi.spaced(this, 22, 10));
            for (int i = 0; i < Math.min(3, running.size()); i++) body.addView(taskCard(running.get(i)), AgentUi.spaced(this, 0, 10));
        }
        body.addView(section("지금 맡기기 좋은 일", "문맥에 따라 바뀝니다"), AgentUi.spaced(this, 22, 10));
        for (AgentOsCore.Skill skill : registry.recommendations(currentContext, 4)) body.addView(skillSuggestion(skill), AgentUi.spaced(this, 0, 10));
        TextView footer = AgentUi.text(this, "공식 API·Intent·검증된 규칙을 모델보다 먼저 사용합니다. 성공 증거가 없으면 완료로 표시하지 않습니다.", 12, false, AgentUi.INK_SOFT);
        footer.setLineSpacing(0, 1.25f); footer.setPadding(dp(4), dp(16), dp(4), dp(28));
        body.addView(footer, AgentUi.matchWrap());
        scroll.addView(body);
        return scroll;
    }

    private View commandSurface() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(18), dp(18), dp(18), dp(16));
        panel.setBackground(AgentUi.round(AgentUi.SURFACE, 24, AgentUi.LINE, 1));
        panel.setElevation(dp(2));
        panel.addView(AgentUi.text(this, "목표만 말하세요", 13, true, AgentUi.SAGE_DARK), AgentUi.matchWrap());
        TextView headline = AgentUi.text(this, "앱을 고르지 않아도 됩니다", 22, true, AgentUi.INK);
        headline.setPadding(0, dp(5), 0, dp(12)); panel.addView(headline, AgentUi.matchWrap());
        commandInput = new EditText(this);
        commandInput.setHint("예: 금요일 오후에 정형외과 예약해줘");
        commandInput.setText(commandDraft);
        commandInput.setTextSize(17); commandInput.setTextColor(AgentUi.INK); commandInput.setHintTextColor(0xff949990);
        commandInput.setGravity(Gravity.TOP | Gravity.START);
        commandInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        commandInput.setMinLines(3); commandInput.setMaxLines(6);
        commandInput.setPadding(dp(14), dp(13), dp(14), dp(13));
        commandInput.setBackground(AgentUi.round(AgentUi.CANVAS, 18, AgentUi.LINE, 1));
        panel.addView(commandInput, AgentUi.matchWrap());
        LinearLayout actions = new LinearLayout(this); actions.setOrientation(LinearLayout.HORIZONTAL);
        Button voice = AgentUi.secondary(this, "음성", v -> startVoice());
        LinearLayout.LayoutParams vp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, .34f); vp.topMargin=dp(12); vp.rightMargin=dp(8); actions.addView(voice, vp);
        Button plan = AgentUi.primary(this, "처리 계획 보기", v -> planCommand());
        LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, .66f); pp.topMargin=dp(12); actions.addView(plan, pp);
        panel.addView(actions, AgentUi.matchWrap());
        return panel;
    }

    private void addContext(LinearLayout body) {
        String summary = currentContext.safeSummary;
        String label = currentContext.label();
        AgentOsCore.Event last = AgentOsCore.Events.last(this);
        if (summary.isEmpty() && last.fresh(30 * 60 * 1000L)) { summary = last.summary; label = "최근 상황"; }
        if (summary.isEmpty()) return;
        LinearLayout content = new LinearLayout(this); content.setOrientation(LinearLayout.VERTICAL);
        LinearLayout head = new LinearLayout(this); head.setOrientation(LinearLayout.HORIZONTAL); head.setGravity(Gravity.CENTER_VERTICAL);
        head.addView(AgentUi.pill(this, label, AgentUi.TERRA_PALE, AgentUi.TERRA), AgentUi.wrapWrap());
        head.addView(AgentUi.text(this, "  현재 계획에 함께 사용", 12, false, AgentUi.INK_SOFT), AgentUi.wrapWrap());
        content.addView(head, AgentUi.matchWrap());
        TextView text = AgentUi.text(this, summary, 15, false, AgentUi.INK); text.setLineSpacing(0,1.2f); text.setPadding(0,dp(10),0,0); content.addView(text,AgentUi.matchWrap());
        body.addView(AgentUi.card(this, content, AgentUi.TERRA_PALE), AgentUi.spaced(this, 12, 0));
    }

    private View skillSuggestion(AgentOsCore.Skill skill) {
        LinearLayout row = new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL); row.setGravity(Gravity.CENTER_VERTICAL);
        TextView glyph = AgentUi.text(this, skill.glyph, 24, true, AgentUi.SAGE_DARK); glyph.setGravity(Gravity.CENTER); glyph.setBackground(AgentUi.round(AgentUi.SAGE_PALE,18,0,0));
        LinearLayout.LayoutParams gp=new LinearLayout.LayoutParams(dp(52),dp(52));gp.rightMargin=dp(14);row.addView(glyph,gp);
        LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.addView(AgentUi.text(this,skill.title,16,true,AgentUi.INK),AgentUi.matchWrap());
        TextView sub=AgentUi.text(this,skill.subtitle,13,false,AgentUi.INK_SOFT);sub.setMaxLines(2);sub.setPadding(0,dp(3),0,0);copy.addView(sub,AgentUi.matchWrap());
        row.addView(copy,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));row.addView(AgentUi.text(this,"›",28,false,AgentUi.INK_SOFT),AgentUi.wrapWrap());
        LinearLayout card=AgentUi.card(this,row,AgentUi.SURFACE);card.setClickable(true);card.setFocusable(true);card.setOnClickListener(v->seed(skill));return card;
    }

    private View tasksScreen() {
        ScrollView scroll=new ScrollView(this);LinearLayout body=body();body.addView(topBar("작업함","중단돼도 이어지는 업무"),AgentUi.matchWrap());
        LinearLayout stats=new LinearLayout(this);stats.setOrientation(LinearLayout.HORIZONTAL);stats.setGravity(Gravity.CENTER);
        stats.addView(stat("개입 필요",graph.attention().size(),AgentUi.TERRA_PALE),weight());stats.addView(stat("진행 중",activeWithoutAttention(),AgentUi.SAGE_PALE),weight());stats.addView(stat("완료",graph.completed(),AgentUi.SURFACE_ALT),weight());body.addView(stats,AgentUi.spaced(this,20,4));
        List<AgentOsCore.Task> tasks=graph.all();
        if(tasks.isEmpty())body.addView(empty("아직 맡긴 업무가 없습니다","홈에서 목표를 말하거나 다른 앱의 내용을 Life Agent로 공유해보세요.","업무 맡기기",v->showTab(HOME)),AgentUi.spaced(this,18,0));
        else{body.addView(section("모든 작업",tasks.size()+"건"),AgentUi.spaced(this,22,10));for(AgentOsCore.Task task:tasks)body.addView(taskCard(task),AgentUi.spaced(this,0,10));}
        scroll.addView(body);return scroll;
    }

    private View taskCard(AgentOsCore.Task task) {
        LinearLayout content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);
        LinearLayout top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);top.setGravity(Gravity.CENTER_VERTICAL);
        top.addView(AgentUi.pill(this,statusLabel(task.status),statusBg(task.status),statusFg(task.status)),AgentUi.wrapWrap());
        TextView time=AgentUi.text(this,time(task.updatedAt),11,false,AgentUi.INK_SOFT);time.setGravity(Gravity.END|Gravity.CENTER_VERTICAL);top.addView(time,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));content.addView(top,AgentUi.matchWrap());
        TextView title=AgentUi.text(this,task.goal,16,true,AgentUi.INK);title.setMaxLines(2);title.setPadding(0,dp(10),0,dp(5));content.addView(title,AgentUi.matchWrap());
        content.addView(AgentUi.text(this,task.skillTitle+" · "+executorLabel(task.primary),12,false,AgentUi.INK_SOFT),AgentUi.matchWrap());
        TextView next=AgentUi.text(this,"다음 · "+task.nextAction,13,true,task.attention()?AgentUi.TERRA:AgentUi.SAGE_DARK);next.setPadding(0,dp(9),0,0);content.addView(next,AgentUi.matchWrap());
        LinearLayout card=AgentUi.card(this,content,task.attention()?AgentUi.TERRA_PALE:AgentUi.SURFACE);card.setClickable(true);card.setOnClickListener(v->taskDetail(task));return card;
    }

    private View automationsScreen() {
        ScrollView scroll=new ScrollView(this);LinearLayout body=body();body.addView(topBar("자동화","스킬과 Trigger → Action"),AgentUi.matchWrap());
        LinearLayout intro=new LinearLayout(this);intro.setOrientation(LinearLayout.VERTICAL);intro.addView(AgentUi.text(this,"반복 업무는 모델 없이",20,true,AgentUi.INK),AgentUi.matchWrap());
        TextView desc=AgentUi.text(this,"정확한 트리거, 조건, 실행 스킬, 성공 검증을 하나의 규칙으로 저장합니다. 화면이 바뀌거나 실패하면 자동 실행을 멈추고 상위 실행기로 승격합니다.",14,false,AgentUi.INK_SOFT);desc.setLineSpacing(0,1.25f);desc.setPadding(0,dp(7),0,0);intro.addView(desc,AgentUi.matchWrap());intro.addView(AgentUi.primary(this,"새 자동화 만들기",v->recipeDialog()),AgentUi.spaced(this,12,0));
        body.addView(AgentUi.card(this,intro,AgentUi.SAGE_PALE),AgentUi.spaced(this,20,0));
        List<AgentOsCore.Recipe> all=recipes.all();body.addView(section("내 자동화",all.isEmpty()?"아직 없음":all.size()+"개"),AgentUi.spaced(this,22,10));
        if(all.isEmpty())body.addView(empty("첫 규칙을 만들어보세요","예: ‘추가서류가 필요합니다’ 알림이 오면 보험 청구 스킬로 이어가기","규칙 만들기",v->recipeDialog()),AgentUi.spaced(this,0,10));
        else for(AgentOsCore.Recipe recipe:all)body.addView(recipeCard(recipe),AgentUi.spaced(this,0,10));
        body.addView(section("설치된 스킬",registry.all().size()+"개"),AgentUi.spaced(this,22,10));String category="";
        for(AgentOsCore.Skill skill:registry.all()){if(!skill.category.equals(category)){TextView c=AgentUi.text(this,skill.category,12,true,AgentUi.INK_SOFT);c.setPadding(dp(4),dp(8),0,dp(7));body.addView(c,AgentUi.matchWrap());category=skill.category;}body.addView(installedSkill(skill),AgentUi.spaced(this,0,10));}
        scroll.addView(body);return scroll;
    }

    private View recipeCard(AgentOsCore.Recipe recipe) {
        LinearLayout content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);LinearLayout head=new LinearLayout(this);head.setOrientation(LinearLayout.HORIZONTAL);head.setGravity(Gravity.CENTER_VERTICAL);
        head.addView(AgentUi.text(this,recipe.name,16,true,AgentUi.INK),new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));Switch toggle=new Switch(this);toggle.setChecked(recipe.enabled);toggle.setOnCheckedChangeListener((b,c)->recipes.enabled(recipe.id,c));head.addView(toggle,AgentUi.wrapWrap());content.addView(head,AgentUi.matchWrap());
        AgentOsCore.Skill action=registry.find(recipe.skillId);String actionName=action==null?recipe.skillId:action.title;TextView flow=AgentUi.text(this,triggerLabel(recipe.type)+" · ‘"+recipe.triggerValue+"’\n→ "+actionName,13,false,AgentUi.INK_SOFT);flow.setLineSpacing(0,1.25f);flow.setPadding(0,dp(7),0,0);content.addView(flow,AgentUi.matchWrap());
        LinearLayout chips=new LinearLayout(this);chips.setOrientation(LinearLayout.HORIZONTAL);chips.setPadding(0,dp(10),0,0);chips.addView(AgentUi.pill(this,recipe.modelFree()?"MODEL_FREE":"확인 후 실행",recipe.modelFree()?AgentUi.SAGE_PALE:AgentUi.WARNING_PALE,recipe.modelFree()?AgentUi.SAGE_DARK:AgentUi.WARNING),AgentUi.wrapWrap());chips.addView(AgentUi.text(this,"  검증 "+recipe.verifiedRuns+"회",11,false,AgentUi.INK_SOFT),AgentUi.wrapWrap());content.addView(chips,AgentUi.matchWrap());
        LinearLayout card=AgentUi.card(this,content,AgentUi.SURFACE);card.setOnLongClickListener(v->{new AlertDialog.Builder(this).setTitle("자동화 삭제").setMessage(recipe.name+" 규칙을 삭제할까요?").setNegativeButton("취소",null).setPositiveButton("삭제",(d,w)->{recipes.delete(recipe.id);showTab(AUTOMATIONS);}).show();return true;});return card;
    }

    private View installedSkill(AgentOsCore.Skill skill) {
        LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);TextView glyph=AgentUi.text(this,skill.glyph,20,true,AgentUi.SAGE_DARK);glyph.setGravity(Gravity.CENTER);glyph.setBackground(AgentUi.round(AgentUi.SAGE_PALE,15,0,0));LinearLayout.LayoutParams gp=new LinearLayout.LayoutParams(dp(44),dp(44));gp.rightMargin=dp(12);row.addView(glyph,gp);
        LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.addView(AgentUi.text(this,skill.title,15,true,AgentUi.INK),AgentUi.matchWrap());TextView sub=AgentUi.text(this,skill.subtitle,12,false,AgentUi.INK_SOFT);sub.setMaxLines(2);copy.addView(sub,AgentUi.matchWrap());row.addView(copy,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));row.addView(AgentUi.pill(this,riskLabel(skill.risk),riskBg(skill.risk),riskFg(skill.risk)),AgentUi.wrapWrap());
        LinearLayout card=AgentUi.card(this,row,AgentUi.SURFACE);card.setClickable(true);card.setOnClickListener(v->skillDetail(skill));return card;
    }

    private View meScreen() {
        ScrollView scroll=new ScrollView(this);LinearLayout body=body();body.addView(topBar("내 정보","금고·권한·실행기"),AgentUi.matchWrap());
        LinearLayout vault=new LinearLayout(this);vault.setOrientation(LinearLayout.VERTICAL);vault.addView(AgentUi.text(this,"개인정보 금고",19,true,AgentUi.INK),AgentUi.matchWrap());TextView vt=AgentUi.text(this,"이름·연락처·주소·선호는 Android Keystore로 보호합니다. 비밀번호, OTP, PIN, CVV, 복구코드는 저장하지 않습니다.",14,false,AgentUi.INK_SOFT);vt.setLineSpacing(0,1.25f);vt.setPadding(0,dp(6),0,0);vault.addView(vt,AgentUi.matchWrap());vault.addView(AgentUi.primary(this,"금고 열기",v->openSkill("profile.vault")),AgentUi.spaced(this,12,0));body.addView(AgentUi.card(this,vault,AgentUi.SAGE_PALE),AgentUi.spaced(this,20,0));
        body.addView(section("OS 진입점","앱을 찾지 않고 호출"),AgentUi.spaced(this,22,10));body.addView(permission("알림 문맥",notificationEnabled(),"보험·예약·방송 후속 이벤트",v->notificationSettings()),AgentUi.spaced(this,0,10));body.addView(permission("자동입력",autofillEnabled(),"허용된 금고 필드만 입력",v->autofillSettings()),AgentUi.spaced(this,0,10));body.addView(permission("공유·선택 텍스트",true,"공유 메뉴와 텍스트 선택 메뉴에서 호출",null),AgentUi.spaced(this,0,10));body.addView(permission("빠른 설정 타일",false,"상단 편집에서 Life Agent 추가",v->tileHelp()),AgentUi.spaced(this,0,10));
        body.addView(section("실행기","필요한 순간만 연결"),AgentUi.spaced(this,22,10));body.addView(action("AI 구독·PC Companion","공식 클라이언트와 서명된 기기 연결","연결 관리",v->openSkill("executor.connections")),AgentUi.spaced(this,0,10));body.addView(action("앱 권한·배터리","백그라운드 자동화가 중단될 때 확인","설정 열기",v->appSettings()),AgentUi.spaced(this,0,10));
        body.addView(section("Agent OS 코어","실제로 연결된 5개 층"),AgentUi.spaced(this,22,10));LinearLayout status=new LinearLayout(this);status.setOrientation(LinearLayout.VERTICAL);status.addView(core("Context Engine","공유·선택 텍스트·알림 문맥"));status.addView(core("Skill Registry",registry.all().size()+"개 스킬"));status.addView(core("Policy Kernel","자동·확인·생체인증·차단"));status.addView(core("Executor Router","Intent·OCR·자동입력·CU·Companion"));status.addView(core("Persistent Task Graph",graph.all().size()+"개 작업 기록"));body.addView(AgentUi.card(this,status,AgentUi.SURFACE),AgentUi.spaced(this,0,10));
        TextView note=AgentUi.text(this,"인증은 우회하지 않습니다. 외부 제출, 송금, 계정 변경은 정책 관문을 거치며 실제 성공 증거가 없으면 완료 처리하지 않습니다.",12,false,AgentUi.INK_SOFT);note.setLineSpacing(0,1.25f);note.setPadding(dp(4),dp(18),dp(4),dp(28));body.addView(note,AgentUi.matchWrap());scroll.addView(body);return scroll;
    }

    private void planCommand() {
        if(currentTab!=HOME||commandInput==null)showTab(HOME);String command=commandInput.getText().toString().trim();commandDraft=command;if(command.isEmpty()){commandInput.setError("맡길 일을 한 문장으로 적어주세요.");commandInput.requestFocus();return;}hideKeyboard();AgentOsCore.Plan plan=planner.plan(command,currentContext);planDialog(plan);
    }

    private void planDialog(AgentOsCore.Plan plan) {
        LinearLayout content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(dp(4),0,dp(4),0);LinearLayout head=new LinearLayout(this);head.setOrientation(LinearLayout.HORIZONTAL);head.setGravity(Gravity.CENTER_VERTICAL);TextView glyph=AgentUi.text(this,plan.skill.glyph,22,true,AgentUi.SAGE_DARK);glyph.setGravity(Gravity.CENTER);glyph.setBackground(AgentUi.round(AgentUi.SAGE_PALE,16,0,0));LinearLayout.LayoutParams gp=new LinearLayout.LayoutParams(dp(48),dp(48));gp.rightMargin=dp(12);head.addView(glyph,gp);LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.addView(AgentUi.text(this,plan.skill.title,18,true,AgentUi.INK),AgentUi.matchWrap());copy.addView(AgentUi.text(this,plan.intent.explanation,13,false,AgentUi.INK_SOFT),AgentUi.matchWrap());head.addView(copy,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));content.addView(head,AgentUi.matchWrap());
        LinearLayout badges=new LinearLayout(this);badges.setOrientation(LinearLayout.HORIZONTAL);badges.setPadding(0,dp(14),0,dp(10));badges.addView(AgentUi.pill(this,gateLabel(plan.policy.gate),gateBg(plan.policy.gate),gateFg(plan.policy.gate)),AgentUi.wrapWrap());LinearLayout.LayoutParams rp=AgentUi.wrapWrap();rp.leftMargin=dp(7);badges.addView(AgentUi.pill(this,plan.route.label,AgentUi.SURFACE_ALT,AgentUi.INK_SOFT),rp);content.addView(badges,AgentUi.matchWrap());
        TextView reason=AgentUi.text(this,plan.policy.reason+"\n"+plan.route.rationale,13,false,AgentUi.INK_SOFT);reason.setLineSpacing(0,1.25f);reason.setPadding(dp(12),dp(11),dp(12),dp(11));reason.setBackground(AgentUi.round(AgentUi.CANVAS,15,AgentUi.LINE,1));content.addView(reason,AgentUi.matchWrap());TextView st=AgentUi.text(this,"실행 계획",13,true,AgentUi.INK);st.setPadding(0,dp(15),0,dp(5));content.addView(st,AgentUi.matchWrap());for(int i=0;i<plan.task.steps.size();i++){TextView v=AgentUi.text(this,(i+1)+". "+plan.task.steps.get(i).title,13,false,AgentUi.INK);v.setPadding(dp(4),dp(4),0,dp(4));content.addView(v,AgentUi.matchWrap());}
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("이렇게 처리할까요?").setView(content).setNegativeButton("수정",(d,w)->graph.cancel(plan.task.id)).setPositiveButton(startLabel(plan.policy.gate),null).create();dialog.setOnCancelListener(d->graph.cancel(plan.task.id));dialog.setOnShowListener(d->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{boolean started=AgentOsCore.start(this,plan);dialog.dismiss();if(started)Toast.makeText(this,plan.skill.title+" 작업을 시작했습니다.",Toast.LENGTH_SHORT).show();else{Toast.makeText(this,"실행기를 열지 못해 작업함에 문제로 남겼습니다.",Toast.LENGTH_LONG).show();showTab(TASKS);}}));dialog.show();
    }

    private void taskDetail(AgentOsCore.Task task) {
        LinearLayout content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);TextView goal=AgentUi.text(this,task.goal,16,true,AgentUi.INK);goal.setPadding(0,0,0,dp(8));content.addView(goal,AgentUi.matchWrap());content.addView(AgentUi.pill(this,statusLabel(task.status),statusBg(task.status),statusFg(task.status)),AgentUi.wrapWrap());TextView meta=AgentUi.text(this,"\n스킬 · "+task.skillTitle+"\n실행기 · "+executorLabel(task.primary)+"\n검증 · "+task.verification+"\n다음 · "+task.nextAction,13,false,AgentUi.INK_SOFT);meta.setLineSpacing(0,1.25f);content.addView(meta,AgentUi.matchWrap());TextView h=AgentUi.text(this,"단계",13,true,AgentUi.INK);h.setPadding(0,dp(14),0,dp(4));content.addView(h,AgentUi.matchWrap());for(AgentOsCore.Step step:task.steps){String mark=step.status==AgentOsCore.StepStatus.DONE?"✓":step.status==AgentOsCore.StepStatus.FAILED?"!":step.status==AgentOsCore.StepStatus.ACTIVE?"●":"○";TextView v=AgentUi.text(this,mark+"  "+step.title,13,false,step.status==AgentOsCore.StepStatus.FAILED?AgentUi.DANGER:AgentUi.INK);v.setPadding(0,dp(4),0,dp(4));content.addView(v,AgentUi.matchWrap());}
        boolean resumable=task.status!=AgentOsCore.TaskStatus.COMPLETED&&task.status!=AgentOsCore.TaskStatus.CANCELLED;AlertDialog.Builder b=new AlertDialog.Builder(this).setTitle("작업 상세").setView(content).setNegativeButton("닫기",null);if(resumable){b.setNeutralButton("취소",(d,w)->{graph.cancel(task.id);showTab(TASKS);});b.setPositiveButton("계속",(d,w)->{if(!AgentOsCore.resume(this,task))Toast.makeText(this,"스킬을 다시 열지 못했습니다.",Toast.LENGTH_LONG).show();});}b.show();
    }

    private void recipeDialog() {
        LinearLayout form=new LinearLayout(this);form.setOrientation(LinearLayout.VERTICAL);EditText name=field("규칙 이름","보험 추가서류 후속 처리");form.addView(name);TextView tl=AgentUi.text(this,"트리거",12,true,AgentUi.INK_SOFT);tl.setPadding(0,dp(10),0,dp(4));form.addView(tl);Spinner trigger=new Spinner(this);List<String> triggerNames=Arrays.asList("알림 문구 일치","콘텐츠 공유","선택 텍스트","일정 확인","수동 바로가기");trigger.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,triggerNames));form.addView(trigger);EditText value=field("일치할 값","예: 추가서류가 필요합니다");form.addView(value);EditText condition=field("추가 조건 (선택)","예: 삼성화재 또는 모니모 알림만");form.addView(condition);TextView sl=AgentUi.text(this,"실행 스킬",12,true,AgentUi.INK_SOFT);sl.setPadding(0,dp(10),0,dp(4));form.addView(sl);Spinner skillSpinner=new Spinner(this);List<AgentOsCore.Skill> skills=registry.all();List<String> names=new ArrayList<>();for(AgentOsCore.Skill s:skills)names.add(s.title);skillSpinner.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,names));form.addView(skillSpinner);CheckBox auto=new CheckBox(this);auto.setText("정확히 일치하면 확인 없이 실행");auto.setTextSize(14);auto.setPadding(0,dp(8),0,0);form.addView(auto);TextView note=AgentUi.text(this,"저위험 스킬만 자동 실행합니다. 인증·송금·외부 제출은 항상 정책 관문을 거칩니다.",11,false,AgentUi.INK_SOFT);form.addView(note);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Trigger → Action").setView(form).setNegativeButton("취소",null).setPositiveButton("저장",null).create();dialog.setOnShowListener(d->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{int index=skillSpinner.getSelectedItemPosition();if(index<0||index>=skills.size())return;AgentOsCore.Skill selected=skills.get(index);boolean requested=auto.isChecked();try{recipes.create(name.getText().toString(),triggerAt(trigger.getSelectedItemPosition()),value.getText().toString(),condition.getText().toString(),selected.id,requested);dialog.dismiss();if(requested&&selected.risk!=AgentOsCore.Risk.LOW)Toast.makeText(this,"민감 스킬이라 확인 후 실행으로 저장했습니다.",Toast.LENGTH_LONG).show();showTab(AUTOMATIONS);}catch(IllegalArgumentException e){Toast.makeText(this,e.getMessage(),Toast.LENGTH_LONG).show();}}));dialog.show();
    }

    private View topBar(String title,String subtitle){LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.addView(AgentUi.text(this,title,23,true,AgentUi.INK),AgentUi.matchWrap());TextView sub=AgentUi.text(this,subtitle,12,false,AgentUi.INK_SOFT);sub.setPadding(0,dp(2),0,0);copy.addView(sub,AgentUi.matchWrap());row.addView(copy,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));row.addView(AgentUi.pill(this,"OS α2",AgentUi.SAGE_PALE,AgentUi.SAGE_DARK),AgentUi.wrapWrap());return row;}
    private View section(String title,String trailing){LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);row.addView(AgentUi.text(this,title,18,true,AgentUi.INK),new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));TextView t=AgentUi.text(this,trailing,12,false,AgentUi.INK_SOFT);t.setGravity(Gravity.END|Gravity.CENTER_VERTICAL);row.addView(t,AgentUi.wrapWrap());return row;}
    private LinearLayout body(){LinearLayout b=new LinearLayout(this);b.setOrientation(LinearLayout.VERTICAL);b.setPadding(dp(18),dp(20),dp(18),dp(28));return b;}
    private LinearLayout.LayoutParams weight(){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f);p.leftMargin=dp(3);p.rightMargin=dp(3);return p;}
    private View stat(String label,int count,int color){LinearLayout box=new LinearLayout(this);box.setOrientation(LinearLayout.VERTICAL);box.setGravity(Gravity.CENTER);box.setPadding(dp(8),dp(14),dp(8),dp(14));box.setBackground(AgentUi.round(color,18,AgentUi.LINE,1));TextView n=AgentUi.text(this,Integer.toString(count),22,true,AgentUi.INK);n.setGravity(Gravity.CENTER);TextView l=AgentUi.text(this,label,12,false,AgentUi.INK_SOFT);l.setGravity(Gravity.CENTER);box.addView(n,AgentUi.matchWrap());box.addView(l,AgentUi.matchWrap());return box;}
    private View empty(String title,String detail,String action,View.OnClickListener listener){LinearLayout content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);content.setGravity(Gravity.CENTER_HORIZONTAL);TextView t=AgentUi.text(this,title,17,true,AgentUi.INK);t.setGravity(Gravity.CENTER);content.addView(t,AgentUi.matchWrap());TextView d=AgentUi.text(this,detail,13,false,AgentUi.INK_SOFT);d.setGravity(Gravity.CENTER);d.setLineSpacing(0,1.25f);d.setPadding(0,dp(7),0,0);content.addView(d,AgentUi.matchWrap());content.addView(AgentUi.secondary(this,action,listener),AgentUi.spaced(this,12,0));return AgentUi.card(this,content,AgentUi.SURFACE);}
    private View permission(String title,boolean enabled,String detail,View.OnClickListener listener){LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.addView(AgentUi.text(this,title,15,true,AgentUi.INK),AgentUi.matchWrap());copy.addView(AgentUi.text(this,detail,12,false,AgentUi.INK_SOFT),AgentUi.matchWrap());row.addView(copy,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));row.addView(AgentUi.pill(this,enabled?"켜짐":"설정",enabled?AgentUi.SAGE_PALE:AgentUi.WARNING_PALE,enabled?AgentUi.SAGE_DARK:AgentUi.WARNING),AgentUi.wrapWrap());LinearLayout card=AgentUi.card(this,row,AgentUi.SURFACE);if(listener!=null){card.setClickable(true);card.setOnClickListener(listener);}return card;}
    private View action(String title,String detail,String action,View.OnClickListener listener){LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.addView(AgentUi.text(this,title,15,true,AgentUi.INK),AgentUi.matchWrap());copy.addView(AgentUi.text(this,detail,12,false,AgentUi.INK_SOFT),AgentUi.matchWrap());row.addView(copy,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));row.addView(AgentUi.secondary(this,action,listener),AgentUi.wrapWrap());return AgentUi.card(this,row,AgentUi.SURFACE);}
    private View core(String title,String detail){LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(0,dp(6),0,dp(6));row.addView(AgentUi.text(this,"●",14,true,AgentUi.SAGE_DARK),AgentUi.wrapWrap());LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.setPadding(dp(10),0,0,0);copy.addView(AgentUi.text(this,title,14,true,AgentUi.INK),AgentUi.matchWrap());copy.addView(AgentUi.text(this,detail,12,false,AgentUi.INK_SOFT),AgentUi.matchWrap());row.addView(copy,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));return row;}

    private void seed(AgentOsCore.Skill skill){commandDraft=skill.examples.isEmpty()?skill.title+" 처리해줘":skill.examples.get(0);showTab(HOME);commandInput.requestFocus();}
    private void skillDetail(AgentOsCore.Skill skill){StringBuilder caps=new StringBuilder();for(String c:skill.capabilities)caps.append("• ").append(c).append('\n');new AlertDialog.Builder(this).setTitle(skill.glyph+"  "+skill.title).setMessage(skill.subtitle+"\n\n위험 정책 · "+riskLabel(skill.risk)+"\n성공 검증 · "+skill.verification+"\n\nCapabilities\n"+caps).setNegativeButton("닫기",null).setPositiveButton("이 스킬로 맡기기",(d,w)->seed(skill)).show();}
    private void openSkill(String id){AgentOsCore.Skill skill=registry.find(id);if(skill==null)return;String command=skill.examples.isEmpty()?skill.title:skill.examples.get(0);AgentOsCore.Plan plan=planner.plan(command,currentContext);if(!AgentOsCore.start(this,plan))Toast.makeText(this,"스킬을 열지 못했습니다.",Toast.LENGTH_LONG).show();}
    private void startVoice(){Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM).putExtra(RecognizerIntent.EXTRA_LANGUAGE,"ko-KR").putExtra(RecognizerIntent.EXTRA_PROMPT,"무엇을 처리할까요?");try{startActivityForResult(i,VOICE_REQUEST);}catch(ActivityNotFoundException e){Toast.makeText(this,"이 기기에는 음성 인식기가 없습니다.",Toast.LENGTH_LONG).show();}}
    private void hideKeyboard(){View focus=getCurrentFocus();if(focus==null)return;InputMethodManager imm=(InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);if(imm!=null)imm.hideSoftInputFromWindow(focus.getWindowToken(),0);}
    private EditText field(String label,String hint){EditText e=new EditText(this);e.setHint(label+" · "+hint);e.setTextSize(15);e.setSingleLine(true);e.setPadding(dp(10),dp(9),dp(10),dp(9));e.setBackground(AgentUi.round(AgentUi.CANVAS,13,AgentUi.LINE,1));e.setLayoutParams(AgentUi.spaced(this,8,0));return e;}
    private AgentOsCore.TriggerType triggerAt(int i){if(i==1)return AgentOsCore.TriggerType.CONTENT_SHARED;if(i==2)return AgentOsCore.TriggerType.TEXT_SELECTED;if(i==3)return AgentOsCore.TriggerType.SCHEDULE_TICK;if(i==4)return AgentOsCore.TriggerType.MANUAL_SHORTCUT;return AgentOsCore.TriggerType.NOTIFICATION_MATCH;}
    private int activeWithoutAttention(){int n=0;for(AgentOsCore.Task t:graph.active())if(!t.attention())n++;return n;}
    private int dp(int value){return AgentUi.dp(this,value);}
    private String time(long value){return new SimpleDateFormat("M월 d일 HH:mm",Locale.KOREA).format(new Date(value));}

    private boolean notificationEnabled(){try{String enabled=Settings.Secure.getString(getContentResolver(),"enabled_notification_listeners");if(enabled==null)return false;ComponentName expected=new ComponentName(this,UnifiedNotificationListener.class);for(String value:enabled.split(":")){ComponentName item=ComponentName.unflattenFromString(value);if(expected.equals(item))return true;}}catch(RuntimeException ignored){}return false;}
    private boolean autofillEnabled(){try{String service=Settings.Secure.getString(getContentResolver(),"autofill_service");return service!=null&&service.contains(getPackageName());}catch(RuntimeException ignored){return false;}}
    private void notificationSettings(){try{startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));}catch(RuntimeException e){appSettings();}}
    private void autofillSettings(){try{Intent i=new Intent("android.settings.REQUEST_SET_AUTOFILL_SERVICE");i.setData(Uri.parse("package:"+getPackageName()));startActivity(i);}catch(RuntimeException e){try{startActivity(new Intent(Settings.ACTION_SETTINGS));}catch(RuntimeException ignored){appSettings();}}}
    private void appSettings(){try{startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName())));}catch(RuntimeException e){Toast.makeText(this,"앱 설정을 열 수 없습니다.",Toast.LENGTH_LONG).show();}}
    private void tileHelp(){new AlertDialog.Builder(this).setTitle("빠른 설정에 추가").setMessage("화면 상단을 두 번 내려 빠른 설정 편집을 열고, ‘Life Agent’를 활성 타일로 끌어오세요. 이후 어느 앱에서든 한 번 눌러 명령면을 열 수 있습니다.").setPositiveButton("확인",null).show();}

    private static String statusLabel(AgentOsCore.TaskStatus s){switch(s){case READY:return"준비됨";case RUNNING:return"진행 중";case NEEDS_CONFIRMATION:return"확인 필요";case NEEDS_AUTH:return"인증 필요";case VERIFYING:return"결과 확인";case COMPLETED:return"완료";case PROBLEM:return"문제";case CANCELLED:return"취소";default:return"초안";}}
    private static int statusBg(AgentOsCore.TaskStatus s){switch(s){case NEEDS_CONFIRMATION:case NEEDS_AUTH:return AgentUi.WARNING_PALE;case PROBLEM:return AgentUi.DANGER_PALE;case COMPLETED:case READY:case RUNNING:case VERIFYING:return AgentUi.SAGE_PALE;default:return AgentUi.SURFACE_ALT;}}
    private static int statusFg(AgentOsCore.TaskStatus s){switch(s){case NEEDS_CONFIRMATION:case NEEDS_AUTH:return AgentUi.WARNING;case PROBLEM:return AgentUi.DANGER;case COMPLETED:case READY:case RUNNING:case VERIFYING:return AgentUi.SAGE_DARK;default:return AgentUi.INK_SOFT;}}
    private static String executorLabel(String e){try{switch(AgentOsCore.Executor.valueOf(e)){case MODEL_FREE:return"모델 없이 자동화";case ANDROID_INTENT:return"Android 기본 실행";case LOCAL_OCR:return"온디바이스 문서 읽기";case AUTOFILL:return"보안 자동입력";case SUBSCRIPTION:return"AI 구독 실행기";case MOBILE_CU:return"모바일 Computer Use";case DESKTOP:return"PC·Mac Companion";default:return"사용자 관문";}}catch(Exception ignored){return e;}}
    private static String riskLabel(AgentOsCore.Risk r){switch(r){case LOW:return"자동 가능";case BIOMETRIC:return"생체인증";case MANUAL_AUTH:return"직접 인증";default:return"확인 필요";}}
    private static int riskBg(AgentOsCore.Risk r){return r==AgentOsCore.Risk.LOW?AgentUi.SAGE_PALE:(r==AgentOsCore.Risk.CONFIRM?AgentUi.WARNING_PALE:AgentUi.DANGER_PALE);}
    private static int riskFg(AgentOsCore.Risk r){return r==AgentOsCore.Risk.LOW?AgentUi.SAGE_DARK:(r==AgentOsCore.Risk.CONFIRM?AgentUi.WARNING:AgentUi.DANGER);}
    private static String gateLabel(AgentOsCore.Gate g){switch(g){case AUTO:return"자동 준비";case CONFIRM:return"실행 전 확인";case BIOMETRIC:return"생체인증";case MANUAL_AUTH:return"직접 인증";default:return"차단";}}
    private static int gateBg(AgentOsCore.Gate g){return g==AgentOsCore.Gate.AUTO?AgentUi.SAGE_PALE:(g==AgentOsCore.Gate.CONFIRM?AgentUi.WARNING_PALE:AgentUi.DANGER_PALE);}
    private static int gateFg(AgentOsCore.Gate g){return g==AgentOsCore.Gate.AUTO?AgentUi.SAGE_DARK:(g==AgentOsCore.Gate.CONFIRM?AgentUi.WARNING:AgentUi.DANGER);}
    private static String startLabel(AgentOsCore.Gate g){switch(g){case BIOMETRIC:return"인증 단계로";case MANUAL_AUTH:return"직접 인증하고 계속";case CONFIRM:return"확인하고 시작";case BLOCK:return"작업함에 남기기";default:return"바로 시작";}}
    private static String triggerLabel(AgentOsCore.TriggerType t){switch(t){case CONTENT_SHARED:return"콘텐츠 공유";case TEXT_SELECTED:return"선택 텍스트";case SCHEDULE_TICK:return"일정 확인";case MANUAL_SHORTCUT:return"수동 바로가기";default:return"알림 문구 일치";}}
}
