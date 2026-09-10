package com.lifeagent.unified.core;

import java.text.Normalizer;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * Pure-Java decision core for Life Agent OS. Android services are adapters around this kernel.
 * It deliberately separates intent planning, policy, execution routing and verification.
 */
public final class AgentCore {
    private AgentCore() {}

    public enum Sensitivity { PUBLIC, PERSONAL, SENSITIVE, RESTRICTED }
    public enum Risk { LOW, MEDIUM, HIGH, CRITICAL }
    public enum PolicyDecision { AUTO, CONFIRM, BIOMETRIC, MANUAL_AUTH, BLOCK }
    public enum ExecutorType {
        MODEL_FREE,
        ANDROID_INTENT,
        LOCAL_OCR,
        AUTOFILL,
        NOTIFICATION_ACTION,
        LOCATION_CONTEXT,
        OFFICIAL_WEB,
        PHONE,
        SUBSCRIPTION_AI,
        MOBILE_CU,
        DESKTOP_COMPANION,
        HUMAN
    }
    public enum TaskStatus {
        PLANNED,
        READY,
        RUNNING,
        WAITING_USER,
        WAITING_EXTERNAL,
        VERIFYING,
        COMPLETED,
        BLOCKED,
        FAILED
    }
    public enum OpportunityKind {
        URGENT,
        BENEFIT,
        NEARBY,
        CONVENIENCE,
        UPDATE,
        COMMERCIAL
    }

    public static final class ContextFact {
        public final String key;
        public final String value;
        public final Sensitivity sensitivity;
        public final long expiresAtEpochMs;
        public final boolean mayDriveAutomation;
        public final boolean mayDriveCommercialRecommendations;

        public ContextFact(
                String key,
                String value,
                Sensitivity sensitivity,
                long expiresAtEpochMs,
                boolean mayDriveAutomation,
                boolean mayDriveCommercialRecommendations
        ) {
            this.key = requireText(key, "key");
            this.value = value == null ? "" : value;
            this.sensitivity = Objects.requireNonNull(sensitivity, "sensitivity");
            this.expiresAtEpochMs = expiresAtEpochMs;
            this.mayDriveAutomation = mayDriveAutomation;
            this.mayDriveCommercialRecommendations = mayDriveCommercialRecommendations;
        }

        public boolean isExpired(long nowEpochMs) {
            return expiresAtEpochMs > 0 && nowEpochMs >= expiresAtEpochMs;
        }
    }

    public static final class PersonalContextGraph {
        private final Map<String, ContextFact> facts = new LinkedHashMap<>();

        public synchronized void put(ContextFact fact) {
            facts.put(fact.key, fact);
        }

        public synchronized ContextFact get(String key, long nowEpochMs) {
            ContextFact fact = facts.get(key);
            if (fact != null && fact.isExpired(nowEpochMs)) {
                facts.remove(key);
                return null;
            }
            return fact;
        }

        public synchronized void remove(String key) {
            facts.remove(key);
        }

        public synchronized void purgeExpired(long nowEpochMs) {
            List<String> expired = new ArrayList<>();
            for (ContextFact fact : facts.values()) {
                if (fact.isExpired(nowEpochMs)) expired.add(fact.key);
            }
            for (String key : expired) facts.remove(key);
        }

        public synchronized List<ContextFact> snapshot(long nowEpochMs) {
            purgeExpired(nowEpochMs);
            return Collections.unmodifiableList(new ArrayList<>(facts.values()));
        }

        public synchronized boolean hasValueContaining(String token, long nowEpochMs) {
            String needle = normalize(token);
            if (needle.isEmpty()) return false;
            for (ContextFact fact : snapshot(nowEpochMs)) {
                if (normalize(fact.value).contains(needle)) return true;
            }
            return false;
        }

        public synchronized String value(String key, long nowEpochMs) {
            ContextFact fact = get(key, nowEpochMs);
            return fact == null ? "" : fact.value;
        }
    }

    public static final class AmbientEvent {
        public final String id;
        public final String source;
        public final String type;
        public final String summary;
        public final String packageName;
        public final long occurredAtEpochMs;
        public final Map<String, String> entities;
        public final Sensitivity sensitivity;
        public final boolean actionable;

        public AmbientEvent(
                String id,
                String source,
                String type,
                String summary,
                String packageName,
                long occurredAtEpochMs,
                Map<String, String> entities,
                Sensitivity sensitivity,
                boolean actionable
        ) {
            this.id = id == null || id.isBlank() ? UUID.randomUUID().toString() : id;
            this.source = requireText(source, "source");
            this.type = requireText(type, "type");
            this.summary = sanitizeIncoming(summary);
            this.packageName = packageName == null ? "" : packageName;
            this.occurredAtEpochMs = occurredAtEpochMs;
            this.entities = Collections.unmodifiableMap(new LinkedHashMap<>(entities == null ? Map.of() : entities));
            this.sensitivity = Objects.requireNonNull(sensitivity, "sensitivity");
            this.actionable = actionable;
        }
    }

