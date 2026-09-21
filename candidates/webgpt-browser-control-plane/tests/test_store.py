from __future__ import annotations

import unittest

from wbcp.errors import ControlPlaneError, FailureCode
from wbcp.models import ActionRequest, ApprovalKind, JobState, PolicyDecision, RiskTier
from wbcp.store import JobStore


def make_request(key: str = "key", action: str = "inspect") -> ActionRequest:
    return ActionRequest(
        session_id="s",
        idempotency_key=key,
        action_type=action,
        target_url="https://example.com/",
    )


def make_decision(risk: RiskTier = RiskTier.R0_READ_ONLY) -> PolicyDecision:
    return PolicyDecision(True, risk, ApprovalKind.SESSION, 2, "ok", "digest")


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = JobStore()

    def tearDown(self) -> None:
        self.store.close()

    def test_create_and_idempotent_get(self) -> None:
        first, created = self.store.create_or_get(make_request(), make_decision())
        second, created2 = self.store.create_or_get(make_request(), make_decision())
        self.assertTrue(created)
        self.assertFalse(created2)
        self.assertEqual(first.job_id, second.job_id)

    def test_idempotency_conflict_is_rejected(self) -> None:
        self.store.create_or_get(make_request(), make_decision())
        with self.assertRaises(ControlPlaneError) as ctx:
            self.store.create_or_get(make_request(action="navigate"), make_decision())
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_IDEMPOTENCY_CONFLICT)

    def test_legal_transition_uses_revision_cas(self) -> None:
        job, _ = self.store.create_or_get(make_request(), make_decision())
        next_job = self.store.transition(
            job.job_id,
            expected_states={JobState.CREATED},
            new_state=JobState.PREFLIGHTED,
            expected_revision=0,
        )
        self.assertEqual(next_job.state, JobState.PREFLIGHTED)
        self.assertEqual(next_job.revision, 1)
        with self.assertRaises(ControlPlaneError) as ctx:
            self.store.transition(
                job.job_id,
                expected_states={JobState.PREFLIGHTED},
                new_state=JobState.AUTHORIZED,
                expected_revision=0,
            )
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_CONCURRENT_REVISION_CONFLICT)

    def test_illegal_transition_is_blocked(self) -> None:
        job, _ = self.store.create_or_get(make_request(), make_decision())
        with self.assertRaises(ControlPlaneError) as ctx:
            self.store.transition(
                job.job_id,
                expected_states={JobState.CREATED},
                new_state=JobState.SUCCEEDED,
            )
        self.assertEqual(ctx.exception.code, FailureCode.BLOCKED_ILLEGAL_STATE_TRANSITION)


if __name__ == "__main__":
    unittest.main()
