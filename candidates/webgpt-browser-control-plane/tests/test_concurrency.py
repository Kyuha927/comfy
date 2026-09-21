from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from wbcp.evidence import EvidenceLedger
from wbcp.errors import ControlPlaneError, FailureCode
from wbcp.models import ActionRequest, ApprovalKind, RiskTier
from wbcp.permits import ApprovalAuthority, PermitAuthority, PermitRegistry
from wbcp.store import JobStore
from wbcp.models import PolicyDecision


class ConcurrencyTests(unittest.TestCase):
    def test_idempotent_job_creation_converges_to_one_job(self) -> None:
        store = JobStore()
        decision = PolicyDecision(
            True, RiskTier.R0_READ_ONLY, ApprovalKind.SESSION, 2, "ok", "digest"
        )

        def create() -> str:
            request = ActionRequest(
                session_id="s",
                idempotency_key="same-key",
                action_type="inspect",
                target_url="https://example.com/",
            )
            return store.create_or_get(request, decision)[0].job_id

        with ThreadPoolExecutor(max_workers=12) as pool:
            ids = list(pool.map(lambda _: create(), range(50)))
        self.assertEqual(len(set(ids)), 1)
        store.close()

    def test_finite_permit_never_exceeds_call_cap_under_race(self) -> None:
        registry = PermitRegistry()
        authority = PermitAuthority(b"P" * 32, registry)
        token = authority.issue(
            subject="host",
            session_id="s",
            allowed_actions=["navigate"],
            exact_hosts=["example.com"],
            risk_ceiling=RiskTier.R1_LOCAL_REVERSIBLE,
            max_calls=5,
        )

        def consume(index: int) -> str:
            request = ActionRequest(
                session_id="s",
                idempotency_key=f"k-{index}",
                action_type="navigate",
                target_url="https://example.com/",
            )
            try:
                authority.validate_and_consume(
                    token,
                    request=request,
                    risk=RiskTier.R1_LOCAL_REVERSIBLE,
                    expected_subject="host",
                )
                return "ok"
            except ControlPlaneError as exc:
                self.assertEqual(exc.code, FailureCode.BLOCKED_PERMIT_EXHAUSTED)
                return "blocked"

        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(consume, range(40)))
        self.assertEqual(results.count("ok"), 5)
        self.assertEqual(results.count("blocked"), 35)
        registry.close()

    def test_one_shot_approval_has_exactly_one_winner(self) -> None:
        registry = PermitRegistry()
        authority = ApprovalAuthority(b"A" * 32, registry)
        token = authority.issue(
            job_id="job",
            action_digest="digest",
            approval_kind=ApprovalKind.HIGH_IMPACT,
            approvers=["owner"],
        )

        def consume(_: int) -> str:
            try:
                authority.validate_and_consume(
                    token,
                    job_id="job",
                    action_digest="digest",
                    required_kind=ApprovalKind.HIGH_IMPACT,
                )
                return "ok"
            except ControlPlaneError as exc:
                self.assertEqual(exc.code, FailureCode.BLOCKED_APPROVAL_REPLAY)
                return "blocked"

        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(consume, range(32)))
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("blocked"), 31)
        registry.close()

    def test_evidence_sequence_is_contiguous_under_concurrency(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ledger = EvidenceLedger(Path(td) / "ledger.jsonl", hmac_key=b"E" * 32)
            with ThreadPoolExecutor(max_workers=16) as pool:
                list(pool.map(lambda i: ledger.append("EVENT", f"job-{i}", {"i": i}), range(80)))
            result = ledger.verify()
            self.assertTrue(result.valid, result.error)
            self.assertEqual(result.event_count, 80)


if __name__ == "__main__":
    unittest.main()
