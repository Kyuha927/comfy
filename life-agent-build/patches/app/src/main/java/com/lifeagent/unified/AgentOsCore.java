package com.lifeagent.unified;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.service.notification.StatusBarNotification;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * Life Agent OS core. Features are manifests beneath this kernel, not product navigation.
 * The pipeline is Context -> Skill Registry -> Policy -> Executor -> Persistent Task Graph.
 */
final class AgentOsCore {
    static final String EXTRA_SOURCE = "lifeagent.os.source";
    static final String EXTRA_COMMAND = "lifeagent.os.command";
    static final String EXTRA_TASK_ID = "lifeagent.os.task_id";
    static final String EXTRA_SKILL_ID = "lifeagent.os.skill_id";
    static final String EXTRA_CONTEXT = "lifeagent.os.context";
    static final String EXTRA_TAB = "lifeagent.os.tab";

    private AgentOsCore() {}

    enum Source { APP, SHARE, SELECTED_TEXT, NOTIFICATION, QUICK_TILE, SHORTCUT, DEEP_LINK }
    enum Risk { LOW, CONFIRM, BIOMETRIC, MANUAL_AUTH }
    enum Gate { AUTO, CONFIRM, BIOMETRIC, MANUAL_AUTH, BLOCK }
    enum Executor { MODEL_FREE, ANDROID_INTENT, LOCAL_OCR, AUTOFILL, SUBSCRIPTION, MOBILE_CU, DESKTOP, HUMAN }
    enum TaskStatus { DRAFT, READY, RUNNING, NEEDS_CONFIRMATION, NEEDS_AUTH, VERIFYING, COMPLETED, PROBLEM, CANCELLED }
    enum StepStatus { PENDING, ACTIVE, WAITING_USER, DONE, FAILED }
    enum TriggerType { NOTIFICATION_MATCH, CONTENT_SHARED, TEXT_SELECTED, SCHEDULE_TICK, MANUAL_SHORTCUT }

    static final class ContextSnapshot {
        final Source source;
        final String trigger;
        final String commandHint;
        final String safeSummary;
        final String mimeType;
        final Uri sharedUri;
        final boolean sensitive;

        ContextSnapshot(Source source, String trigger, String commandHint, String safeSummary,
                        String mimeType, Uri sharedUri, boolean sensitive) {
            this.source = source;
            this.trigger = trigger;
            this.commandHint = commandHint == null ? "" : commandHint;
            this.safeSummary = safeSummary == null ? "" : safeSummary;
            this.mimeType = mimeType == null ? "" : mimeType;
            this.sharedUri = sharedUri;
            this.sensitive = sensitive;
        }

        static ContextSnapshot empty() {
            return new ContextSnapshot(Source.APP, "app.opened", "", "", "", null, false);
        }

        String label() {
            switch (source) {
                case SHARE: return "공유된 항목";
                case SELECTED_TEXT: return "선택한 텍스트";
                case NOTIFICATION: return "알림 문맥";
                case QUICK_TILE: return "빠른 설정";
                case SHORTCUT: return "홈 바로가기";
                case DEEP_LINK: return "외부 호출";
                default: return "Life Agent";
            }
        }
    }

    static final class ContextEngine {
        private static final Pattern OTP = Pattern.compile("(?i)(인증번호|인증코드|otp|verification code).{0,16}\\b\\d{4,8}\\b");
        private static final Pattern CARD = Pattern.compile("\\b(?:\\d[ -]*?){13,19}\\b");

        static ContextSnapshot capture(Context context, Intent intent) {
            if (intent == null) return ContextSnapshot.empty();
            String action = safe(intent.getAction());
            String mime = safe(intent.getType());
            String text = safe(intent.getStringExtra(EXTRA_COMMAND));
            Uri uri = intent.getData();
            Source source = parseSource(intent.getStringExtra(EXTRA_SOURCE));
            String trigger = "app.opened";

            if (Intent.ACTION_SEND.equals(action)) {
                source = Source.SHARE;
                trigger = "content.shared";
                String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
                if (sharedText != null) text = sharedText;
                uri = streamUri(intent);
            } else if (Intent.ACTION_PROCESS_TEXT.equals(action)) {
                source = Source.SELECTED_TEXT;
                trigger = "text.selected";
                CharSequence selected = intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT);
                if (selected != null) text = selected.toString();
            } else if (Intent.ACTION_VIEW.equals(action)) {
                source = Source.DEEP_LINK;
                trigger = "deep_link.opened";
            } else if (source == Source.QUICK_TILE) {
                trigger = "quick_tile.tapped";
            } else if (source == Source.SHORTCUT) {
                trigger = "shortcut.opened";
            } else if (source == Source.NOTIFICATION) {
                trigger = "notification.opened";
            }

            boolean sensitive = looksSensitive(text);
            String summary;
            if (sensitive) summary = "민감정보가 포함된 항목입니다. 원문은 저장하지 않습니다.";
            else if (!text.trim().isEmpty()) summary = shorten(redact(text), 150);
            else if (uri != null) summary = mime.isEmpty() ? "공유된 파일 1개" : mime + " 파일 1개";
            else summary = "";
            Events.remember(context, source.name(), trigger, summary, mime);
            return new ContextSnapshot(source, trigger, text, summary, mime, uri, sensitive);
        }

        static String recommendedPrompt(ContextSnapshot c) {
            if (c == null) return "";
            if (!c.commandHint.trim().isEmpty()) return c.commandHint.trim();
            String mime = c.mimeType.toLowerCase(Locale.ROOT);
            if (mime.startsWith("image/") || "application/pdf".equals(mime)) {
                return "이 문서를 확인해서 필요한 일을 처리해줘";
            }
            if (c.source == Source.SELECTED_TEXT) return "선택한 내용을 바탕으로 필요한 일을 처리해줘";
            if (c.source == Source.NOTIFICATION) return "이 알림의 후속 작업을 처리해줘";
            return "";
        }