    public static final class SkillManifest {
        public final String id;
        public final String name;
        public final String description;
        public final Set<String> capabilities;
        public final Set<String> triggers;
        public final Set<String> keywords;
        public final Set<ExecutorType> executors;
        public final Risk risk;
        public final String verificationEvidence;
        public final boolean connectorRequired;

        public SkillManifest(
                String id,
                String name,
                String description,
                Set<String> capabilities,
                Set<String> triggers,
                Set<String> keywords,
                Set<ExecutorType> executors,
                Risk risk,
                String verificationEvidence,
                boolean connectorRequired
        ) {
            this.id = requireText(id, "id");
            this.name = requireText(name, "name");
            this.description = requireText(description, "description");
            this.capabilities = immutableSet(capabilities);
            this.triggers = immutableSet(triggers);
            this.keywords = immutableSet(keywords);
            this.executors = Collections.unmodifiableSet(new LinkedHashSet<>(executors));
            this.risk = Objects.requireNonNull(risk, "risk");
            this.verificationEvidence = requireText(verificationEvidence, "verificationEvidence");
            this.connectorRequired = connectorRequired;
        }
    }

    public static final class RankedSkill {
        public final SkillManifest skill;
        public final int score;

        RankedSkill(SkillManifest skill, int score) {
            this.skill = skill;
            this.score = score;
        }
    }

    public static final class PlanStep {
        public final String id;
        public final String title;
        public final ExecutorType executor;
        public final PolicyDecision policy;
        public final String verification;

        public PlanStep(String id, String title, ExecutorType executor, PolicyDecision policy, String verification) {
            this.id = requireText(id, "id");
            this.title = requireText(title, "title");
            this.executor = Objects.requireNonNull(executor, "executor");
            this.policy = Objects.requireNonNull(policy, "policy");
            this.verification = requireText(verification, "verification");
        }
    }

    public static final class ActionPlan {
        public final String id;
        public final String goal;
        public final SkillManifest primarySkill;
        public final List<SkillManifest> supportingSkills;
        public final PolicyDecision policy;
        public final ExecutorType primaryExecutor;
        public final List<PlanStep> steps;
        public final List<String> reasons;
        public final boolean connectorRequired;
        public final String completionEvidence;

        public ActionPlan(
                String id,
                String goal,
                SkillManifest primarySkill,
                List<SkillManifest> supportingSkills,
                PolicyDecision policy,
                ExecutorType primaryExecutor,
                List<PlanStep> steps,
                List<String> reasons,
                boolean connectorRequired,
                String completionEvidence
        ) {
            this.id = id == null || id.isBlank() ? UUID.randomUUID().toString() : id;
            this.goal = requireText(goal, "goal");
            this.primarySkill = Objects.requireNonNull(primarySkill, "primarySkill");
            this.supportingSkills = Collections.unmodifiableList(new ArrayList<>(supportingSkills));
            this.policy = Objects.requireNonNull(policy, "policy");
            this.primaryExecutor = Objects.requireNonNull(primaryExecutor, "primaryExecutor");
            this.steps = Collections.unmodifiableList(new ArrayList<>(steps));
            this.reasons = Collections.unmodifiableList(new ArrayList<>(reasons));
            this.connectorRequired = connectorRequired;
            this.completionEvidence = requireText(completionEvidence, "completionEvidence");
        }
    }

    public static final class TaskNode {
        public final String id;
        public final String title;
        public TaskStatus status;
        public final ExecutorType executor;
        public final PolicyDecision policy;
        public final String verification;
        public String evidence;
        public String failureCode;

        public TaskNode(String id, String title, TaskStatus status, ExecutorType executor,
                        PolicyDecision policy, String verification) {
            this.id = requireText(id, "id");
            this.title = requireText(title, "title");
            this.status = Objects.requireNonNull(status, "status");
            this.executor = Objects.requireNonNull(executor, "executor");
            this.policy = Objects.requireNonNull(policy, "policy");
            this.verification = requireText(verification, "verification");
            this.evidence = "";
            this.failureCode = "";
        }
    }

    public static final class TaskGraph {
        public final String id;
        public final String goal;
        public final String skillId;
        public final long createdAtEpochMs;
        public long updatedAtEpochMs;
        public TaskStatus status;
        public int activeNodeIndex;
        public final List<TaskNode> nodes;
        public String nextAction;
        public String completionEvidence;

        public TaskGraph(ActionPlan plan, long nowEpochMs) {
            this.id = plan.id;
            this.goal = plan.goal;
            this.skillId = plan.primarySkill.id;
            this.createdAtEpochMs = nowEpochMs;
            this.updatedAtEpochMs = nowEpochMs;
            this.status = plan.policy == PolicyDecision.AUTO ? TaskStatus.READY : TaskStatus.WAITING_USER;
            this.activeNodeIndex = 0;
            this.nodes = new ArrayList<>();
            for (PlanStep step : plan.steps) {
                this.nodes.add(new TaskNode(step.id, step.title, TaskStatus.PLANNED,
                        step.executor, step.policy, step.verification));
            }
            this.nextAction = nodes.isEmpty() ? "실행 단계 없음" : nodes.get(0).title;
            this.completionEvidence = plan.completionEvidence;
        }

