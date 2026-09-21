from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wbcp.errors import ControlPlaneError, FailureCode
from wbcp.models import RiskTier
from wbcp.runtime import BrowserControlRuntime, build_runtime
from wbcp.settings import RuntimeConfigurationError, RuntimeSettings


class SettingsAndSessionTests(unittest.TestCase):
    def test_live_settings_require_explicit_encoded_keys(self) -> None:
        env = {
            "WBCP_DATA_DIR": "/tmp/wbcp-test",
            "WBCP_ALLOWED_HOSTS": "example.com",
            "WBCP_HOST_SUBJECT": "subject",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RuntimeConfigurationError):
                RuntimeSettings.from_env()

    def test_live_settings_reject_wildcard_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RuntimeConfigurationError):
                RuntimeSettings(
                    data_dir=Path(td),
                    allowed_hosts=frozenset({"*.example.com"}),
                    host_subject="subject",
                    permit_signing_key=b"P" * 32,
                    approval_signing_key=b"A" * 32,
                    evidence_hmac_key=b"E" * 32,
                )

    def test_duplicate_session_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = BrowserControlRuntime(build_runtime(RuntimeSettings.for_tests(Path(td))))
            try:
                token = runtime.issue_permit(
                    {
                        "session_id": "s1",
                        "allowed_actions": ["session_create"],
                        "exact_hosts": ["example.com"],
                        "risk_ceiling": int(RiskTier.R1_LOCAL_REVERSIBLE),
                        "max_calls": 2,
                    }
                )["token"]
                args = {
                    "sessionId": "s1",
                    "initialUrl": "https://example.com/",
                    "permitToken": token,
                    "idempotencyKey": "create-1",
                }
                runtime.create_session(args)
                args["idempotencyKey"] = "create-2"
                with self.assertRaises(ControlPlaneError) as raised:
                    runtime.create_session(args)
                self.assertEqual(raised.exception.code, FailureCode.BLOCKED_SESSION_ALREADY_EXISTS)
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()


class SessionIdempotencyTests(unittest.TestCase):
    def test_session_create_exact_replay_returns_existing_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = BrowserControlRuntime(build_runtime(RuntimeSettings.for_tests(Path(td))))
            try:
                token = runtime.issue_permit(
                    {
                        "session_id": "replay-session",
                        "allowed_actions": ["session_create"],
                        "exact_hosts": ["example.com"],
                        "risk_ceiling": int(RiskTier.R1_LOCAL_REVERSIBLE),
                        "max_calls": 1,
                    }
                )["token"]
                args = {
                    "sessionId": "replay-session",
                    "initialUrl": "https://example.com/",
                    "permitToken": token,
                    "idempotencyKey": "create-replay",
                }
                first = runtime.create_session(args)
                second = runtime.create_session(args)
                self.assertEqual(first["session"]["session_id"], second["session"]["session_id"])
                self.assertTrue(second["authorization"]["usage"]["replayed"])
                self.assertEqual(runtime.components.sessions.count(), 1)
            finally:
                runtime.close()
