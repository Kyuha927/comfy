from __future__ import annotations

import base64
import time
import unittest

from wbcp.errors import ControlPlaneError, FailureCode
from wbcp.models import ActionRequest, ApprovalKind, RiskTier
from wbcp.permits import ApprovalAuthority, PermitAuthority, PermitRegistry


def action(
    *,
    key: str = "k1",
    action_type: str = "navigate",
    host: str = "example.com",
    cost: float | None = None,
    currency: str | None = None,
) -> ActionRequest:
    return ActionRequest(
        session_id="session-1",
        idempotency_key=key,
        action_type=action_type,
        target_url=f"https://{host}/",
        estimated_cost=cost,
        currency=currency,
    )


class PermitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = PermitRegistry()
        self.auth = PermitAuthority(b"P" * 32, self.registry)
        self.approvals = ApprovalAuthority(b"A" * 32, self.registry)

    def tearDown(self) -> None:
        self.registry.close()

    def issue(self, **overrides) -> str:
        values = dict(
            subject="host",
            session_id="session-1",
            allowed_actions=["navigate"],
            exact_hosts=["example.com"],
            risk_ceiling=RiskTier.R1_LOCAL_REVERSIBLE,
            max_calls=2,
            max_cost=0.0,
            currency="USD",
            ttl_seconds=300,
        )
        values.update(overrides)
        return self.auth.issue(**values)

    def test_valid_permit_is_consumed(self) -> None:
        result = self.auth.validate_and_consume(
            self.issue(),
            request=action(),
            risk=RiskTier.R1_LOCAL_REVERSIBLE,
            expected_subject="host",
        )
        self.assertEqual(result.usage["calls"], 1)
        self.assertFalse(result.usage["replayed"])

    def test_same_idempotency_key_replays_without_second_consumption(self) -> None:
        token = self.issue(max_calls=1)
        first = self.auth.validate_and_consume(
            token,
            request=action(),
            risk=RiskTier.R1_LOCAL_REVERSIBLE,
            expected_subject="host",
        )
        second = self.auth.validate_and_consume(
            token,
            request=action(),
            risk=RiskTier.R1_LOCAL_REVERSIBLE,
            expected_subject="host",
        )
        self.assertEqual(first.usage["calls"], 1)
        self.assertTrue(second.usage["replayed"])

    def test_call_limit_is_hard(self) -> None:
        token = self.issue(max_calls=1)
        self.auth.validate_and_consume(
            token,
            request=action(key="first"),
            risk=RiskTier.R1_LOCAL_REVERSIBLE,
            expected_subject="host",
        )
        with self.assertRaises(ControlPlaneError) as ctx:
            self.auth.validate_and_consume(
                token,
                request=action(key="second"),
                risk=RiskTier.R1_LOCAL_REVERSIBLE,
                expected_subject="host",
            )
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_PERMIT_EXHAUSTED)

    def test_tamper_is_detected(self) -> None:
        token = self.issue()
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with self.assertRaises(ControlPlaneError) as ctx:
            self.auth.validate_and_consume(
                tampered,
                request=action(),
                risk=RiskTier.R1_LOCAL_REVERSIBLE,
                expected_subject="host",
            )
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_PERMIT_INVALID)


    def test_noncanonical_base64url_signature_alias_is_rejected(self) -> None:
        token = self.issue()
        header, payload, signature = token.split(".")
        raw = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        alias = None
        for char in alphabet:
            candidate = signature[:-1] + char
            if candidate == signature:
                continue
            decoded = base64.urlsafe_b64decode(candidate + "=" * (-len(candidate) % 4))
            if decoded == raw:
                alias = candidate
                break
        self.assertIsNotNone(alias, "Expected an alternate noncanonical Base64url spelling")
        with self.assertRaises(ControlPlaneError) as ctx:
            self.auth.validate_and_consume(
                f"{header}.{payload}.{alias}",
                request=action(),
                risk=RiskTier.R1_LOCAL_REVERSIBLE,
                expected_subject="host",
            )
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_PERMIT_INVALID)

    def test_expired_permit_is_rejected(self) -> None:
        token = self.issue(ttl_seconds=-1)
        with self.assertRaises(ControlPlaneError) as ctx:
            self.auth.validate_and_consume(
                token,
                request=action(),
                risk=RiskTier.R1_LOCAL_REVERSIBLE,
                expected_subject="host",
                now=time.time(),
            )
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_PERMIT_EXPIRED)

    def test_action_host_session_subject_and_risk_are_bound(self) -> None:
        token = self.issue()
        cases = [
            (action(action_type="inspect"), RiskTier.R0_READ_ONLY, "host"),
            (action(host="api.example.com"), RiskTier.R1_LOCAL_REVERSIBLE, "host"),
            (action(), RiskTier.R2_REMOTE_REVERSIBLE, "host"),
            (action(), RiskTier.R1_LOCAL_REVERSIBLE, "other"),
        ]
        for request, risk, subject in cases:
            with self.subTest(request=request, risk=risk, subject=subject):
                with self.assertRaises(ControlPlaneError) as ctx:
                    self.auth.validate_and_consume(
                        token,
                        request=request,
                        risk=risk,
                        expected_subject=subject,
                    )
                self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_PERMIT_SCOPE_MISMATCH)

    def test_cost_cap_and_currency_are_bound(self) -> None:
        token = self.issue(
            allowed_actions=["start_paid_generation"],
            risk_ceiling=RiskTier.R3_CONSEQUENTIAL,
            max_cost=5.0,
        )
        self.auth.validate_and_consume(
            token,
            request=action(
                key="cost1",
                action_type="start_paid_generation",
                cost=3.0,
                currency="USD",
            ),
            risk=RiskTier.R3_CONSEQUENTIAL,
            expected_subject="host",
        )
        with self.assertRaises(ControlPlaneError) as ctx:
            self.auth.validate_and_consume(
                token,
                request=action(
                    key="cost2",
                    action_type="start_paid_generation",
                    cost=3.0,
                    currency="USD",
                ),
                risk=RiskTier.R3_CONSEQUENTIAL,
                expected_subject="host",
            )
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_PERMIT_EXHAUSTED)

    def test_high_impact_approval_is_job_and_digest_bound_and_one_shot(self) -> None:
        token = self.approvals.issue(
            job_id="job-1",
            action_digest="digest-1",
            approval_kind=ApprovalKind.HIGH_IMPACT,
            approvers=["user-1"],
        )
        claims = self.approvals.validate_and_consume(
            token,
            job_id="job-1",
            action_digest="digest-1",
            required_kind=ApprovalKind.HIGH_IMPACT,
        )
        self.assertEqual(claims["approvers"], ["user-1"])
        with self.assertRaises(ControlPlaneError) as ctx:
            self.approvals.validate_and_consume(
                token,
                job_id="job-1",
                action_digest="digest-1",
                required_kind=ApprovalKind.HIGH_IMPACT,
            )
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_APPROVAL_REPLAY)

    def test_approval_cannot_be_rebound(self) -> None:
        token = self.approvals.issue(
            job_id="job-1",
            action_digest="digest-1",
            approval_kind=ApprovalKind.HIGH_IMPACT,
            approvers=["user-1"],
        )
        with self.assertRaises(ControlPlaneError) as ctx:
            self.approvals.validate_and_consume(
                token,
                job_id="job-2",
                action_digest="digest-1",
                required_kind=ApprovalKind.HIGH_IMPACT,
            )
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_APPROVAL_INVALID)

    def test_dual_control_requires_two_distinct_approvers(self) -> None:
        with self.assertRaises(ValueError):
            self.approvals.issue(
                job_id="job-1",
                action_digest="digest-1",
                approval_kind=ApprovalKind.DUAL_CONTROL,
                approvers=["same", "same"],
            )
        token = self.approvals.issue(
            job_id="job-1",
            action_digest="digest-1",
            approval_kind=ApprovalKind.DUAL_CONTROL,
            approvers=["user-a", "user-b"],
        )
        claims = self.approvals.validate_and_consume(
            token,
            job_id="job-1",
            action_digest="digest-1",
            required_kind=ApprovalKind.DUAL_CONTROL,
        )
        self.assertEqual(len(claims["approvers"]), 2)


if __name__ == "__main__":
    unittest.main()
