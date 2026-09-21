from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from wbcp.evidence import EvidenceLedger
from wbcp.orchestrator import JobOrchestrator
from wbcp.permits import ApprovalAuthority, PermitAuthority, PermitRegistry
from wbcp.policy import PolicyConfig, PolicyEngine
from wbcp.store import JobStore
from wbcp.url_guard import URLGuard, URLPolicy


@dataclass
class TestStack:
    tempdir: tempfile.TemporaryDirectory[str]
    orchestrator: JobOrchestrator
    permits: PermitAuthority
    approvals: ApprovalAuthority
    registry: PermitRegistry
    store: JobStore
    evidence: EvidenceLedger

    def cleanup(self) -> None:
        self.store.close()
        self.registry.close()
        self.tempdir.cleanup()


def build_stack(*, r4_mode: str = "block", max_cost: float = 100.0) -> TestStack:
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    registry = PermitRegistry(str(root / "permits.sqlite3"))
    store = JobStore(str(root / "jobs.sqlite3"))
    secret = b"P" * 32
    approval_secret = b"A" * 32
    permits = PermitAuthority(secret, registry)
    approvals = ApprovalAuthority(approval_secret, registry)
    evidence = EvidenceLedger(root / "evidence.jsonl", hmac_key=b"E" * 32)
    policy = PolicyEngine(
        PolicyConfig(r4_mode=r4_mode, maximum_action_cost=max_cost, currency="USD")
    )
    orchestrator = JobOrchestrator(
        url_guard=URLGuard(URLPolicy(allowed_hosts={"example.com", "api.example.com"})),
        policy=policy,
        permits=permits,
        approvals=approvals,
        store=store,
        evidence=evidence,
        host_subject="host-model-attested",
    )
    return TestStack(td, orchestrator, permits, approvals, registry, store, evidence)
