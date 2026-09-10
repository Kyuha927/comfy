package com.lifeagent.unified.core;

import org.junit.Test;

import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

public final class AgentCoreTest {
    @Test
    public void reservationGoalSelectsReservationSkill() {
        AgentCore.AgentKernel kernel = new AgentCore.AgentKernel();
        AgentCore.ActionPlan plan = kernel.plan(
                "금요일 오후 정형외과를 전화로 예약해줘",
                new AgentCore.PersonalContextGraph(), null, 0, 0, 1000L);
        assertEquals("reservation.orchestrator", plan.primarySkill.id);
        assertEquals(AgentCore.ExecutorType.PHONE, plan.primaryExecutor);
        assertEquals(AgentCore.PolicyDecision.AUTO, plan.policy);
    }

    @Test
    public void transferAlwaysRequiresDeviceAuthentication() {
        AgentCore.AgentKernel kernel = new AgentCore.AgentKernel();
        AgentCore.ActionPlan plan = kernel.plan(
                "엄마에게 5만원 송금 초안 만들어줘",
                new AgentCore.PersonalContextGraph(), null, 0, 0, 1000L);
        assertEquals("transfer.safe", plan.primarySkill.id);
        assertEquals(AgentCore.PolicyDecision.BIOMETRIC, plan.policy);
        assertEquals(AgentCore.ExecutorType.HUMAN, plan.primaryExecutor);
    }

    @Test
    public void authenticationSecretRoutesToManualAuth() {
        AgentCore.AgentKernel kernel = new AgentCore.AgentKernel();
        AgentCore.ActionPlan plan = kernel.plan(
                "인증번호를 입력해서 회원가입해줘",
                new AgentCore.PersonalContextGraph(), null, 0, 0, 1000L);
        assertEquals(AgentCore.PolicyDecision.MANUAL_AUTH, plan.policy);
        assertEquals(AgentCore.ExecutorType.HUMAN, plan.primaryExecutor);
    }

    @Test
    public void unsafeBypassIsBlocked() {
        AgentCore.AgentKernel kernel = new AgentCore.AgentKernel();
        AgentCore.ActionPlan plan = kernel.plan(
                "동의없이 잠금해제우회 해줘",
                new AgentCore.PersonalContextGraph(), null, 0, 0, 1000L);
        assertEquals(AgentCore.PolicyDecision.BLOCK, plan.policy);
    }

    @Test
    public void repeatedVerifiedStreamCanRunModelFree() {
        AgentCore.AgentKernel kernel = new AgentCore.AgentKernel();
        AgentCore.AmbientEvent event = new AgentCore.AmbientEvent(
                "e1", "notification", "notification.stream_live",
                "감스트 방송을 시작했습니다", "kr.co.nowcom.mobile.afreeca",
                1000L, Map.of(), AgentCore.Sensitivity.PERSONAL, true);
        AgentCore.ActionPlan plan = kernel.plan(
                "감스트 방송 자동 실행", new AgentCore.PersonalContextGraph(),
                event, 3, 0, 1000L);
        assertEquals("stream.autoplay", plan.primarySkill.id);
        assertEquals(AgentCore.ExecutorType.MODEL_FREE, plan.primaryExecutor);
    }

    @Test
    public void contextGraphPurgesExpiredFacts() {
        AgentCore.PersonalContextGraph graph = new AgentCore.PersonalContextGraph();
        graph.put(new AgentCore.ContextFact("temporary", "value",
                AgentCore.Sensitivity.PERSONAL, 100L, true, false));
        assertNull(graph.get("temporary", 101L));
        assertTrue(graph.snapshot(101L).isEmpty());
    }

    @Test
    public void healthAndLocationCreateNonCommercialPharmacyOpportunity() {
        AgentCore.PersonalContextGraph graph = new AgentCore.PersonalContextGraph();
        graph.put(new AgentCore.ContextFact("consent.location", "true",
                AgentCore.Sensitivity.PERSONAL, 0L, true, false));
        graph.put(new AgentCore.ContextFact("location.coarse", "37.500,127.000",
                AgentCore.Sensitivity.SENSITIVE, 0L, true, false));
        graph.put(new AgentCore.ContextFact("context.health_interest", "비타민과 영양제",
                AgentCore.Sensitivity.SENSITIVE, 0L, true, false));
        List<AgentCore.Opportunity> opportunities = new AgentCore.OpportunityEngine().evaluate(graph, null, 1000L);
        AgentCore.Opportunity pharmacy = opportunities.stream()
                .filter(item -> item.id.equals("nearby-pharmacy"))
                .findFirst().orElseThrow();
        assertEquals(AgentCore.OpportunityKind.NEARBY, pharmacy.kind);
        assertFalse(pharmacy.commercial);
    }

