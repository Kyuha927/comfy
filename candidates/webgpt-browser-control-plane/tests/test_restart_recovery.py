from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from wbcp.models import RiskTier
from wbcp.runtime import BrowserControlRuntime, build_runtime
from wbcp.settings import RuntimeSettings


class RestartRecoveryTests(unittest.TestCase):
    def test_authorized_job_survives_process_restart_and_commits_once(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            settings = RuntimeSettings.for_tests(root)
            runtime1 = BrowserControlRuntime(build_runtime(settings))
            session_id = "restart-session"
            try:
                permit = runtime1.issue_permit(
                    {
                        "session_id": session_id,
                        "allowed_actions": ["session_create", "inspect"],
                        "exact_hosts": ["example.com"],
                        "risk_ceiling": int(RiskTier.R1_LOCAL_REVERSIBLE),
                        "max_calls": 2,
                    }
                )["token"]
                runtime1.create_session(
                    {
                        "sessionId": session_id,
                        "initialUrl": "https://example.com/",
                        "permitToken": permit,
                        "idempotencyKey": "restart-create-1",
                    }
                )
                job = runtime1.preflight(
                    {
                        "sessionId": session_id,
                        "idempotencyKey": "restart-inspect-1",
                        "actionType": "inspect",
                        "targetUrl": "https://example.com/",
                        "expected": {"text_contains": "ready"},
                    }
                )["job"]
                runtime1.authorize({"jobId": job["job_id"], "permitToken": permit})
                self.assertEqual(runtime1.components.store.get(job["job_id"]).state.value, "AUTHORIZED")
            finally:
                runtime1.close()

            runtime2 = BrowserControlRuntime(build_runtime(settings))
            try:
                recreate = runtime2.issue_permit(
                    {
                        "session_id": session_id,
                        "allowed_actions": ["session_create"],
                        "exact_hosts": ["example.com"],
                        "risk_ceiling": int(RiskTier.R1_LOCAL_REVERSIBLE),
                        "max_calls": 1,
                    }
                )["token"]
                runtime2.create_session(
                    {
                        "sessionId": session_id,
                        "initialUrl": "https://example.com/",
                        "permitToken": recreate,
                        "idempotencyKey": "restart-create-2",
                    }
                )
                receipt = runtime2.commit({"jobId": job["job_id"], "sessionId": session_id})[
                    "receipt"
                ]
                self.assertEqual(receipt["state"], "SUCCEEDED")
                replay = runtime2.commit({"jobId": job["job_id"], "sessionId": session_id})[
                    "receipt"
                ]
                self.assertEqual(replay["state"], "SUCCEEDED")
                self.assertEqual(replay["action_digest"], receipt["action_digest"])
                self.assertTrue(runtime2.components.evidence.verify().valid)
            finally:
                runtime2.close()


if __name__ == "__main__":
    unittest.main()
