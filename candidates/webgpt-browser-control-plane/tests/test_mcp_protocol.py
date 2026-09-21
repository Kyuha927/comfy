from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from wbcp.mcp_protocol import McpProtocolServer
from wbcp.models import ApprovalKind, RiskTier
from wbcp.runtime import BrowserControlRuntime, build_runtime
from wbcp.settings import RuntimeSettings


class McpProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        settings = RuntimeSettings.for_tests(Path(self.tempdir.name))
        self.runtime = BrowserControlRuntime(build_runtime(settings))
        self.server = McpProtocolServer(self.runtime)
        self.session_id = "session-mcp"
        permit = self.runtime.issue_permit(
            {
                "session_id": self.session_id,
                "allowed_actions": [
                    "session_create",
                    "session_close",
                    "inspect",
                    "navigate",
                    "query",
                    "submit",
                    "job_get",
                    "job_cancel",
                    "evidence_get",
                ],
                "exact_hosts": ["example.com"],
                "risk_ceiling": int(RiskTier.R3_CONSEQUENTIAL),
                "max_calls": 20,
                "max_cost": 0.0,
                "currency": "USD",
                "ttl_seconds": 600,
            }
        )["token"]
        self.permit = permit
        result = self.server.call_tool(
            "browser.session.create",
            {
                "sessionId": self.session_id,
                "initialUrl": "https://example.com/",
                "permitToken": permit,
                "idempotencyKey": "session-create-1",
            },
        )
        self.assertFalse(result["isError"], result)

    def tearDown(self) -> None:
        self.runtime.close()
        self.tempdir.cleanup()

    def test_tool_catalog_never_exposes_token_issuance(self) -> None:
        response = self.server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertIn("browser.action.authorize", names)
        self.assertNotIn("browser.permit.issue", names)
        self.assertNotIn("browser.approval.issue", names)
        self.assertNotIn("browser.click", names)
        self.assertNotIn("browser.evaluate", names)

    def test_legacy_initialize_and_2026_discover(self) -> None:
        initialize = self.server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": "i",
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25"},
            },
            protocol_version="2025-11-25",
        )
        assert initialize is not None
        self.assertEqual(initialize["result"]["protocolVersion"], "2025-11-25")
        discover = self.server.handle_message(
            {"jsonrpc": "2.0", "id": "d", "method": "server/discover", "params": {}},
            protocol_version="2026-07-28",
        )
        assert discover is not None
        self.assertEqual(discover["result"]["protocolVersion"], "2026-07-28")
        self.assertGreater(len(discover["result"]["tools"]), 5)

    def test_read_action_is_preflighted_then_authorized_then_committed(self) -> None:
        preflight = self.server.call_tool(
            "browser.inspect",
            {
                "sessionId": self.session_id,
                "idempotencyKey": "inspect-1",
                "expected": {"text_contains": "ready"},
            },
        )
        self.assertFalse(preflight["isError"], preflight)
        job = preflight["structuredContent"]["job"]
        self.assertEqual(job["state"], "PREFLIGHTED")
        auth = self.server.call_tool(
            "browser.action.authorize",
            {"jobId": job["job_id"], "permitToken": self.permit},
        )
        self.assertFalse(auth["isError"], auth)
        commit = self.server.call_tool(
            "browser.action.commit",
            {"jobId": job["job_id"], "sessionId": self.session_id},
        )
        self.assertFalse(commit["isError"], commit)
        self.assertEqual(commit["structuredContent"]["receipt"]["state"], "SUCCEEDED")

    def test_consequential_action_cannot_authorize_without_one_shot_approval(self) -> None:
        preflight = self.server.call_tool(
            "browser.action.preflight",
            {
                "sessionId": self.session_id,
                "idempotencyKey": "submit-1",
                "actionType": "submit",
                "targetUrl": "https://example.com/form",
                "payload": {},
                "expected": {"submitted": True},
                "reversible": False,
            },
        )
        self.assertFalse(preflight["isError"], preflight)
        job = preflight["structuredContent"]["job"]
        self.assertEqual(job["decision"]["approval_kind"], "HIGH_IMPACT")
        blocked = self.server.call_tool(
            "browser.action.authorize",
            {"jobId": job["job_id"], "permitToken": self.permit},
        )
        self.assertTrue(blocked["isError"], blocked)
        self.assertEqual(
            blocked["structuredContent"]["error"]["code"],
            "BLOCKED_PENDING_HIGH_IMPACT_APPROVAL",
        )

        approval = self.runtime.issue_approval(
            {
                "job_id": job["job_id"],
                "approval_kind": ApprovalKind.HIGH_IMPACT.value,
                "approvers": ["owner@example"],
                "ttl_seconds": 120,
                "confirm_action_digest": job["decision"]["action_digest"],
            }
        )["token"]
        authorized = self.server.call_tool(
            "browser.action.authorize",
            {
                "jobId": job["job_id"],
                "permitToken": self.permit,
                "approvalToken": approval,
            },
        )
        self.assertFalse(authorized["isError"], authorized)
        commit = self.server.call_tool(
            "browser.action.commit",
            {"jobId": job["job_id"], "sessionId": self.session_id},
        )
        self.assertFalse(commit["isError"], commit)
        receipt = commit["structuredContent"]["receipt"]
        self.assertEqual(receipt["state"], "SUCCEEDED")
        self.assertEqual(receipt["risk_name"], "R3_CONSEQUENTIAL")

    def test_job_is_bound_to_the_exact_browser_session(self) -> None:
        preflight = self.server.call_tool(
            "browser.inspect",
            {"sessionId": self.session_id, "idempotencyKey": "inspect-binding"},
        )["structuredContent"]["job"]
        self.server.call_tool(
            "browser.action.authorize",
            {"jobId": preflight["job_id"], "permitToken": self.permit},
        )
        result = self.server.call_tool(
            "browser.action.commit",
            {"jobId": preflight["job_id"], "sessionId": "other-session"},
        )
        self.assertTrue(result["isError"])
        self.assertEqual(
            result["structuredContent"]["error"]["code"],
            "BLOCKED_SESSION_BINDING_MISMATCH",
        )

    def test_evidence_read_requires_a_finite_permit(self) -> None:
        preflight = self.server.call_tool(
            "browser.inspect",
            {"sessionId": self.session_id, "idempotencyKey": "inspect-evidence"},
        )["structuredContent"]["job"]
        result = self.server.call_tool(
            "browser.evidence.get",
            {
                "jobId": preflight["job_id"],
                "permitToken": self.permit,
                "idempotencyKey": "evidence-read-1",
            },
        )
        self.assertFalse(result["isError"], result)
        structured = result["structuredContent"]
        self.assertTrue(structured["verification"]["valid"])
        self.assertGreaterEqual(len(structured["events"]), 1)