        static boolean looksSensitive(String text) {
            if (text == null || text.isEmpty()) return false;
            return OTP.matcher(text).find() || CARD.matcher(text).find();
        }

        static String redact(String text) {
            if (text == null) return "";
            return CARD.matcher(OTP.matcher(text).replaceAll("[인증정보 숨김]"))
                    .replaceAll("[결제정보 숨김]");
        }

        private static Uri streamUri(Intent intent) {
            if (Build.VERSION.SDK_INT >= 33) return intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri.class);
            @SuppressWarnings("deprecation") Uri value = intent.getParcelableExtra(Intent.EXTRA_STREAM);
            return value;
        }

        private static Source parseSource(String value) {
            if (value == null) return Source.APP;
            try { return Source.valueOf(value.toUpperCase(Locale.ROOT)); }
            catch (IllegalArgumentException ignored) { return Source.APP; }
        }
    }

    static final class Skill {
        final String id;
        final String title;
        final String subtitle;
        final String category;
        final String glyph;
        final String activity;
        final Risk risk;
        final String verification;
        final Set<String> capabilities;
        final Set<String> triggers;
        final List<String> examples;
        final int priority;

        Skill(String id, String title, String subtitle, String category, String glyph,
              String activity, Risk risk, String verification, String[] capabilities,
              String[] triggers, String[] examples, int priority) {
            this.id = id;
            this.title = title;
            this.subtitle = subtitle;
            this.category = category;
            this.glyph = glyph;
            this.activity = activity;
            this.risk = risk;
            this.verification = verification;
            this.capabilities = set(capabilities);
            this.triggers = set(triggers);
            List<String> exampleList = new ArrayList<>();
            Collections.addAll(exampleList, examples);
            this.examples = Collections.unmodifiableList(exampleList);
            this.priority = priority;
        }

        int score(Set<String> wanted, ContextSnapshot context) {
            int score = priority;
            for (String capability : wanted) if (capabilities.contains(capability)) score += 40;
            if (context != null && triggers.contains(context.trigger)) score += 24;
            if (context != null && (context.mimeType.startsWith("image/")
                    || "application/pdf".equals(context.mimeType))
                    && capabilities.contains("document.read")) score += 18;
            return score;
        }

        Intent launch(Context context, String taskId, ContextSnapshot snapshot, String command) {
            if (activity.isEmpty()) return null;
            Intent intent = new Intent();
            intent.setClassName(context.getPackageName(), activity);
            intent.putExtra(EXTRA_TASK_ID, taskId);
            intent.putExtra(EXTRA_SKILL_ID, id);
            intent.putExtra(EXTRA_COMMAND, command);
            if (snapshot != null) {
                intent.putExtra(EXTRA_SOURCE, snapshot.source.name());
                intent.putExtra(EXTRA_CONTEXT, snapshot.safeSummary);
                if (snapshot.sharedUri != null) {
                    intent.setData(snapshot.sharedUri);
                    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                }
            }
            return intent;
        }
    }

    static final class Registry {
        private static volatile Registry instance;
        private final Map<String, Skill> skills = new LinkedHashMap<>();

        private Registry() {
            add(new Skill("reservation.orchestrator", "예약 대행", "웹·앱·전화 중 가장 알맞은 경로로 예약합니다", "생활", "◷",
                    "com.lifeagent.unified.ReservationActivity", Risk.CONFIRM, "reservation_confirmation",
                    a("reservation.plan", "reservation.execute", "phone.call"), a("command.received", "reservation.requested"),
                    a("금요일 오후 정형외과 예약해줘", "전화로 미용실 예약해줘"), 15));
            add(new Skill("insurance.claim.monimo", "보험금 청구", "병원 서류 판독부터 모니모 후속 처리까지 이어갑니다", "건강", "▤",
                    "com.lifeagent.unified.InsuranceActivity", Risk.CONFIRM, "claim_receipt_number",
                    a("insurance.claim", "document.read", "document.ocr", "notification.followup"),
                    a("content.shared", "insurance.notification.received", "document.captured"),
                    a("이 병원 서류 보험 청구해줘", "추가서류 문제 해결해줘"), 18));
            add(new Skill("transfer.secure", "안전 송금", "초안을 만들고 수취인·금액 확인과 생체인증 뒤 실행합니다", "금융", "₩",
                    "com.lifeagent.unified.TransferActivity", Risk.BIOMETRIC, "provider_transaction_receipt",
                    a("money.transfer", "money.transfer.draft"), a("command.received"),
                    a("엄마에게 5만원 보내는 초안 만들어줘"), 12));
            add(new Skill("identity.signup", "회원가입·자동입력", "금고의 허용 필드만 꺼내 반복 입력을 줄입니다", "계정", "＋",
                    "com.lifeagent.unified.SignupActivity", Risk.CONFIRM, "account_creation_receipt",
                    a("identity.signup", "form.autofill"), a("command.received", "text.selected", "content.shared"),
                    a("이 사이트 회원가입해줘", "내 정보로 이 폼 채워줘"), 10));
            add(new Skill("stream.autoopen", "방송 자동 실행", "선택 스트리머의 검증된 알림을 모델 없이 바로 엽니다", "자동화", "▶",
                    "com.lifeagent.unified.StreamRulesActivity", Risk.LOW, "target_app_opened",
                    a("stream.autoopen", "notification.rule"), a("stream.live.started", "notification.received"),
                    a("감스트 방송 켜지면 자동으로 열어줘"), 11));
            add(new Skill("software.update.monitor", "업데이트 감시", "RustDesk 등 등록한 소프트웨어의 안정판을 확인합니다", "기기", "↻",
                    "com.lifeagent.unified.RustDeskActivity", Risk.LOW, "official_release_metadata",
                    a("software.update", "software.monitor"), a("software.update.detected", "schedule.tick"),
                    a("RustDesk 새 버전 나오면 알려줘"), 8));
            add(new Skill("profile.vault", "개인정보 금고", "개인정보와 선호를 기기 키로 암호화해 관리합니다", "보안", "◆",
                    "com.lifeagent.unified.VaultActivity", Risk.MANUAL_AUTH, "encrypted_field_write",
                    a("profile.vault", "profile.preference"), a("command.received"),
                    a("내 개인정보와 예약 선호를 관리해줘"), 7));
            add(new Skill("executor.connections", "실행기 연결", "AI 구독 실행기와 PC·Mac Companion을 관리합니다", "기기", "⌁",
                    "com.lifeagent.unified.ConnectionsActivity", Risk.MANUAL_AUTH, "signed_connection_probe",
                    a("executor.connect", "desktop.companion"), a("command.received"),
                    a("내 Mac과 AI 구독 실행기를 연결해줘"), 6));
            add(new Skill("automation.recipe.builder", "자동화 만들기", "Trigger → 조건 → Action → 검증을 한 규칙으로 묶습니다", "자동화", "⌘",
                    "com.lifeagent.unified.MainActivity", Risk.CONFIRM, "recipe_saved",
                    a("automation.recipe"), a("command.received", "shortcut.opened"),
                    a("이 알림이 오면 자동으로 처리하는 규칙 만들어줘"), 14));
            add(new Skill("general.delegate", "일반 업무 맡기기", "문맥을 정리하고 필요한 스킬이나 실행기를 찾습니다", "에이전트", "✦",
                    "com.lifeagent.unified.GeneralTaskActivity", Risk.CONFIRM, "explicit_user_result",
                    a("general.assist", "document.read"), a("command.received", "content.shared", "text.selected", "notification.opened"),
                    a("이거 처리해줘"), 1));
        }

        static Registry get() {
            if (instance == null) synchronized (Registry.class) {
                if (instance == null) instance = new Registry();
            }
            return instance;
        }

        void add(Skill skill) { if (!skills.containsKey(skill.id)) skills.put(skill.id, skill); }
        Skill find(String id) { return id == null ? null : skills.get(id); }

        List<Skill> all() {
            List<Skill> result = new ArrayList<>(skills.values());
            result.sort(Comparator.comparing((Skill s) -> s.category)
                    .thenComparing((Skill s) -> -s.priority).thenComparing(s -> s.title));
            return result;
        }

        List<Skill> resolve(Set<String> caps, ContextSnapshot context) {
            List<SkillScore> scored = new ArrayList<>();
            for (Skill skill : skills.values()) {
                int score = skill.score(caps, context);
                if (score > skill.priority) scored.add(new SkillScore(skill, score));
            }
            scored.sort((a, b) -> Integer.compare(b.score, a.score));
            List<Skill> result = new ArrayList<>();
            for (SkillScore score : scored) result.add(score.skill);
            return result;
        }

        List<Skill> recommendations(ContextSnapshot context, int max) {
            List<SkillScore> scored = new ArrayList<>();
            for (Skill skill : skills.values()) {
                int score = skill.score(Collections.emptySet(), context);
                if (context == null || context.source == Source.APP) {
                    if (skill.id.equals("reservation.orchestrator")) score += 7;
                    if (skill.id.equals("insurance.claim.monimo")) score += 5;
                    if (skill.id.equals("stream.autoopen")) score += 4;
                }
                scored.add(new SkillScore(skill, score));
            }
            scored.sort((a, b) -> Integer.compare(b.score, a.score));
            List<Skill> result = new ArrayList<>();
            for (SkillScore score : scored) {
                if (result.size() >= max) break;
                result.add(score.skill);
            }
            return result;
        }
    }

    static final class IntentSpec {
        final String goal;
        final Set<String> capabilities;
        final int confidence;
        final boolean externalEffect;
        final boolean irreversible;
        final boolean authentication;
        final boolean recipeCandidate;
        final String explanation;

        IntentSpec(String goal, Set<String> capabilities, int confidence, boolean externalEffect,
                   boolean irreversible, boolean authentication, boolean recipeCandidate, String explanation) {
            this.goal = goal;
            this.capabilities = capabilities;
            this.confidence = confidence;
            this.externalEffect = externalEffect;
            this.irreversible = irreversible;
            this.authentication = authentication;
            this.recipeCandidate = recipeCandidate;
            this.explanation = explanation;
        }
    }

    static final class Interpreter {
        static IntentSpec interpret(String raw, ContextSnapshot context) {
            String command = safe(raw).trim();
            if (command.isEmpty()) command = ContextEngine.recommendedPrompt(context);
            String n = normalize(command + " " + (context == null ? "" : context.safeSummary));
            Set<String> caps = new LinkedHashSet<>();
            boolean effect = false, irreversible = false, auth = false, recipe = false;
            int confidence = 30;
            String why = "일반 업무로 해석했습니다.";

            if (has(n, "예약", "진료잡", "자리잡", "미용실", "식당")) {
                caps.add("reservation.plan");
                if (has(n, "해줘", "잡아", "확정", "신청", "전화")) { caps.add("reservation.execute"); effect = true; }
                if (has(n, "전화", "통화")) caps.add("phone.call");
                confidence = 88; why = "예약 목표와 가능한 실행 경로를 찾았습니다.";
            }
            boolean document = context != null && (context.mimeType.startsWith("image/")
                    || "application/pdf".equalsIgnoreCase(context.mimeType));
            if (has(n, "보험", "모니모", "보험금", "청구", "추가서류", "진료비")
                    || (document && has(n, "병원", "영수증", "진료"))) {
                Collections.addAll(caps, "insurance.claim", "document.read", "document.ocr");
                if (has(n, "추가서류", "문제", "카톡", "결과")) caps.add("notification.followup");
                effect = has(n, "청구해", "신청", "제출", "처리해");
                confidence = document ? 93 : 87;
                why = document ? "공유된 병원 문서와 보험 청구 의도를 연결했습니다." : "보험 청구 또는 후속 처리 목표입니다.";
            } else if (document) {
                caps.add("document.read"); confidence = 66; why = "공유된 문서를 먼저 읽어야 합니다.";
            }
            if (has(n, "송금", "이체", "입금", "돈보내", "보내줘")) {
                Collections.addAll(caps, "money.transfer", "money.transfer.draft");
                effect = true; irreversible = true; auth = true; confidence = 94;
                why = "금융 실행이 포함돼 생체인증 관문을 적용합니다.";
            }
            if (has(n, "회원가입", "가입해", "폼채워", "자동입력", "신청서")) {
                Collections.addAll(caps, "identity.signup", "form.autofill");
                effect = has(n, "가입해", "제출", "신청해");
                auth = auth || has(n, "본인인증", "인증", "로그인"); confidence = Math.max(confidence, 89);
                why = "회원가입과 개인정보 자동입력 능력이 필요합니다.";
            }
            if (has(n, "방송", "스트리머", "치지직", "soop", "숲", "라이브")) {
                Collections.addAll(caps, "stream.autoopen", "notification.rule");
                recipe = has(n, "켜지면", "시작하면", "때마다", "자동", "바로열");
                confidence = Math.max(confidence, 91); why = recipe ? "방송 알림을 트리거로 쓰는 결정론적 규칙입니다." : "방송 실행 스킬입니다.";
            }
            if (has(n, "rustdesk", "러스트데스크", "업데이트", "새버전", "버전확인")) {
                Collections.addAll(caps, "software.update", "software.monitor");
                recipe = recipe || has(n, "나오면", "있으면", "알려", "감시"); confidence = Math.max(confidence, 86);
                why = "공식 릴리스 기반 업데이트 감시입니다.";
            }
            if (has(n, "내정보", "개인정보", "주소바꿔", "전화번호바꿔", "선호저장", "금고")) {
                Collections.addAll(caps, "profile.vault", "profile.preference"); auth = true; effect = true;
                confidence = Math.max(confidence, 90); why = "암호화 금고의 정보 변경 작업입니다.";
            }
            if (has(n, "맥연결", "pc연결", "컴퓨터연결", "구독연결", "모델연결", "실행기")) {
                Collections.addAll(caps, "executor.connect", "desktop.companion"); auth = true;
                confidence = Math.max(confidence, 85); why = "기기 또는 구독 실행기 연결 작업입니다.";
            }
            if (has(n, "자동화만들", "규칙만들", "때마다", "트리거")) {
                caps.add("automation.recipe"); recipe = true; confidence = Math.max(confidence, 76);
                why = "반복 가능한 Trigger → Action 규칙 후보입니다.";
            }
            if (caps.isEmpty()) { caps.add("general.assist"); confidence = command.isEmpty() ? 10 : 42; }
            if (context != null && context.sensitive) { auth = true; confidence = Math.min(confidence, 70); why += " 민감 원문은 저장하지 않습니다."; }
            return new IntentSpec(command, caps, confidence, effect, irreversible, auth, recipe, why);
        }
    }

    static final class PolicyDecision {
        final Gate gate;
        final String reason;
        PolicyDecision(Gate gate, String reason) { this.gate = gate; this.reason = reason; }
    }

    static final class PolicyKernel {
        PolicyDecision evaluate(IntentSpec intent, Skill skill) {
            if (intent == null || skill == null) return new PolicyDecision(Gate.BLOCK, "의도 또는 스킬을 확정하지 못했습니다.");
            if (intent.capabilities.contains("money.transfer") || intent.irreversible)
                return new PolicyDecision(Gate.BIOMETRIC, "수취인과 금액 확인, 기기 인증, 은행 인증이 필요합니다.");
            if (skill.risk == Risk.MANUAL_AUTH || intent.authentication)
                return new PolicyDecision(Gate.MANUAL_AUTH, "비밀번호·OTP·생체정보는 사용자가 직접 처리합니다.");
            if (intent.externalEffect || skill.risk == Risk.CONFIRM)
                return new PolicyDecision(Gate.CONFIRM, "외부 제출 또는 확정 전에 계획과 대상을 확인합니다.");
            if (skill.risk == Risk.BIOMETRIC)
                return new PolicyDecision(Gate.BIOMETRIC, "민감 작업은 생체인증 뒤에만 진행합니다.");
            if (intent.recipeCandidate && intent.confidence >= 80)
                return new PolicyDecision(Gate.AUTO, "사용자가 정한 좁고 결정론적인 규칙으로 실행할 수 있습니다.");
            return new PolicyDecision(Gate.AUTO, "외부 제출 없는 준비 단계는 자동으로 진행합니다.");
        }
    }

    static final class Route {
        final Executor primary;
        final Executor fallback;
        final int difficulty;
        final String label;
        final String rationale;
        Route(Executor primary, Executor fallback, int difficulty, String label, String rationale) {
            this.primary = primary; this.fallback = fallback; this.difficulty = difficulty;
            this.label = label; this.rationale = rationale;
        }
    }

    static final class ExecutorRouter {
        Route route(IntentSpec intent, PolicyDecision policy, int failures) {
            if (policy.gate == Gate.BLOCK) return new Route(Executor.HUMAN, Executor.HUMAN, 100, "차단", policy.reason);
            if (policy.gate == Gate.BIOMETRIC || policy.gate == Gate.MANUAL_AUTH)
                return new Route(Executor.HUMAN, Executor.ANDROID_INTENT, 72, "사용자 관문", "인증 직전까지 준비하고 사용자가 이어받습니다.");
            if (intent.recipeCandidate && intent.confidence >= 80 && failures == 0)
                return new Route(Executor.MODEL_FREE, Executor.MOBILE_CU, 12, "모델 없이", "검증된 Trigger → Action 규칙을 재생합니다.");
            if (intent.capabilities.contains("document.ocr") || intent.capabilities.contains("document.read"))
                return new Route(Executor.LOCAL_OCR, Executor.MOBILE_CU, 34, "기기에서 문서 읽기", "온디바이스 OCR을 먼저 사용합니다.");
            if (intent.capabilities.contains("form.autofill"))
                return new Route(Executor.AUTOFILL, Executor.MOBILE_CU, 28, "보안 자동입력", "허용된 금고 필드만 전달합니다.");
            if (intent.capabilities.contains("phone.call"))
                return new Route(Executor.SUBSCRIPTION, Executor.HUMAN, 58, "전화 실행기", "전화 예약 실행기 연결을 확인합니다.");
            if (intent.capabilities.contains("desktop.companion"))
                return new Route(Executor.DESKTOP, Executor.HUMAN, 46, "PC·Mac Companion", "서명된 Companion 채널을 사용합니다.");
            if (failures >= 2 || intent.confidence < 55)
                return new Route(Executor.MOBILE_CU, Executor.HUMAN, 78, "화면 복구", "모호하거나 반복 실패한 화면만 CU로 승격합니다.");
            return new Route(Executor.ANDROID_INTENT, Executor.MOBILE_CU, 22, "기본 앱 실행", "공식 Intent와 앱 링크를 우선 사용합니다.");
        }
    }

    static final class Step {
        String id, title, executor, evidence, failure;
        StepStatus status;
        boolean checkpoint;
        Step(String id, String title, String executor, StepStatus status, boolean checkpoint) {
            this.id=id; this.title=title; this.executor=executor; this.status=status; this.checkpoint=checkpoint;
            this.evidence=""; this.failure="";
        }
        JSONObject json() throws JSONException {
            return new JSONObject().put("id",id).put("title",title).put("executor",executor)
                    .put("status",status.name()).put("checkpoint",checkpoint)
                    .put("evidence",evidence).put("failure",failure);
        }
        static Step parse(JSONObject j) {
            Step s=new Step(j.optString("id",UUID.randomUUID().toString()),j.optString("title","단계"),
                    j.optString("executor",Executor.HUMAN.name()),enumValue(StepStatus.class,j.optString("status"),StepStatus.PENDING),j.optBoolean("checkpoint"));
            s.evidence=j.optString("evidence",""); s.failure=j.optString("failure",""); return s;
        }
    }

    static final class Task {
        final String id;
        String goal, skillId, skillTitle, policy, primary, fallback, nextAction, context, verification, evidence, failure;
        TaskStatus status;
        int difficulty, confidence, currentStep, failures;
        long createdAt, updatedAt;
        final List<Step> steps=new ArrayList<>();
        Task(String id){this.id=id;}
        boolean attention(){return status==TaskStatus.NEEDS_CONFIRMATION||status==TaskStatus.NEEDS_AUTH||status==TaskStatus.PROBLEM;}
        boolean active(){return attention()||status==TaskStatus.READY||status==TaskStatus.RUNNING||status==TaskStatus.VERIFYING;}
        JSONObject json() throws JSONException {
            JSONArray ss=new JSONArray(); for(Step s:steps)ss.put(s.json());
            return new JSONObject().put("id",id).put("goal",goal).put("skill_id",skillId).put("skill_title",skillTitle)
                    .put("status",status.name()).put("policy",policy).put("primary",primary).put("fallback",fallback)
                    .put("difficulty",difficulty).put("confidence",confidence).put("current_step",currentStep).put("failures",failures)
                    .put("next_action",nextAction).put("context",context).put("verification",verification)
                    .put("evidence",evidence).put("failure",failure).put("created_at",createdAt).put("updated_at",updatedAt).put("steps",ss);
        }
        static Task parse(JSONObject j){
            Task t=new Task(j.optString("id",UUID.randomUUID().toString()));
            t.goal=j.optString("goal","업무"); t.skillId=j.optString("skill_id",""); t.skillTitle=j.optString("skill_title","일반 업무");
            t.status=enumValue(TaskStatus.class,j.optString("status"),TaskStatus.DRAFT); t.policy=j.optString("policy",Gate.CONFIRM.name());
            t.primary=j.optString("primary",Executor.HUMAN.name()); t.fallback=j.optString("fallback",Executor.HUMAN.name());
            t.difficulty=j.optInt("difficulty",50); t.confidence=j.optInt("confidence",0); t.currentStep=j.optInt("current_step",0); t.failures=j.optInt("failures",0);
            t.nextAction=j.optString("next_action","계속하기"); t.context=j.optString("context",""); t.verification=j.optString("verification","explicit_user_result");
            t.evidence=j.optString("evidence",""); t.failure=j.optString("failure",""); t.createdAt=j.optLong("created_at",System.currentTimeMillis()); t.updatedAt=j.optLong("updated_at",t.createdAt);
            JSONArray a=j.optJSONArray("steps"); if(a!=null)for(int i=0;i<a.length();i++){JSONObject o=a.optJSONObject(i);if(o!=null)t.steps.add(Step.parse(o));} return t;
        }
    }

    static final class TaskGraph {
        private static final String PREFS="life_agent_os_task_graph_v2", KEY="tasks";
        private final SharedPreferences prefs;
        TaskGraph(Context context){prefs=context.getApplicationContext().getSharedPreferences(PREFS,Context.MODE_PRIVATE);}

        synchronized Task create(IntentSpec intent, Skill skill, PolicyDecision policy, Route route, ContextSnapshot context){
            Task t=new Task(UUID.randomUUID().toString()); t.goal=intent.goal.isEmpty()?skill.title:intent.goal; t.skillId=skill.id; t.skillTitle=skill.title;
            t.status=initial(policy.gate); t.policy=policy.gate.name(); t.primary=route.primary.name(); t.fallback=route.fallback.name();
            t.difficulty=route.difficulty; t.confidence=intent.confidence; t.currentStep=1; t.failures=0; t.nextAction=next(policy.gate,skill.title);
            t.context=context==null?"":context.safeSummary; t.verification=skill.verification; t.evidence="";t.failure="";t.createdAt=System.currentTimeMillis();t.updatedAt=t.createdAt;
            t.steps.add(new Step("understand","목표와 현재 문맥 확인","CONTEXT_ENGINE",StepStatus.DONE,false));
            t.steps.add(new Step("prepare","필요한 정보·권한 준비",route.primary.name(),policy.gate==Gate.AUTO?StepStatus.ACTIVE:StepStatus.WAITING_USER,true));
            t.steps.add(new Step("execute",skill.title+" 실행",route.primary.name(),StepStatus.PENDING,true));
            t.steps.add(new Step("verify","실제 성공 증거 확인","VERIFICATION_KERNEL",StepStatus.PENDING,true));
            t.steps.add(new Step("finish","결과 정리와 후속 작업 연결","TASK_GRAPH",StepStatus.PENDING,false));
            List<Task> all=mutable(); all.add(0,t); while(all.size()>80)all.remove(all.size()-1); save(all); return t;
        }

        synchronized List<Task> all(){List<Task>a=mutable();a.sort(Comparator.comparingLong((Task t)->t.updatedAt).reversed());return a;}
        synchronized List<Task> active(){List<Task>r=new ArrayList<>();for(Task t:all())if(t.active())r.add(t);return r;}
        synchronized List<Task> attention(){List<Task>r=new ArrayList<>();for(Task t:all())if(t.attention())r.add(t);return r;}
        synchronized int completed(){int n=0;for(Task t:mutable())if(t.status==TaskStatus.COMPLETED)n++;return n;}
        synchronized Task find(String id){for(Task t:mutable())if(t.id.equals(id))return t;return null;}
        synchronized void running(String id){mutate(id,t->{t.status=TaskStatus.RUNNING;t.nextAction="스킬 실행 결과 확인";if(t.currentStep<t.steps.size())t.steps.get(t.currentStep).status=StepStatus.ACTIVE;});}
        synchronized void auth(String id,String next){mutate(id,t->{t.status=TaskStatus.NEEDS_AUTH;t.nextAction=next;if(t.currentStep<t.steps.size())t.steps.get(t.currentStep).status=StepStatus.WAITING_USER;});}
        synchronized void problem(String id,String code,String next){mutate(id,t->{t.status=TaskStatus.PROBLEM;t.failures++;t.failure=code;t.nextAction=next;if(t.currentStep<t.steps.size()){Step s=t.steps.get(t.currentStep);s.status=StepStatus.FAILED;s.failure=code;}});}
        synchronized void cancel(String id){mutate(id,t->{t.status=TaskStatus.CANCELLED;t.nextAction="취소됨";});}
        synchronized void evidence(String id,String evidence,boolean verified){mutate(id,t->{t.evidence=evidence;if(verified){t.status=TaskStatus.COMPLETED;t.nextAction="완료됨";for(Step s:t.steps)if(s.status==StepStatus.PENDING||s.status==StepStatus.ACTIVE)s.status=StepStatus.DONE;}else{t.status=TaskStatus.VERIFYING;t.nextAction="외부 서비스의 완료 증거 기다리기";}});}
        private void mutate(String id,Mutator m){List<Task>a=mutable();for(Task t:a)if(t.id.equals(id)){m.apply(t);t.updatedAt=System.currentTimeMillis();save(a);return;}}
        private List<Task> mutable(){List<Task>r=new ArrayList<>();try{JSONArray a=new JSONArray(prefs.getString(KEY,"[]"));for(int i=0;i<a.length();i++){JSONObject j=a.optJSONObject(i);if(j!=null)r.add(Task.parse(j));}}catch(Exception ignored){}return r;}
        private void save(List<Task>a){try{JSONArray out=new JSONArray();for(Task t:a)out.put(t.json());prefs.edit().putString(KEY,out.toString()).apply();}catch(Exception ignored){}}
        private interface Mutator{void apply(Task task);}
    }

    static final class Recipe {
        final String id; String name, triggerValue, condition, skillId; TriggerType type; boolean enabled, autoRun; int verifiedRuns, failures; long updatedAt;
        Recipe(String id){this.id=id;}
        boolean modelFree(){return enabled&&autoRun&&failures==0;}
        JSONObject json()throws JSONException{return new JSONObject().put("id",id).put("name",name).put("type",type.name()).put("trigger",triggerValue).put("condition",condition).put("skill",skillId).put("enabled",enabled).put("auto",autoRun).put("verified",verifiedRuns).put("failures",failures).put("updated",updatedAt);}
        static Recipe parse(JSONObject j){Recipe r=new Recipe(j.optString("id",UUID.randomUUID().toString()));r.name=j.optString("name","자동화");r.type=enumValue(TriggerType.class,j.optString("type"),TriggerType.MANUAL_SHORTCUT);r.triggerValue=j.optString("trigger","");r.condition=j.optString("condition","");r.skillId=j.optString("skill","general.delegate");r.enabled=j.optBoolean("enabled",true);r.autoRun=j.optBoolean("auto",false);r.verifiedRuns=j.optInt("verified",0);r.failures=j.optInt("failures",0);r.updatedAt=j.optLong("updated",System.currentTimeMillis());return r;}
    }

    static final class Recipes {
        private static final String PREFS="life_agent_os_recipes_v2",KEY="recipes",CHANNEL="life_agent_recipe_events_v2";
        private final Context context; private final SharedPreferences prefs;
        Recipes(Context context){this.context=context.getApplicationContext();prefs=this.context.getSharedPreferences(PREFS,Context.MODE_PRIVATE);}
        synchronized Recipe create(String name,TriggerType type,String trigger,String condition,String skillId,boolean auto){
            if(safe(name).trim().isEmpty())throw new IllegalArgumentException("규칙 이름이 필요합니다.");
            if(safe(trigger).trim().length()<2)throw new IllegalArgumentException("트리거 값은 두 글자 이상이어야 합니다.");
            Skill skill=Registry.get().find(skillId);if(skill==null)throw new IllegalArgumentException("실행 스킬을 찾지 못했습니다.");
            Recipe r=new Recipe(UUID.randomUUID().toString());r.name=name.trim();r.type=type;r.triggerValue=trigger.trim();r.condition=safe(condition).trim();r.skillId=skillId;r.enabled=true;r.autoRun=auto&&skill.risk==Risk.LOW;r.updatedAt=System.currentTimeMillis();
            List<Recipe>a=mutable();a.add(0,r);save(a);return r;
        }
        synchronized List<Recipe> all(){List<Recipe>a=mutable();a.sort(Comparator.comparingLong((Recipe r)->r.updatedAt).reversed());return a;}
        synchronized void enabled(String id,boolean value){mutate(id,r->r.enabled=value);}
        synchronized void delete(String id){List<Recipe>a=mutable();a.removeIf(r->r.id.equals(id));save(a);}
        synchronized void outcome(String id,boolean success){mutate(id,r->{if(success){r.verifiedRuns++;r.failures=0;}else{r.failures++;r.autoRun=false;}});}
        synchronized List<Recipe> matching(TriggerType type,String text){String n=normalize(text);List<Recipe>r=new ArrayList<>();for(Recipe x:mutable())if(x.enabled&&x.type==type&&!normalize(x.triggerValue).isEmpty()&&n.contains(normalize(x.triggerValue)))r.add(x);return r;}
        private void mutate(String id,RecipeMutator m){List<Recipe>a=mutable();for(Recipe r:a)if(r.id.equals(id)){m.apply(r);r.updatedAt=System.currentTimeMillis();save(a);return;}}
        private List<Recipe> mutable(){List<Recipe>r=new ArrayList<>();try{JSONArray a=new JSONArray(prefs.getString(KEY,"[]"));for(int i=0;i<a.length();i++){JSONObject j=a.optJSONObject(i);if(j!=null)r.add(Recipe.parse(j));}}catch(Exception ignored){}return r;}
        private void save(List<Recipe>a){try{JSONArray out=new JSONArray();for(Recipe r:a)out.put(r.json());prefs.edit().putString(KEY,out.toString()).apply();}catch(Exception ignored){}}
        private interface RecipeMutator{void apply(Recipe recipe);}

        static void onNotification(Context context,String safeText){
            if(safeText==null||safeText.isEmpty())return;Recipes store=new Recipes(context);List<Recipe>matches=store.matching(TriggerType.NOTIFICATION_MATCH,safeText);if(matches.size()!=1)return;
            Recipe recipe=matches.get(0);Skill skill=Registry.get().find(recipe.skillId);if(skill==null){store.outcome(recipe.id,false);return;}postHandoff(context,recipe,skill,safeText);
        }
        private static void postHandoff(Context context,Recipe recipe,Skill skill,String safeText){
            NotificationManager nm=context.getSystemService(NotificationManager.class);if(nm==null)return;
            if(Build.VERSION.SDK_INT>=26)nm.createNotificationChannel(new NotificationChannel(CHANNEL,"Life Agent 자동화",NotificationManager.IMPORTANCE_DEFAULT));
            Intent i=new Intent(context,AgentEntryActivity.class).setAction(Intent.ACTION_VIEW).putExtra(EXTRA_SOURCE,Source.NOTIFICATION.name()).putExtra(EXTRA_COMMAND,recipe.name).putExtra(EXTRA_SKILL_ID,skill.id).putExtra(EXTRA_CONTEXT,shorten(safeText,150));
            PendingIntent pi=PendingIntent.getActivity(context,recipe.id.hashCode(),i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
            Notification.Builder b=Build.VERSION.SDK_INT>=26?new Notification.Builder(context,CHANNEL):new Notification.Builder(context);
            b.setSmallIcon(android.R.drawable.ic_popup_sync).setContentTitle("자동화 조건 일치 · "+recipe.name).setContentText(skill.title+" 작업을 준비했습니다").setContentIntent(pi).setAutoCancel(true).setOnlyAlertOnce(true).setCategory(Notification.CATEGORY_EVENT);
            nm.notify(recipe.id.hashCode(),b.build());
        }
    }

    static final class Events {
        private static final String PREFS="life_agent_os_event_v2",KEY="last";
        static void remember(Context context,String source,String trigger,String summary,String mime){
            try{JSONObject j=new JSONObject().put("source",safe(source)).put("trigger",safe(trigger)).put("summary",safe(summary)).put("mime",safe(mime)).put("at",System.currentTimeMillis());context.getApplicationContext().getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString(KEY,j.toString()).apply();}catch(Exception ignored){}
        }
        static Event last(Context context){try{JSONObject j=new JSONObject(context.getApplicationContext().getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString(KEY,"{}"));return new Event(j.optString("source"),j.optString("trigger"),j.optString("summary"),j.optString("mime"),j.optLong("at"));}catch(Exception ignored){return new Event("","","","",0);}}
        static String captureNotification(Context context,StatusBarNotification sbn){
            if(sbn==null||sbn.getNotification()==null)return "";Bundle e=sbn.getNotification().extras;String title=chars(e.getCharSequence(Notification.EXTRA_TITLE));String body=chars(e.getCharSequence(Notification.EXTRA_BIG_TEXT));if(body.isEmpty())body=chars(e.getCharSequence(Notification.EXTRA_TEXT));String combined=(title+" "+body).replaceAll("\\s+"," ").trim();if(combined.isEmpty())return "";
            if(ContextEngine.looksSensitive(combined)||has(normalize(combined),"인증번호","인증코드","otp")){remember(context,Source.NOTIFICATION.name(),"notification.received","민감 알림은 내용 없이 감지했습니다.","");return "";}
            String redacted=shorten(ContextEngine.redact(combined),160);String trigger=classify(normalize(combined));remember(context,Source.NOTIFICATION.name(),trigger,redacted,"");Recipes.onNotification(context,redacted);return redacted;
        }
        private static String classify(String n){if(has(n,"보험금","삼성화재","추가서류","모니모"))return"insurance.notification.received";if(has(n,"방송을시작","라이브시작","생방송","isnowlive"))return"stream.live.started";if(has(n,"예약완료","예약확정","방문예정"))return"reservation.confirmed";if(has(n,"업데이트","새버전","release"))return"software.update.detected";return"notification.received";}
    }

    static final class Event {final String source,trigger,summary,mime;final long at;Event(String s,String t,String m,String mime,long at){source=s;trigger=t;summary=m;this.mime=mime;this.at=at;}boolean fresh(long age){return at>0&&System.currentTimeMillis()-at<=age;}}

    static final class Plan {
        final ContextSnapshot context;final IntentSpec intent;final Skill skill;final PolicyDecision policy;final Route route;final Task task;
        Plan(ContextSnapshot c,IntentSpec i,Skill s,PolicyDecision p,Route r,Task t){context=c;intent=i;skill=s;policy=p;route=r;task=t;}
    }

    static final class Planner {
        private final Registry registry=Registry.get();private final PolicyKernel policy=new PolicyKernel();private final ExecutorRouter router=new ExecutorRouter();private final TaskGraph graph;
        Planner(Context context){graph=new TaskGraph(context);}
        Plan plan(String command,ContextSnapshot context){IntentSpec intent=Interpreter.interpret(command,context);List<Skill>matches=registry.resolve(intent.capabilities,context);Skill skill=choose(matches,intent);if(skill==null)skill=registry.find("general.delegate");PolicyDecision p=policy.evaluate(intent,skill);Route r=router.route(intent,p,0);Task t=graph.create(intent,skill,p,r,context);return new Plan(context,intent,skill,p,r,t);}
        private Skill choose(List<Skill>matches,IntentSpec intent){if(matches.isEmpty())return null;if(intent.capabilities.contains("document.read")&&!intent.capabilities.contains("insurance.claim")){for(Skill s:matches)if(s.id.equals("general.delegate"))return s;}return matches.get(0);}
    }

    static boolean start(Context context,Plan plan){
        TaskGraph graph=new TaskGraph(context);if(plan.policy.gate==Gate.BLOCK){graph.problem(plan.task.id,"POLICY_BLOCKED","입력과 권한 확인");return false;}
        if(plan.skill.id.equals("automation.recipe.builder")){graph.running(plan.task.id);Intent i=new Intent(context,MainActivity.class).putExtra(EXTRA_TAB,"automations").addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP);context.startActivity(i);return true;}
        Intent intent=plan.skill.launch(context,plan.task.id,plan.context,plan.intent.goal);if(intent==null){graph.problem(plan.task.id,"SKILL_UI_NOT_AVAILABLE","실행기 연결 확인");return false;}
        try{if(plan.policy.gate==Gate.BIOMETRIC||plan.policy.gate==Gate.MANUAL_AUTH)graph.auth(plan.task.id,plan.task.nextAction);else graph.running(plan.task.id);context.startActivity(intent);return true;}catch(RuntimeException e){graph.problem(plan.task.id,"SKILL_LAUNCH_FAILED","스킬 연결 복구");return false;}
    }

    static boolean resume(Context context,Task task){Skill skill=Registry.get().find(task.skillId);TaskGraph graph=new TaskGraph(context);if(skill==null){graph.problem(task.id,"SKILL_NOT_REGISTERED","스킬 다시 연결");return false;}Intent intent=skill.launch(context,task.id,ContextSnapshot.empty(),task.goal);try{context.startActivity(intent);graph.running(task.id);return true;}catch(RuntimeException e){graph.problem(task.id,"RESUME_FAILED","다른 실행 경로 선택");return false;}}

    private static TaskStatus initial(Gate gate){switch(gate){case BIOMETRIC:case MANUAL_AUTH:return TaskStatus.NEEDS_AUTH;case CONFIRM:return TaskStatus.NEEDS_CONFIRMATION;case BLOCK:return TaskStatus.PROBLEM;default:return TaskStatus.READY;}}
    private static String next(Gate gate,String skill){switch(gate){case BIOMETRIC:return"수취인·금액 확인 후 생체인증";case MANUAL_AUTH:return"사용자 인증 후 계속";case CONFIRM:return"계획 확인 후 "+skill+" 시작";case BLOCK:return"입력과 권한 다시 확인";default:return skill+" 시작";}}
    private static Set<String> set(String[] values){Set<String>s=new LinkedHashSet<>();Collections.addAll(s,values);return Collections.unmodifiableSet(s);}
    private static String[] a(String...values){return values;}
    private static String safe(String value){return value==null?"":value;}
    private static String chars(CharSequence value){return value==null?"":value.toString();}
    private static String normalize(String value){return safe(value).toLowerCase(Locale.ROOT).replaceAll("[\\s\\p{Punct}·ㆍ]+","");}
    private static boolean has(String value,String...needles){for(String needle:needles)if(value.contains(normalize(needle)))return true;return false;}
    private static String shorten(String value,int max){String v=safe(value).replaceAll("\\s+"," ").trim();return v.length()<=max?v:v.substring(0,Math.max(0,max-1))+"…";}
    private static <E extends Enum<E>> E enumValue(Class<E> type,String raw,E fallback){try{return Enum.valueOf(type,safe(raw).toUpperCase(Locale.ROOT));}catch(Exception ignored){return fallback;}}
    private static final class SkillScore{final Skill skill;final int score;SkillScore(Skill skill,int score){this.skill=skill;this.score=score;}}
}