        public synchronized TaskNode activeNode() {
            if (nodes.isEmpty() || activeNodeIndex < 0 || activeNodeIndex >= nodes.size()) return null;
            return nodes.get(activeNodeIndex);
        }

        public synchronized void markActiveRunning(long nowEpochMs) {
            TaskNode node = activeNode();
            if (node == null) return;
            node.status = TaskStatus.RUNNING;
            status = TaskStatus.RUNNING;
            updatedAtEpochMs = nowEpochMs;
            nextAction = node.title;
        }

        public synchronized void markActiveVerified(String evidence, long nowEpochMs) {
            TaskNode node = activeNode();
            if (node == null) return;
            node.evidence = evidence == null ? "" : evidence;
            node.status = TaskStatus.COMPLETED;
            activeNodeIndex++;
            updatedAtEpochMs = nowEpochMs;
            if (activeNodeIndex >= nodes.size()) {
                if (evidence == null || evidence.isBlank()) {
                    status = TaskStatus.VERIFYING;
                    nextAction = "완료 증거 확인";
                } else {
                    status = TaskStatus.COMPLETED;
                    nextAction = "완료";
                }
            } else {
                status = TaskStatus.READY;
                nextAction = nodes.get(activeNodeIndex).title;
            }
        }

        public synchronized void waitForUser(String action, long nowEpochMs) {
            TaskNode node = activeNode();
            if (node != null) node.status = TaskStatus.WAITING_USER;
            status = TaskStatus.WAITING_USER;
            nextAction = action == null || action.isBlank() ? "사용자 확인" : action;
            updatedAtEpochMs = nowEpochMs;
        }

        public synchronized void fail(String code, String action, long nowEpochMs) {
            TaskNode node = activeNode();
            if (node != null) {
                node.status = TaskStatus.FAILED;
                node.failureCode = code == null ? "UNKNOWN" : code;
            }
            status = TaskStatus.FAILED;
            nextAction = action == null || action.isBlank() ? "실패 원인 확인" : action;
            updatedAtEpochMs = nowEpochMs;
        }
    }

    public static final class Opportunity {
        public final String id;
        public final OpportunityKind kind;
        public final String title;
        public final String summary;
        public final String skillId;
        public final List<String> reasons;
        public final int score;
        public final boolean commercial;
        public final long expiresAtEpochMs;

        public Opportunity(String id, OpportunityKind kind, String title, String summary, String skillId,
                           List<String> reasons, int score, boolean commercial, long expiresAtEpochMs) {
            this.id = id == null || id.isBlank() ? UUID.randomUUID().toString() : id;
            this.kind = Objects.requireNonNull(kind, "kind");
            this.title = requireText(title, "title");
            this.summary = requireText(summary, "summary");
            this.skillId = requireText(skillId, "skillId");
            this.reasons = Collections.unmodifiableList(new ArrayList<>(reasons));
            this.score = score;
            this.commercial = commercial;
            this.expiresAtEpochMs = expiresAtEpochMs;
        }
    }

    public static final class Recipe {
        public final String id;
        public final String name;
        public final String triggerType;
        public final Map<String, String> conditions;
        public final String skillId;
        public final PolicyDecision maximumAutomation;
        public final String verification;
        public final boolean enabled;

        public Recipe(String id, String name, String triggerType, Map<String, String> conditions,
                      String skillId, PolicyDecision maximumAutomation, String verification, boolean enabled) {
            this.id = id == null || id.isBlank() ? UUID.randomUUID().toString() : id;
            this.name = requireText(name, "name");
            this.triggerType = requireText(triggerType, "triggerType");
            this.conditions = Collections.unmodifiableMap(new LinkedHashMap<>(conditions == null ? Map.of() : conditions));
            this.skillId = requireText(skillId, "skillId");
            this.maximumAutomation = Objects.requireNonNull(maximumAutomation, "maximumAutomation");
            this.verification = requireText(verification, "verification");
            this.enabled = enabled;
        }
    }

    public static final class SkillRegistry {
        private final Map<String, SkillManifest> skills = new LinkedHashMap<>();

        public SkillRegistry() {
            registerDefaults();
        }

        public synchronized void register(SkillManifest skill) {
            skills.put(skill.id, skill);
        }

        public synchronized SkillManifest get(String id) {
            return skills.get(id);
        }

        public synchronized List<SkillManifest> all() {
            return Collections.unmodifiableList(new ArrayList<>(skills.values()));
        }

