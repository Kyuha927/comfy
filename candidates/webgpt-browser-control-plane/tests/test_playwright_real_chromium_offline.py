from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from wbcp.evidence import EvidenceLedger
from wbcp.browser_binary import discover_chromium_executable
from wbcp.errors import FailureCode
from wbcp.models import ActionRequest, ApprovalKind, JobState, RiskTier
from wbcp.orchestrator import JobOrchestrator
from wbcp.permits import ApprovalAuthority, PermitAuthority, PermitRegistry
from wbcp.playwright_adapter import PlaywrightBrowserAdapter
from wbcp.policy import PolicyConfig, PolicyEngine
from wbcp.store import JobStore
from wbcp.url_guard import URLGuard, URLPolicy


PAGE = """<!doctype html>
<html><head><title>WBCP Offline Chromium</title></head>
<body>
  <h1>Ready</h1>
  <label for='name'>Name</label>
  <input id='name' aria-label='Name'>
  <button id='publish' type='button'>Publish</button>
  <div id='status' aria-live='polite'>Draft</div>
  <script>
    document.querySelector('#publish').addEventListener('click', () => {
      document.querySelector('#status').textContent = 'Published';
    });
  </script>
</body></html>"""


class RealChromiumOfflineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        self.registry = PermitRegistry(str(root / "permits.sqlite3"))
        self.store = JobStore(str(root / "jobs.sqlite3"))
        self.permits = PermitAuthority(b"P" * 32, self.registry)
        self.approvals = ApprovalAuthority(b"A" * 32, self.registry)
        self.evidence = EvidenceLedger(root / "evidence.jsonl", hmac_key=b"E" * 32)
        self.guard = URLGuard(URLPolicy(allowed_hosts={"example.com"}))
        self.orchestrator = JobOrchestrator(
            url_guard=self.guard,
            policy=PolicyEngine(PolicyConfig()),
            permits=self.permits,
            approvals=self.approvals,
            store=self.store,
            evidence=self.evidence,
            host_subject="real-chromium-offline-host",
        )
        self.trace_path = root / "trace.zip"
        executable = discover_chromium_executable()
        if executable is None:
            self.td.cleanup()
            self.skipTest("No supported Chromium executable is installed")
        self.adapter = PlaywrightBrowserAdapter(
            artifacts_dir=root / "artifacts",
            executable_path=executable,
            url_guard=self.guard,
            trace_path=self.trace_path,
        )
        self.adapter.start()
        self.adapter.page.set_content(PAGE)

    def tearDown(self) -> None:
        self.adapter.close()
        self.store.close()
        self.registry.close()
        self.assertTrue(self.trace_path.exists())
        self.assertGreater(self.trace_path.stat().st_size, 0)
        self.td.cleanup()

    def permit(self, request: ActionRequest, risk: RiskTier) -> str:
        return self.permits.issue(
            subject="real-chromium-offline-host",
            session_id=request.session_id,
            allowed_actions=[request.action_type],
            exact_hosts=["example.com"],
            risk_ceiling=risk,
            max_calls=1,
        )

    def authorize_and_run(self, request: ActionRequest, risk: RiskTier):
        preflight = self.orchestrator.preflight(request)
        approval = None
        if preflight.job.decision.approval_kind == ApprovalKind.HIGH_IMPACT:
            approval = self.approvals.issue(
                job_id=preflight.job.job_id,
                action_digest=preflight.job.decision.action_digest,
                approval_kind=ApprovalKind.HIGH_IMPACT,
                approvers=["offline-test-owner"],
            )
        self.orchestrator.authorize(
            preflight.job.job_id,
            permit_token=self.permit(request, risk),
            approval_token=approval,
        )
        return self.orchestrator.run(preflight.job.job_id, self.adapter)

    def test_real_chromium_dom_and_pixel_evidence_pass_for_reversible_fill(self) -> None:
        request = ActionRequest(
            session_id="offline-real",
            idempotency_key="real-fill",
            action_type="type",
            target_url="https://example.com/form",
            payload={"locator": {"label": "Name"}, "value": "Ada"},
            expected={
                "value_equals": {"label": "Name", "value": "Ada"},
                "pixel_assertion": "changed",
            },
        )
        receipt = self.authorize_and_run(request, RiskTier.R2_REMOTE_REVERSIBLE)
        self.assertEqual(receipt.state, JobState.SUCCEEDED)
        self.assertTrue(self.evidence.verify().valid)
        self.assertNotEqual(receipt.evidence_root, "0" * 64)

    def test_consequential_click_cannot_pass_without_real_network_or_provider_receipt(self) -> None:
        request = ActionRequest(
            session_id="offline-real",
            idempotency_key="real-publish-no-network",
            action_type="publish",
            target_url="https://example.com/form",
            payload={
                "locator": {"role": "button", "name": "Publish"},
                "wait_for": {"text": "Published"},
            },
            expected={
                "text_contains": "Published",
                "pixel_assertion": "changed",
                "network": {"url_contains": "/publish", "method": "POST", "statuses": [200]},
            },
            reversible=False,
        )
        receipt = self.authorize_and_run(request, RiskTier.R3_CONSEQUENTIAL)
        self.assertEqual(receipt.state, JobState.QUARANTINED)
        self.assertEqual(receipt.failure_code, FailureCode.BLOCKED_POSTCONDITION_UNVERIFIED.value)
        self.assertTrue(receipt.result["signals"]["dom_ok"])
        self.assertTrue(receipt.result["signals"]["pixel_ok"])
        self.assertFalse(receipt.result["signals"]["network_ok"])
        self.assertTrue(self.evidence.verify().valid)


if __name__ == "__main__":
    unittest.main()
