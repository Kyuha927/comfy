from __future__ import annotations

import unittest

from wbcp.errors import ControlPlaneError, FailureCode
from wbcp.mock_browser import MockBrowserAdapter
from wbcp.models import ActionRequest, ApprovalKind, AuthoritySource, JobState, RiskTier

from helpers import build_stack


class OrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = build_stack()
        self.browser = MockBrowserAdapter()

    def tearDown(self) -> None:
        self.stack.cleanup()

    def permit_for(
        self,
        request: ActionRequest,
        risk: RiskTier,
        *,
        max_calls: int = 1,
        max_cost: float = 0.0,
    ) -> str:
        return self.stack.permits.issue(
            subject="host-model-attested",
            session_id=request.session_id,
            allowed_actions=[request.action_type],
            exact_hosts=["example.com"],
            risk_ceiling=risk,
            max_calls=max_calls,
            max_cost=max_cost,
            currency=request.currency or "USD",
        )

    def test_read_only_happy_path(self) -> None:
        request = ActionRequest(
            session_id="s1",
            idempotency_key="read-1",
            action_type="inspect",
            target_url="https://example.com/",
        )
        pre = self.stack.orchestrator.preflight(request)
        self.assertEqual(pre.job.state, JobState.PREFLIGHTED)
        authorized = self.stack.orchestrator.authorize(
            pre.job.job_id,
            permit_token=self.permit_for(request, RiskTier.R0_READ_ONLY),
        )
        self.assertEqual(authorized.state, JobState.AUTHORIZED)
        receipt = self.stack.orchestrator.run(pre.job.job_id, self.browser)
        self.assertEqual(receipt.state, JobState.SUCCEEDED)
        self.assertTrue(self.stack.evidence.verify().valid)

    def test_write_requires_finite_permit_before_execution(self) -> None:
        request = ActionRequest(
            session_id="s1",
            idempotency_key="write-1",
            action_type="type",
            target_url="https://example.com/",
            payload={"field": "name", "value": "Ada"},
            expected={"field_equals": {"name": "Ada"}},
        )
        pre = self.stack.orchestrator.preflight(request)
        self.assertEqual(pre.job.state, JobState.AWAITING_APPROVAL)
        with self.assertRaises(ControlPlaneError) as ctx:
            self.stack.orchestrator.run(pre.job.job_id, self.browser)
        self.assertEqual(
            ctx.exception.code,
            FailureCode.BLOCKED_PENDING_FINITE_WRITE_PERMIT_OR_EXPLICIT_SESSION_AUTHORIZATION,
        )
        self.stack.orchestrator.authorize(
            pre.job.job_id,
            permit_token=self.permit_for(request, RiskTier.R2_REMOTE_REVERSIBLE),
        )
        receipt = self.stack.orchestrator.run(pre.job.job_id, self.browser)
        self.assertEqual(receipt.state, JobState.SUCCEEDED)
        self.assertEqual(self.browser.state.fields["name"], "Ada")

    def test_consequential_action_requires_one_shot_approval(self) -> None:
        request = ActionRequest(
            session_id="s1",
            idempotency_key="publish-1",
            action_type="publish",
            target_url="https://example.com/",
            expected={"published": True},
            reversible=True,
        )
        pre = self.stack.orchestrator.preflight(request)
        permit = self.permit_for(request, RiskTier.R3_CONSEQUENTIAL)
        with self.assertRaises(ControlPlaneError) as ctx:
            self.stack.orchestrator.authorize(pre.job.job_id, permit_token=permit)
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_PENDING_HIGH_IMPACT_APPROVAL)

        approval = self.stack.approvals.issue(
            job_id=pre.job.job_id,
            action_digest=pre.job.decision.action_digest,
            approval_kind=ApprovalKind.HIGH_IMPACT,
            approvers=["human-owner"],
        )
        # The failed approval attempt does not consume the finite permit; the
        # final authorization consumes permit + approval atomically.
        self.stack.orchestrator.authorize(
            pre.job.job_id,
            permit_token=permit,
            approval_token=approval,
        )
        receipt = self.stack.orchestrator.run(pre.job.job_id, self.browser)
        self.assertEqual(receipt.state, JobState.SUCCEEDED)
        self.assertTrue(self.browser.state.published)

    def test_failed_approval_does_not_burn_finite_permit(self) -> None:
        first = ActionRequest(
            session_id="s1",
            idempotency_key="publish-missing-approval",
            action_type="publish",
            target_url="https://example.com/",
            expected={"published": True},
        )
        first_pre = self.stack.orchestrator.preflight(first)
        permit = self.permit_for(first, RiskTier.R3_CONSEQUENTIAL, max_calls=1)
        with self.assertRaises(ControlPlaneError) as ctx:
            self.stack.orchestrator.authorize(first_pre.job.job_id, permit_token=permit)
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_PENDING_HIGH_IMPACT_APPROVAL)

        second = ActionRequest(
            session_id="s1",
            idempotency_key="publish-valid-after-failure",
            action_type="publish",
            target_url="https://example.com/",
            expected={"published": True},
        )
        second_pre = self.stack.orchestrator.preflight(second)
        approval = self.stack.approvals.issue(
            job_id=second_pre.job.job_id,
            action_digest=second_pre.job.decision.action_digest,
            approval_kind=ApprovalKind.HIGH_IMPACT,
            approvers=["human-owner"],
        )
        authorized = self.stack.orchestrator.authorize(
            second_pre.job.job_id, permit_token=permit, approval_token=approval
        )
        self.assertEqual(authorized.state, JobState.AUTHORIZED)

    def test_consequential_action_demands_all_three_signals_and_rolls_back(self) -> None:
        request = ActionRequest(
            session_id="s1",
            idempotency_key="publish-fail",
            action_type="publish",
            target_url="https://example.com/",
            payload={"simulate_pixel_failure": True},
            expected={"published": True},
            reversible=True,
        )
        pre = self.stack.orchestrator.preflight(request)
        permit = self.permit_for(request, RiskTier.R3_CONSEQUENTIAL)
        approval = self.stack.approvals.issue(
            job_id=pre.job.job_id,
            action_digest=pre.job.decision.action_digest,
            approval_kind=ApprovalKind.HIGH_IMPACT,
            approvers=["human-owner"],
        )
        self.stack.orchestrator.authorize(
            pre.job.job_id, permit_token=permit, approval_token=approval
        )
        receipt = self.stack.orchestrator.run(pre.job.job_id, self.browser)
        self.assertEqual(receipt.state, JobState.ROLLED_BACK)
        self.assertFalse(self.browser.state.published)
        self.assertEqual(receipt.failure_code, FailureCode.BLOCKED_POSTCONDITION_UNVERIFIED.value)

    def test_failed_verification_with_failed_rollback_is_quarantined(self) -> None:
        self.browser.fail_rollback = True
        request = ActionRequest(
            session_id="s1",
            idempotency_key="write-quarantine",
            action_type="type",
            target_url="https://example.com/",
            payload={
                "field": "name",
                "value": "Ada",
                "simulate_dom_failure": True,
                "simulate_pixel_failure": True,
            },
            expected={"field_equals": {"name": "Ada"}},
            reversible=True,
        )
        pre = self.stack.orchestrator.preflight(request)
        self.stack.orchestrator.authorize(
            pre.job.job_id,
            permit_token=self.permit_for(request, RiskTier.R2_REMOTE_REVERSIBLE),
        )
        receipt = self.stack.orchestrator.run(pre.job.job_id, self.browser)
        self.assertEqual(receipt.state, JobState.QUARANTINED)
        self.assertEqual(
            receipt.failure_code,
            FailureCode.BLOCKED_ROLLBACK_UNAVAILABLE_FOR_REQUIRED_REVERSIBILITY.value,
        )

    def test_stale_page_revision_is_blocked_before_action(self) -> None:
        request = ActionRequest(
            session_id="s1",
            idempotency_key="stale-1",
            action_type="navigate",
            target_url="https://example.com/new",
            page_revision="rev-999",
        )
        pre = self.stack.orchestrator.preflight(request)
        self.stack.orchestrator.authorize(
            pre.job.job_id,
            permit_token=self.permit_for(request, RiskTier.R1_LOCAL_REVERSIBLE),
        )
        receipt = self.stack.orchestrator.run(pre.job.job_id, self.browser)
        self.assertEqual(receipt.state, JobState.BLOCKED)
        self.assertEqual(receipt.failure_code, FailureCode.BLOCKED_STALE_PAGE_REVISION.value)
        self.assertNotEqual(self.browser.state.url, "https://example.com/new")

    def test_execution_exception_is_quarantined_without_success_claim(self) -> None:
        request = ActionRequest(
            session_id="s1",
            idempotency_key="exec-fail",
            action_type="navigate",
            target_url="https://example.com/new",
            payload={"simulate_execution_failure": True},
        )
        pre = self.stack.orchestrator.preflight(request)
        self.stack.orchestrator.authorize(
            pre.job.job_id,
            permit_token=self.permit_for(request, RiskTier.R1_LOCAL_REVERSIBLE),
        )
        receipt = self.stack.orchestrator.run(pre.job.job_id, self.browser)
        self.assertEqual(receipt.state, JobState.QUARANTINED)
        self.assertEqual(receipt.failure_code, FailureCode.FAILED_BROWSER_EXECUTION.value)

    def test_same_idempotent_request_returns_existing_terminal_receipt(self) -> None:
        request = ActionRequest(
            session_id="s1",
            idempotency_key="idem-1",
            action_type="inspect",
            target_url="https://example.com/",
        )
        pre = self.stack.orchestrator.preflight(request)
        self.stack.orchestrator.authorize(
            pre.job.job_id,
            permit_token=self.permit_for(request, RiskTier.R0_READ_ONLY),
        )
        first = self.stack.orchestrator.run(pre.job.job_id, self.browser)
        duplicate = self.stack.orchestrator.preflight(request)
        second = self.stack.orchestrator.run(duplicate.job.job_id, self.browser)
        self.assertFalse(duplicate.created)
        self.assertEqual(first.job_id, second.job_id)
        self.assertEqual(first.evidence_root, second.evidence_root)

    def test_untrusted_web_content_is_terminally_blocked_at_preflight(self) -> None:
        request = ActionRequest(
            session_id="s1",
            idempotency_key="web-authority",
            action_type="navigate",
            target_url="https://example.com/",
            authority_source=AuthoritySource.WEB_CONTENT,
        )
        pre = self.stack.orchestrator.preflight(request)
        self.assertEqual(pre.job.state, JobState.BLOCKED)
        self.assertEqual(
            pre.job.error_code, FailureCode.BLOCKED_PROMPT_INJECTION_SUSPECTED.value
        )

    def test_unknown_paid_cost_is_blocked_before_permit(self) -> None:
        request = ActionRequest(
            session_id="s1",
            idempotency_key="unknown-cost",
            action_type="start_paid_generation",
            target_url="https://example.com/",
        )
        pre = self.stack.orchestrator.preflight(request)
        self.assertEqual(pre.job.state, JobState.BLOCKED)
        self.assertEqual(
            pre.job.error_code, FailureCode.BLOCKED_COST_UNKNOWN_OR_BUDGET_EXCEEDED.value
        )

    def test_paid_generation_cost_is_enforced_at_policy_and_permit(self) -> None:
        request = ActionRequest(
            session_id="s1",
            idempotency_key="paid-1",
            action_type="start_paid_generation",
            target_url="https://example.com/",
            estimated_cost=2.5,
            currency="USD",
            expected={"resource_created": True},
        )
        pre = self.stack.orchestrator.preflight(request)
        permit = self.permit_for(
            request, RiskTier.R3_CONSEQUENTIAL, max_cost=2.5
        )
        approval = self.stack.approvals.issue(
            job_id=pre.job.job_id,
            action_digest=pre.job.decision.action_digest,
            approval_kind=ApprovalKind.HIGH_IMPACT,
            approvers=["human-owner"],
        )
        self.stack.orchestrator.authorize(
            pre.job.job_id, permit_token=permit, approval_token=approval
        )
        receipt = self.stack.orchestrator.run(pre.job.job_id, self.browser)
        self.assertEqual(receipt.state, JobState.SUCCEEDED)
        self.assertIn("provider_receipt", receipt.result["output"])