        public synchronized List<RankedSkill> rank(String goal, AmbientEvent event) {
            String normalizedGoal = normalize(goal);
            String normalizedEvent = event == null ? "" : normalize(event.type + " " + event.summary);
            List<RankedSkill> ranked = new ArrayList<>();
            for (SkillManifest skill : skills.values()) {
                int score = 0;
                for (String keyword : skill.keywords) {
                    String needle = normalize(keyword);
                    if (!needle.isEmpty() && normalizedGoal.contains(needle)) score += 12;
                    if (!needle.isEmpty() && normalizedEvent.contains(needle)) score += 8;
                }
                if (event != null && skill.triggers.contains(event.type)) score += 30;
                if (skill.id.equals("general.delegate")) score += 1;
                ranked.add(new RankedSkill(skill, score));
            }
            ranked.sort(Comparator.comparingInt((RankedSkill item) -> item.score).reversed()
                    .thenComparing(item -> item.skill.id));
            return Collections.unmodifiableList(ranked);
        }

        private void registerDefaults() {
            register(skill("reservation.orchestrator", "예약 오케스트레이터",
                    "웹·앱·전화 중 가장 적절한 경로로 예약하고 확인 증거를 남깁니다.",
                    set("reservation.search", "reservation.book", "phone.call"),
                    set("goal", "notification.reservation_cancelled"),
                    set("예약", "병원", "식당", "미용실", "자리", "전화"),
                    set(ExecutorType.MODEL_FREE, ExecutorType.ANDROID_INTENT, ExecutorType.PHONE,
                            ExecutorType.SUBSCRIPTION_AI, ExecutorType.MOBILE_CU, ExecutorType.DESKTOP_COMPANION),
                    Risk.MEDIUM, "예약번호·확인 문자·캘린더 일정 중 하나", true));

            register(skill("insurance.monimo.claim", "모니모 보험금 청구",
                    "병원 서류를 판독하고 모니모 청구 및 추가서류 후속 처리를 연결합니다.",
                    set("document.read", "insurance.claim.prepare", "insurance.claim.followup"),
                    set("document.shared", "notification.insurance_followup"),
                    set("보험", "보험금", "청구", "모니모", "병원서류", "추가서류", "진료비"),
                    set(ExecutorType.LOCAL_OCR, ExecutorType.ANDROID_INTENT, ExecutorType.MOBILE_CU,
                            ExecutorType.HUMAN),
                    Risk.HIGH, "보험사 접수번호 또는 추가서류 접수 확인", true));

            register(skill("transfer.safe", "안전 송금",
                    "수취인과 금액을 초안으로 만들고 기기 인증과 은행 확인 뒤 완료합니다.",
                    set("transfer.draft", "transfer.approve", "transfer.verify"),
                    set("goal"),
                    set("송금", "이체", "보내", "입금", "계좌"),
                    set(ExecutorType.HUMAN, ExecutorType.ANDROID_INTENT),
                    Risk.CRITICAL, "은행 거래번호 또는 거래 영수증", true));

            register(skill("signup.autofill", "회원가입·보안 자동입력",
                    "개인정보 금고의 허용 필드만 입력하고 비밀번호·OTP는 사용자에게 맡깁니다.",
                    set("signup", "form.fill", "profile.inject"),
                    set("goal", "share.text"),
                    set("회원가입", "가입", "폼", "신청서", "주소입력", "자동입력"),
                    set(ExecutorType.AUTOFILL, ExecutorType.MOBILE_CU, ExecutorType.HUMAN),
                    Risk.MEDIUM, "서비스의 가입 완료 화면 또는 확인 이메일", true));

            register(skill("stream.autoplay", "방송 자동 실행",
                    "선택한 SOOP·치지직 방송 시작 알림을 정확히 매칭해 실행합니다.",
                    set("notification.match", "screen.wake", "stream.open"),
                    set("notification.stream_live"),
                    set("방송", "스트리머", "치지직", "숲", "soop", "라이브"),
                    set(ExecutorType.MODEL_FREE, ExecutorType.NOTIFICATION_ACTION,
                            ExecutorType.ANDROID_INTENT, ExecutorType.DESKTOP_COMPANION),
                    Risk.LOW, "대상 방송 화면의 채널 식별자", false));

            register(skill("software.update.monitor", "소프트웨어 업데이트 감시",
                    "RustDesk 등 지정한 소프트웨어의 공식 안정판을 감시합니다.",
                    set("software.version.read", "release.monitor"),
                    set("schedule.daily", "notification.update"),
                    set("러스트데스크", "rustdesk", "업데이트", "새버전", "릴리스"),
                    set(ExecutorType.MODEL_FREE, ExecutorType.OFFICIAL_WEB,
                            ExecutorType.DESKTOP_COMPANION),
                    Risk.LOW, "공식 릴리스 버전과 설치 버전 비교 결과", false));

            register(skill("benefits.autopilot", "혜택·지원 자동 신청",
                    "자격 프로필로 받을 수 있는 혜택을 찾고 신청서 준비와 후속 보완을 관리합니다.",
                    set("benefit.eligibility", "benefit.application.prepare", "benefit.followup"),
                    set("schedule.daily", "notification.benefit", "profile.changed"),
                    set("지원금", "혜택", "보조금", "신청", "지원사업", "할인", "복지"),
                    set(ExecutorType.MODEL_FREE, ExecutorType.OFFICIAL_WEB,
                            ExecutorType.AUTOFILL, ExecutorType.MOBILE_CU, ExecutorType.HUMAN),
                    Risk.HIGH, "기관 접수번호 또는 신청 완료 영수증", true));

            register(skill("nearby.local", "주변 생활 추천",
                    "현재 문맥과 위치를 바탕으로 약국·상점·시설을 추천합니다.",
                    set("location.coarse", "nearby.search", "recommendation.explain"),
                    set("location.changed", "goal"),
                    set("주변", "근처", "약국", "상가", "식당", "편의점", "주차", "가까운"),
                    set(ExecutorType.MODEL_FREE, ExecutorType.LOCATION_CONTEXT,
                            ExecutorType.ANDROID_INTENT, ExecutorType.OFFICIAL_WEB),
                    Risk.LOW, "지도 검색 결과 또는 사용자의 방문 선택", false));

            register(skill("vault.manage", "개인정보 금고",
                    "민감정보를 기기 키로 암호화하고 스킬에는 필요한 필드만 전달합니다.",
                    set("vault.store", "vault.lease", "vault.delete"),
                    set("goal"),
                    set("개인정보", "금고", "이름", "전화번호", "주소", "프로필"),
                    set(ExecutorType.MODEL_FREE, ExecutorType.HUMAN),
                    Risk.HIGH, "기기 암호화 저장 성공", false));

            register(skill("automation.recipe", "범용 자동화 만들기",
                    "Trigger·조건·행동·검증·실패정책을 하나의 레시피로 저장합니다.",
                    set("recipe.create", "recipe.evaluate", "recipe.audit"),
                    set("goal"),
                    set("자동화", "때마다", "오면", "하면", "자동으로", "규칙"),
                    set(ExecutorType.MODEL_FREE, ExecutorType.SUBSCRIPTION_AI, ExecutorType.HUMAN),
                    Risk.MEDIUM, "레시피 검증 통과와 사용자 동의", false));

            register(skill("connections.manage", "AI·PC 연결 관리",
                    "공식 AI 구독 클라이언트와 PC·Mac Companion의 상태를 관리합니다.",
                    set("subscription.client", "desktop.companion", "connection.health"),
                    set("goal", "connection.changed"),
                    set("ai연결", "구독", "컴패니언", "pc", "맥", "컴퓨터"),
                    set(ExecutorType.MODEL_FREE, ExecutorType.DESKTOP_COMPANION, ExecutorType.HUMAN),
                    Risk.HIGH, "연결 상태와 서명된 헬스체크", true));

            register(skill("general.delegate", "일반 업무 위임",
                    "등록된 스킬로 처리되지 않는 목표를 안전한 계획으로 분해합니다.",
                    set("goal.decompose", "skill.compose"),
                    set("goal"),
                    set("처리", "해줘", "도와", "정리"),
                    set(ExecutorType.SUBSCRIPTION_AI, ExecutorType.MOBILE_CU,
                            ExecutorType.DESKTOP_COMPANION, ExecutorType.HUMAN),
                    Risk.MEDIUM, "목표별 명시된 완료 증거", true));
        }
    }