    @Test
    public void commerceFirewallRejectsSensitiveReasonEvenWithConsent() {
        AgentCore.PersonalContextGraph graph = new AgentCore.PersonalContextGraph();
        graph.put(new AgentCore.ContextFact("consent.commercial", "true",
                AgentCore.Sensitivity.PERSONAL, 0L, true, false));
        graph.put(new AgentCore.ContextFact("health.condition", "통풍",
                AgentCore.Sensitivity.SENSITIVE, 0L, true, false));
        assertFalse(new AgentCore.CommerceFirewall().allowCommercialRecommendation(
                graph, List.of("health.condition"), 1000L));
    }

    @Test
    public void commerceFirewallAllowsExplicitNonSensitiveInterest() {
        AgentCore.PersonalContextGraph graph = new AgentCore.PersonalContextGraph();
        graph.put(new AgentCore.ContextFact("consent.commercial", "true",
                AgentCore.Sensitivity.PERSONAL, 0L, true, false));
        graph.put(new AgentCore.ContextFact("interest.shopping", "러닝화",
                AgentCore.Sensitivity.PERSONAL, 0L, true, true));
        assertTrue(new AgentCore.CommerceFirewall().allowCommercialRecommendation(
                graph, List.of("interest.shopping"), 1000L));
    }

    @Test
    public void actionableInsuranceNotificationCreatesUrgentOpportunity() {
        AgentCore.PersonalContextGraph graph = new AgentCore.PersonalContextGraph();
        graph.put(new AgentCore.ContextFact("consent.notifications", "true",
                AgentCore.Sensitivity.PERSONAL, 0L, true, false));
        AgentCore.AmbientEvent event = new AgentCore.AmbientEvent(
                "insurance1", "notification", "notification.insurance_followup",
                "추가서류가 필요합니다", "com.kakao.talk", 1000L, Map.of(),
                AgentCore.Sensitivity.SENSITIVE, true);
        List<AgentCore.Opportunity> opportunities = new AgentCore.OpportunityEngine().evaluate(graph, event, 1000L);
        assertEquals(AgentCore.OpportunityKind.URGENT, opportunities.get(0).kind);
        assertEquals("insurance.monimo.claim", opportunities.get(0).skillId);
    }

    @Test
    public void recipeRequiresAllConditions() {
        AgentCore.Recipe recipe = new AgentCore.Recipe("r", "감스트 방송", "notification.stream_live",
                Map.of("package", "nowcom", "summary_contains", "감스트"),
                "stream.autoplay", AgentCore.PolicyDecision.AUTO, "채널", true);
        AgentCore.AmbientEvent event = new AgentCore.AmbientEvent(
                "e", "notification", "notification.stream_live", "감스트 생방송 시작",
                "kr.co.nowcom.mobile.afreeca", 1000L, Map.of(),
                AgentCore.Sensitivity.PERSONAL, true);
        assertEquals(1, new AgentCore.RecipeEngine().match(event, List.of(recipe)).size());
    }

    @Test
    public void taskGraphRefusesFinalCompletionWithoutEvidence() {
        AgentCore.ActionPlan plan = new AgentCore.AgentKernel().plan(
                "예약해줘", new AgentCore.PersonalContextGraph(), null, 0, 0, 1000L);
        AgentCore.TaskGraph graph = new AgentCore.TaskGraph(plan, 1000L);
        for (int i = 0; i < plan.steps.size(); i++) graph.markActiveVerified("", 1001L + i);
        assertEquals(AgentCore.TaskStatus.VERIFYING, graph.status);
    }

    @Test
    public void sanitizerRemovesAuthenticationAndFinancialNumbers() {
        String sanitized = AgentCore.sanitizeIncoming(
                "인증번호 123456, 카드 4111 1111 1111 1111");
        assertFalse(sanitized.contains("123456"));
        assertFalse(sanitized.contains("4111"));
        assertTrue(sanitized.contains("숨김"));
    }
}