if __name__ == "__main__":
    unittest.main()


class ProviderReceiptRegressionTests(unittest.TestCase):
    def test_r3_cannot_succeed_with_network_boolean_but_no_provider_receipt(self) -> None:
        from wbcp.models import BrowserSnapshot, ExecutionResult, SignalBundle

        class MissingReceiptAdapter(MockBrowserAdapter):
            def execute(self, request):
                result = super().execute(request)
                return ExecutionResult(
                    before=result.before,
                    after=result.after,
                    signals=SignalBundle(
                        dom_ok=True,
                        pixel_ok=True,
                        network_ok=True,
                        provider_receipt=None,
                    ),
                    output=result.output,
                    rollback_token=None,
                )

        stack = build_stack()
        try:
            request = ActionRequest(
                session_id="session",
                idempotency_key="missing-receipt",
                action_type="submit",
                target_url="https://example.com/form",
                expected={"submitted": True},
                reversible=False,
            )
            preflight = stack.orchestrator.preflight(request)
            permit = stack.permits.issue(
                subject="host-model-attested",
                session_id="session",
                allowed_actions=["submit"],
                exact_hosts=["example.com"],
                risk_ceiling=RiskTier.R3_CONSEQUENTIAL,
                max_calls=1,
            )
            approval = stack.approvals.issue(
                job_id=preflight.job.job_id,
                action_digest=preflight.job.decision.action_digest,
                approval_kind=ApprovalKind.HIGH_IMPACT,
                approvers=["owner"],
            )
            stack.orchestrator.authorize(
                preflight.job.job_id,
                permit_token=permit,
                approval_token=approval,
            )
            receipt = stack.orchestrator.run(preflight.job.job_id, MissingReceiptAdapter())
            self.assertEqual(receipt.state, JobState.QUARANTINED)
            self.assertEqual(receipt.failure_code, "BLOCKED_POSTCONDITION_UNVERIFIED")
        finally:
            stack.cleanup()