    public static final class PolicyKernel {
        public PolicyDecision decide(SkillManifest skill, String goal, PersonalContextGraph context, long nowEpochMs) {
            String text = normalize(goal);
            if (containsAny(text, "otp", "인증번호", "비밀번호", "핀번호", "보안카드", "복구코드", "시드문구")) {
                return PolicyDecision.MANUAL_AUTH;
            }
            if (containsAny(text, "인증우회", "잠금해제우회", "몰래송금", "동의없이")) {
                return PolicyDecision.BLOCK;
            }
            if (skill.risk == Risk.CRITICAL) return PolicyDecision.BIOMETRIC;
            if (skill.id.equals("insurance.monimo.claim")) {
                return containsAny(text, "제출", "접수", "청구해") ? PolicyDecision.CONFIRM : PolicyDecision.AUTO;
            }
            if (skill.id.equals("benefits.autopilot")) {
                return containsAny(text, "제출", "신청해", "접수") ? PolicyDecision.CONFIRM : PolicyDecision.AUTO;
            }
            if (skill.id.equals("signup.autofill")) return PolicyDecision.CONFIRM;
            if (skill.id.equals("connections.manage") || skill.id.equals("vault.manage")) return PolicyDecision.CONFIRM;
            if (skill.risk == Risk.HIGH) return PolicyDecision.CONFIRM;
            return PolicyDecision.AUTO;
        }
    }

