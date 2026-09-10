package com.lifeagent.unified.core;

import android.content.Context;

import com.lifeagent.unified.data.AgentRepository;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Android-facing orchestrator. Every entry point goes through the same kernel and repository. */
public final class AgentRuntime {
    private static volatile AgentRuntime instance;

    private final Context context;
    private final AgentCore.AgentKernel kernel;
    private final AgentCore.OpportunityEngine opportunityEngine;
    private final AgentCore.RecipeEngine recipeEngine;
    private final AgentRepository repository;
    private volatile AgentCore.ActionPlan lastPlan;

    private AgentRuntime(Context context) {
        this.context = context.getApplicationContext();
        this.kernel = new AgentCore.AgentKernel();
        this.opportunityEngine = new AgentCore.OpportunityEngine();
        this.recipeEngine = new AgentCore.RecipeEngine();
        this.repository = new AgentRepository(this.context);
    }

    public static AgentRuntime get(Context context) {
        AgentRuntime local = instance;
        if (local == null) {
            synchronized (AgentRuntime.class) {
                local = instance;
                if (local == null) {
                    local = new AgentRuntime(context);
                    instance = local;
                }
            }
        }
        return local;
    }

    public AgentRepository repository() {
        return repository;
    }

    public AgentCore.SkillRegistry skills() {
        return kernel.registry();
    }

    public AgentCore.ActionPlan plan(String goal) {
        long now = AgentCore.now();
        AgentCore.PersonalContextGraph graph = repository.loadContextGraph(now);
        AgentCore.AmbientEvent event = repository.latestEvent(now);
        List<AgentCore.RankedSkill> ranked = kernel.registry().rank(goal, event);
        String skillId = ranked.isEmpty() ? "general.delegate" : ranked.get(0).skill.id;
        int successes = repository.getPlainString("skill_successes_" + skillId, "0").isBlank()
                ? 0 : parseInt(repository.getPlainString("skill_successes_" + skillId, "0"));
        int failures = repository.getPlainString("skill_failures_" + skillId, "0").isBlank()
                ? 0 : parseInt(repository.getPlainString("skill_failures_" + skillId, "0"));
        lastPlan = kernel.plan(goal, graph, event, successes, failures, now);
        return lastPlan;
    }

    public String acceptPlan(AgentCore.ActionPlan plan) {
        if (plan == null) throw new IllegalArgumentException("계획이 없습니다.");
        return repository.createTask(plan, AgentCore.now());
    }

    public AgentCore.ActionPlan lastPlan() {
        return lastPlan;
    }

    public List<AgentCore.Opportunity> opportunities() {
        long now = AgentCore.now();
        AgentCore.PersonalContextGraph graph = repository.loadContextGraph(now);
        AgentCore.AmbientEvent event = repository.latestEvent(now);
        return opportunityEngine.evaluate(graph, event, now);
    }

    public List<String> handleAmbientEvent(AgentCore.AmbientEvent event) {
        long now = AgentCore.now();
        repository.recordEvent(event, now);
        List<String> createdTaskIds = new ArrayList<>();
        for (AgentCore.Recipe recipe : recipeEngine.match(event, repository.listRecipes())) {
            AgentCore.SkillManifest skill = kernel.registry().get(recipe.skillId);
            if (skill == null) continue;
            String goal = recipe.name + ": " + event.summary;
            AgentCore.PersonalContextGraph graph = repository.loadContextGraph(now);
            AgentCore.ActionPlan plan = kernel.plan(goal, graph, event, 0, 0, now);
            if (!plan.primarySkill.id.equals(skill.id)) {
                plan = forceSkillPlan(goal, skill, graph, event, now);
            }
            createdTaskIds.add(repository.createTask(plan, now));
        }
        return Collections.unmodifiableList(createdTaskIds);
    }

    public AgentCore.ActionPlan planOpportunity(AgentCore.Opportunity opportunity) {
        AgentCore.SkillManifest skill = kernel.registry().get(opportunity.skillId);
        if (skill == null) return plan(opportunity.title);
        long now = AgentCore.now();
        return forceSkillPlan(opportunity.title + ". " + opportunity.summary,
                skill, repository.loadContextGraph(now), repository.latestEvent(now), now);
    }

    public void recordSkillSuccess(String skillId) {
        String key = "skill_successes_" + skillId;
        int current = parseInt(repository.getPlainString(key, "0"));
        repository.setPlainString(key, Integer.toString(Math.min(1000, current + 1)));
        repository.setPlainString("skill_failures_" + skillId, "0");
    }

    public void recordSkillFailure(String skillId) {
        String key = "skill_failures_" + skillId;
        int current = parseInt(repository.getPlainString(key, "0"));
        repository.setPlainString(key, Integer.toString(Math.min(100, current + 1)));
    }

    private AgentCore.ActionPlan forceSkillPlan(String goal, AgentCore.SkillManifest skill,
                                                AgentCore.PersonalContextGraph graph,
                                                AgentCore.AmbientEvent event, long now) {
        AgentCore.PolicyDecision policy = new AgentCore.PolicyKernel().decide(skill, goal, graph, now);
        AgentCore.ExecutorType executor = new AgentCore.ExecutorRouter().route(skill, goal, event, 0, 0);
        if (policy == AgentCore.PolicyDecision.BLOCK
                || policy == AgentCore.PolicyDecision.MANUAL_AUTH
                || policy == AgentCore.PolicyDecision.BIOMETRIC) {
            executor = AgentCore.ExecutorType.HUMAN;
        }
        List<AgentCore.PlanStep> steps = List.of(
                new AgentCore.PlanStep("context", "추천 근거와 허용 범위를 확인합니다",
                        AgentCore.ExecutorType.MODEL_FREE, AgentCore.PolicyDecision.AUTO,
                        "사용한 문맥 키 목록"),
                new AgentCore.PlanStep("prepare", skill.name + " 입력을 준비합니다",
                        executor, policy, "필수 입력 검증"),
                new AgentCore.PlanStep("execute", "허용된 실행기로 작업을 진행합니다",
                        executor, policy, "실행 상태 또는 영수증"),
                new AgentCore.PlanStep("verify", "실제 완료 증거를 확인합니다",
                        AgentCore.ExecutorType.MODEL_FREE, AgentCore.PolicyDecision.AUTO,
                        skill.verificationEvidence)
        );
        return new AgentCore.ActionPlan(null, goal, skill, List.of(), policy, executor, steps,
                List.of("기회 엔진이 선택한 스킬: " + skill.name,
                        "정책 커널 판정: " + policy.name(),
                        "실행기 라우팅: " + executor.name()),
                skill.connectorRequired, skill.verificationEvidence);
    }

    private static int parseInt(String raw) {
        try {
            return Integer.parseInt(raw);
        } catch (Exception ignored) {
            return 0;
        }
    }
}