if __name__ == "__main__":
    unittest.main()


class ApprovalPreviewBindingTests(unittest.TestCase):
    def test_operator_cannot_issue_approval_without_exact_digest_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = BrowserControlRuntime(build_runtime(RuntimeSettings.for_tests(Path(td))))
            try:
                session_id = "approval-confirm-session"
                permit = runtime.issue_permit(
                    {
                        "session_id": session_id,
                        "allowed_actions": ["session_create", "submit"],
                        "exact_hosts": ["example.com"],
                        "risk_ceiling": int(RiskTier.R3_CONSEQUENTIAL),
                        "max_calls": 2,
                    }
                )["token"]
                runtime.create_session(
                    {
                        "sessionId": session_id,
                        "initialUrl": "https://example.com/",
                        "permitToken": permit,
                        "idempotencyKey": "approval-create",
                    }
                )
                job = runtime.preflight(
                    {
                        "sessionId": session_id,
                        "idempotencyKey": "approval-submit",
                        "actionType": "submit",
                        "targetUrl": "https://example.com/form",
                        "reversible": False,
                    }
                )["job"]
                with self.assertRaises(Exception):
                    runtime.issue_approval(
                        {
                            "job_id": job["job_id"],
                            "approval_kind": "HIGH_IMPACT",
                            "approvers": ["owner"],
                            "confirm_action_digest": "wrong",
                        }
                    )
            finally:
                runtime.close()