    public static final class ExecutorRouter {
        public ExecutorType route(SkillManifest skill, String goal, AmbientEvent event,
                                  int verifiedSuccesses, int priorFailures) {
            String text = normalize(goal + " " + (event == null ? "" : event.type + " " + event.summary));
            if (skill.risk == Risk.CRITICAL || containsAny(text, "otp", "인증번호", "비밀번호", "생체인증")) {
                return ExecutorType.HUMAN;
            }
            if (verifiedSuccesses >= 3 && priorFailures == 0 && skill.executors.contains(ExecutorType.MODEL_FREE)) {
                return ExecutorType.MODEL_FREE;
            }
            if (skill.id.equals("nearby.local")) return ExecutorType.LOCATION_CONTEXT;
            if (skill.id.equals("insurance.monimo.claim") && containsAny(text, "서류", "영수증", "세부내역")) {
                return ExecutorType.LOCAL_OCR;
            }
            if (skill.id.equals("signup.autofill")) return ExecutorType.AUTOFILL;
            if (skill.id.equals("stream.autoplay") && event != null) return ExecutorType.NOTIFICATION_ACTION;
            if (skill.id.equals("software.update.monitor")) return ExecutorType.OFFICIAL_WEB;
            if (skill.id.equals("reservation.orchestrator") && containsAny(text, "전화", "통화")) {
                return priorFailures > 0 ? ExecutorType.SUBSCRIPTION_AI : ExecutorType.PHONE;
            }
            if (priorFailures >= 2 && skill.executors.contains(ExecutorType.MOBILE_CU)) return ExecutorType.MOBILE_CU;
            if (skill.connectorRequired && skill.executors.contains(ExecutorType.DESKTOP_COMPANION)) {
                return ExecutorType.DESKTOP_COMPANION;
            }
            if (skill.executors.contains(ExecutorType.ANDROID_INTENT)) return ExecutorType.ANDROID_INTENT;
            if (skill.executors.contains(ExecutorType.SUBSCRIPTION_AI)) return ExecutorType.SUBSCRIPTION_AI;
            return ExecutorType.HUMAN;
        }
    }

    public static final class CommerceFirewall {
        private static final Set<String> SENSITIVE_KEYS = set(
                "health", "diagnosis", "insurance", "finance", "bank", "family", "message.raw",
                "location.exact", "minor", "disability"
        );

        public boolean allowCommercialRecommendation(
                PersonalContextGraph context,
                List<String> proposedReasonKeys,
                long nowEpochMs
        ) {
            ContextFact consent = context.get("consent.commercial", nowEpochMs);
            if (consent == null || !"true".equalsIgnoreCase(consent.value)) return false;
            for (String key : proposedReasonKeys) {
                String normalized = key.toLowerCase(Locale.ROOT);
                for (String sensitive : SENSITIVE_KEYS) {
                    if (normalized.startsWith(sensitive)) return false;
                }
                ContextFact fact = context.get(key, nowEpochMs);
                if (fact != null && (!fact.mayDriveCommercialRecommendations
                        || fact.sensitivity == Sensitivity.SENSITIVE
                        || fact.sensitivity == Sensitivity.RESTRICTED)) {
                    return false;
                }
            }
            return true;
        }
    }

    public static final class OpportunityEngine {
        private final CommerceFirewall commerceFirewall = new CommerceFirewall();

        public List<Opportunity> evaluate(PersonalContextGraph context, AmbientEvent event, long nowEpochMs) {
            List<Opportunity> result = new ArrayList<>();
            boolean locationEnabled = "true".equalsIgnoreCase(context.value("consent.location", nowEpochMs));
            boolean notificationsEnabled = "true".equalsIgnoreCase(context.value("consent.notifications", nowEpochMs));

            if (event != null && event.actionable && notificationsEnabled) {
                if (event.type.equals("notification.insurance_followup")) {
                    result.add(new Opportunity("insurance:" + event.id, OpportunityKind.URGENT,
                            "보험금 청구에 확인할 일이 있습니다",
                            "추가서류 또는 보완 요청을 기존 청구 건과 연결해 확인합니다.",
                            "insurance.monimo.claim",
                            List.of("보험 관련 알림", "진행 중인 청구 건"), 98, false,
                            nowEpochMs + 3L * 24 * 60 * 60 * 1000));
                } else if (event.type.equals("notification.reservation_cancelled")) {
                    result.add(new Opportunity("reservation:" + event.id, OpportunityKind.URGENT,
                            "취소된 예약의 대체 시간을 찾을까요?",
                            "기존 선호 시간과 장소를 사용해 가능한 대안을 준비합니다.",
                            "reservation.orchestrator",
                            List.of("예약 취소 알림", "기존 예약 선호"), 94, false,
                            nowEpochMs + 24L * 60 * 60 * 1000));
                } else if (event.type.equals("notification.update")) {
                    result.add(new Opportunity("update:" + event.id, OpportunityKind.UPDATE,
                            "설치한 앱의 새 안정판이 있습니다",
                            "공식 릴리스와 설치 버전을 비교해 변경사항을 확인합니다.",
                            "software.update.monitor",
                            List.of("공식 업데이트 알림"), 70, false,
                            nowEpochMs + 7L * 24 * 60 * 60 * 1000));
                } else if (event.type.equals("notification.benefit")) {
                    result.add(new Opportunity("benefit-event:" + event.id, OpportunityKind.BENEFIT,
                            "신청할 수 있는 혜택 안내가 도착했습니다",
                            "개인 자격 프로필과 마감일을 대조해 신청 준비 여부를 확인합니다.",
                            "benefits.autopilot",
                            List.of("기관·서비스 알림", "저장된 자격 프로필"), 86, false,
                            nowEpochMs + 7L * 24 * 60 * 60 * 1000));
                }
            }

            boolean supplementContext = context.hasValueContaining("영양제", nowEpochMs)
                    || context.hasValueContaining("비타민", nowEpochMs)
                    || context.hasValueContaining("약국", nowEpochMs);
            boolean hasCoarseLocation = !context.value("location.coarse", nowEpochMs).isBlank();
            if (locationEnabled && hasCoarseLocation && supplementContext) {
                result.add(new Opportunity("nearby-pharmacy", OpportunityKind.NEARBY,
                        "근처 약국에서 최근 관심 항목을 확인할 수 있습니다",
                        "정확한 위치 기록은 외부 광고망에 보내지 않고 지도 검색에만 사용합니다.",
                        "nearby.local",
                        List.of("최근 영양제·비타민 문맥", "현재의 대략적 위치", "약국 추천 허용"),
                        78, false, nowEpochMs + 90L * 60 * 1000));
            }

            boolean profileReady = !context.value("profile.region", nowEpochMs).isBlank()
                    && !context.value("profile.age_band", nowEpochMs).isBlank();
            if (profileReady) {
                result.add(new Opportunity("benefit-scan", OpportunityKind.BENEFIT,
                        "내 조건에 맞는 혜택을 다시 확인할 때입니다",
                        "거주 지역과 연령대 등 최소 자격 정보로 후보를 찾고 제출 전에는 확인을 받습니다.",
                        "benefits.autopilot",
                        List.of("거주 지역", "연령대", "혜택 검색 동의"), 72, false,
                        nowEpochMs + 24L * 60 * 60 * 1000));
            }

            List<String> commercialKeys = List.of("interest.shopping");
            if (commerceFirewall.allowCommercialRecommendation(context, commercialKeys, nowEpochMs)
                    && !context.value("interest.shopping", nowEpochMs).isBlank()) {
                result.add(new Opportunity("commercial-generic", OpportunityKind.COMMERCIAL,
                        "광고 · 저장한 관심 분야의 지역 혜택",
                        "상업 추천은 별도 동의를 사용하며 건강·금융·메시지·정확한 위치는 사용하지 않습니다.",
                        "nearby.local", List.of("상업 추천 동의", "직접 저장한 쇼핑 관심사"),
                        40, true, nowEpochMs + 6L * 60 * 60 * 1000));
            }

            result.sort(Comparator.comparingInt((Opportunity item) -> item.score).reversed());
            return Collections.unmodifiableList(result);
        }
    }

    public static final class RecipeEngine {
        public List<Recipe> match(AmbientEvent event, List<Recipe> recipes) {
            if (event == null) return List.of();
            List<Recipe> matched = new ArrayList<>();
            for (Recipe recipe : recipes) {
                if (!recipe.enabled || !recipe.triggerType.equals(event.type)) continue;
                boolean all = true;
                for (Map.Entry<String, String> entry : recipe.conditions.entrySet()) {
                    String actual;
                    if (entry.getKey().equals("package")) actual = event.packageName;
                    else if (entry.getKey().equals("summary_contains")) actual = event.summary;
                    else actual = event.entities.getOrDefault(entry.getKey(), "");
                    if (!normalize(actual).contains(normalize(entry.getValue()))) {
                        all = false;
                        break;
                    }
                }
                if (all) matched.add(recipe);
            }
            return Collections.unmodifiableList(matched);
        }
    }

    public static final class AgentKernel {
        private final SkillRegistry registry;
        private final PolicyKernel policyKernel;
        private final ExecutorRouter executorRouter;

        public AgentKernel() {
            this(new SkillRegistry(), new PolicyKernel(), new ExecutorRouter());
        }

        public AgentKernel(SkillRegistry registry, PolicyKernel policyKernel, ExecutorRouter executorRouter) {
            this.registry = registry;
            this.policyKernel = policyKernel;
            this.executorRouter = executorRouter;
        }

        public SkillRegistry registry() {
            return registry;
        }

        public ActionPlan plan(String rawGoal, PersonalContextGraph context, AmbientEvent event,
                               int verifiedSuccesses, int priorFailures, long nowEpochMs) {
            String goal = sanitizeIncoming(rawGoal);
            if (goal.isBlank()) throw new IllegalArgumentException("목표를 입력하세요.");
            List<RankedSkill> ranked = registry.rank(goal, event);
            SkillManifest primary = ranked.isEmpty() ? registry.get("general.delegate") : ranked.get(0).skill;
            if (primary == null) throw new IllegalStateException("등록된 스킬이 없습니다.");
            PolicyDecision policy = policyKernel.decide(primary, goal, context, nowEpochMs);
            ExecutorType executor = executorRouter.route(primary, goal, event, verifiedSuccesses, priorFailures);
            if (policy == PolicyDecision.BLOCK || policy == PolicyDecision.MANUAL_AUTH
                    || policy == PolicyDecision.BIOMETRIC) {
                executor = ExecutorType.HUMAN;
            }

            List<SkillManifest> supporting = new ArrayList<>();
            for (int i = 1; i < ranked.size() && supporting.size() < 2; i++) {
                RankedSkill item = ranked.get(i);
                if (item.score > 0 && !item.skill.id.equals(primary.id)) supporting.add(item.skill);
            }

            List<String> reasons = new ArrayList<>();
            reasons.add("목표와 가장 잘 맞는 스킬: " + primary.name);
            reasons.add("위험도: " + primary.risk.name());
            reasons.add("정책: " + policy.name());
            reasons.add("우선 실행기: " + executor.name());
            if (event != null) reasons.add("연결된 문맥: " + event.type);
            if (primary.connectorRequired) reasons.add("실제 외부 완료에는 공식 연결 또는 Companion이 필요합니다.");

            List<PlanStep> steps = new ArrayList<>();
            steps.add(new PlanStep("context", "현재 문맥과 사용자 허용 범위를 확인합니다",
                    ExecutorType.MODEL_FREE, PolicyDecision.AUTO, "사용한 문맥 키 목록"));
            steps.add(new PlanStep("prepare", primary.name + " 실행에 필요한 입력을 준비합니다",
                    executor, policy, "필수 입력 검증 결과"));
            steps.add(new PlanStep("execute", "허용된 실행 수단으로 작업을 진행합니다",
                    executor, policy, "실행기 영수증 또는 상태"));
            steps.add(new PlanStep("verify", "외부 서비스의 실제 완료 증거를 확인합니다",
                    ExecutorType.MODEL_FREE, PolicyDecision.AUTO, primary.verificationEvidence));

            return new ActionPlan(UUID.randomUUID().toString(), goal, primary, supporting, policy,
                    executor, steps, reasons, primary.connectorRequired,
                    primary.verificationEvidence);
        }
    }

    private static SkillManifest skill(String id, String name, String description, Set<String> capabilities,
                                       Set<String> triggers, Set<String> keywords,
                                       Set<ExecutorType> executors, Risk risk,
                                       String verification, boolean connectorRequired) {
        return new SkillManifest(id, name, description, capabilities, triggers, keywords, executors,
                risk, verification, connectorRequired);
    }

    @SafeVarargs
    private static <T> Set<T> set(T... items) {
        return new LinkedHashSet<>(Arrays.asList(items));
    }

    private static Set<String> immutableSet(Set<String> input) {
        return Collections.unmodifiableSet(new LinkedHashSet<>(input == null ? Set.of() : input));
    }

    private static String requireText(String value, String name) {
        if (value == null || value.isBlank()) throw new IllegalArgumentException(name + " is required");
        return value;
    }

    private static boolean containsAny(String text, String... tokens) {
        for (String token : tokens) {
            if (text.contains(normalize(token))) return true;
        }
        return false;
    }

    private static final Pattern OTP_PATTERN = Pattern.compile("(?<!\\d)\\d{4,8}(?!\\d)");
    private static final Pattern CARD_PATTERN = Pattern.compile("(?<!\\d)(?:\\d[ -]?){13,19}(?!\\d)");
    private static final Pattern ACCOUNT_PATTERN = Pattern.compile("(?<!\\d)\\d{2,6}[- ]\\d{2,6}[- ]\\d{2,8}(?!\\d)");

    public static String sanitizeIncoming(String value) {
        if (value == null) return "";
        String cleaned = value.replace('\u0000', ' ').replaceAll("[\\p{Cntrl}&&[^\\r\\n\\t]]", " ");
        if (containsAny(normalize(cleaned), "인증번호", "otp", "verificationcode", "보안코드")) {
            cleaned = OTP_PATTERN.matcher(cleaned).replaceAll("[인증정보 숨김]");
        }
        cleaned = CARD_PATTERN.matcher(cleaned).replaceAll("[금융번호 숨김]");
        cleaned = ACCOUNT_PATTERN.matcher(cleaned).replaceAll("[계좌정보 숨김]");
        return cleaned.trim().replaceAll("[ \\t]{2,}", " ");
    }

    public static boolean looksSensitive(String value) {
        String normalized = normalize(value);
        return containsAny(normalized, "비밀번호", "otp", "인증번호", "보안카드", "cvv", "cvc",
                "복구코드", "시드문구", "개인키") || CARD_PATTERN.matcher(value == null ? "" : value).find();
    }

    public static String normalize(String value) {
        if (value == null) return "";
        String normalized = Normalizer.normalize(value, Normalizer.Form.NFKC).toLowerCase(Locale.ROOT);
        return normalized.replaceAll("[\\s\\p{Punct}·ㆍ]+", "");
    }

    public static long now() {
        return Instant.now().toEpochMilli();
    }
}
