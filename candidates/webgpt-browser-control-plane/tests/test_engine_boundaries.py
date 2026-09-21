from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from wbcp.cua_binding import CuaBinding
from wbcp.engines import EnginePolicy, EngineRouter
from wbcp.errors import ControlPlaneError, FailureCode
from wbcp.mcp_protocol import tool_catalog
from wbcp.mock_browser import MockBrowserAdapter
from wbcp.models import ActionRequest, EngineKind, ExecutionResult, JobState, RiskTier
from wbcp.runtime import BrowserControlRuntime, build_runtime
from wbcp.settings import RuntimeSettings


class _JevDoneWithoutIndependentVerification(MockBrowserAdapter):
    """A hostile Jev executor claim used to prove WBCP does not trust DONE."""

    def execute(self, request: ActionRequest) -> ExecutionResult:
        result = super().execute(request)
        return ExecutionResult(
            before=result.before,
            after=result.after,
            signals=result.signals,
            output={**result.output, "jev_status": "DONE", "independent_verifier_passed": False},
            rollback_token=None,
        )


class _FailingJevAdapter(MockBrowserAdapter):
    def __init__(self, initial_url: str = "https://example.com/") -> None:
        super().__init__(initial_url)
        self.execution_count = 0

    def execute(self, request: ActionRequest) -> ExecutionResult:
        self.execution_count += 1
        raise RuntimeError("synthetic Jev possible-mutation failure")


class EngineBoundaryTests(unittest.TestCase):
    @staticmethod
    def _request(
        *,
        engine: EngineKind,
        action_type: str = "inspect",
        target_url: str = "https://example.com/",
        payload: dict[str, object] | None = None,
        idempotency_key: str = "engine-boundary",
    ) -> ActionRequest:
        return ActionRequest(
            session_id="engine-session",
            idempotency_key=idempotency_key,
            action_type=action_type,
            target_url=target_url,
            engine=engine,
            payload=payload or {},
        )

    @staticmethod
    def _runtime(root: Path, **overrides: object) -> BrowserControlRuntime:
        settings = replace(RuntimeSettings.for_tests(root), **overrides)
        return BrowserControlRuntime(build_runtime(settings))

    @staticmethod
    def _permit(
        runtime: BrowserControlRuntime,
        *,
        session_id: str,
        actions: list[str],
        max_calls: int,
    ) -> str:
        return runtime.issue_permit(
            {
                "session_id": session_id,
                "allowed_actions": actions,
                "exact_hosts": ["example.com"],
                "risk_ceiling": int(RiskTier.R2_REMOTE_REVERSIBLE),
                "max_calls": max_calls,
                "max_cost": 0.0,
                "currency": "USD",
                "ttl_seconds": 300,
            }
        )["token"]

    def _create_session(
        self,
        runtime: BrowserControlRuntime,
        *,
        session_id: str,
        actions: list[str],
        max_calls: int,
    ) -> str:
        permit = self._permit(
            runtime,
            session_id=session_id,
            actions=["session_create", *actions],
            max_calls=max_calls,
        )
        runtime.create_session(
            {
                "sessionId": session_id,
                "initialUrl": "https://example.com/",
                "permitToken": permit,
                "idempotencyKey": f"{session_id}-create",
            }
        )
        return permit

    def test_auto_keeps_playwright_primary_even_with_jev_preference(self) -> None:
        router = EngineRouter(
            EnginePolicy(
                engine_preference=EngineKind.JEV,
                jev_enabled=True,
                jev_public_hosts=frozenset({"example.com"}),
            )
        )
        route = router.resolve(self._request(engine=EngineKind.AUTO))
        self.assertTrue(route.allowed)
        self.assertEqual(route.selected, EngineKind.PLAYWRIGHT)
        self.assertIn("ENGINE_PREFERENCE_NOT_AUTHORITY", route.flags)

    def test_jev_default_denials_are_specific_and_fail_closed(self) -> None:
        router = EngineRouter(
            EnginePolicy(jev_enabled=True, jev_public_hosts=frozenset({"example.com"}))
        )
        cases = {
            "authenticated": (
                {"authenticated_page": True},
                FailureCode.BLOCKED_JEV_AUTHENTICATED_PAGE_DEFAULT_DENY,
            ),
            "sensitive": (
                {"sensitive_page": True},
                FailureCode.BLOCKED_JEV_SENSITIVE_PAGE_DEFAULT_DENY,
            ),
            "personal-profile": (
                {"existing_personal_profile": True},
                FailureCode.BLOCKED_JEV_EXISTING_PERSONAL_PROFILE_DEFAULT_DENY,
            ),
            "unsupported-canvas": (
                {"page_features": ["canvas"]},
                FailureCode.BLOCKED_JEV_UNSUPPORTED_FEATURE,
            ),
        }
        for name, (payload, expected_code) in cases.items():
            with self.subTest(name=name):
                route = router.resolve(
                    self._request(engine=EngineKind.JEV, payload=payload)
                )
                self.assertFalse(route.allowed)
                self.assertEqual(route.failure_code, expected_code)

    def test_jev_external_egress_is_default_deny_and_loopback_cannot_authorize_it(self) -> None:
        default_router = EngineRouter(
            EnginePolicy(jev_enabled=True, jev_public_hosts=frozenset({"example.com"}))
        )
        denied = default_router.resolve(
            self._request(engine=EngineKind.JEV, payload={"external_model_egress": True})
        )
        self.assertEqual(
            denied.failure_code, FailureCode.BLOCKED_JEV_EXTERNAL_MODEL_EGRESS_DEFAULT_DENY
        )

        authorized_router = EngineRouter(
            EnginePolicy(
                jev_enabled=True,
                jev_public_hosts=frozenset({"example.com"}),
                jev_external_model_egress_enabled=True,
                jev_runtime_authorization_id="independent-host-grant",
            )
        )
        loopback = authorized_router.resolve(
            self._request(
                engine=EngineKind.JEV,
                target_url="http://localhost:8000/fixture",
                payload={"isolated_local_fixture": True, "external_model_egress": True},
            )
        )
        self.assertEqual(
            loopback.failure_code, FailureCode.BLOCKED_JEV_TARGET_NOT_EXACT_PUBLIC_HOST
        )

    def test_jev_done_is_quarantined_without_the_independent_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = self._runtime(
                Path(td),
                jev_enabled=True,
                jev_public_hosts=frozenset({"example.com"}),
            )
            try:
                session_id = "jev-done"
                permit = self._create_session(
                    runtime, session_id=session_id, actions=["inspect"], max_calls=2
                )
                runtime.register_engine_adapter(
                    EngineKind.JEV,
                    lambda session: _JevDoneWithoutIndependentVerification(session.initial_url),
                )
                preflight = runtime.preflight(
                    {
                        "sessionId": session_id,
                        "idempotencyKey": "jev-done-inspect",
                        "actionType": "inspect",
                        "targetUrl": "https://example.com/",
                        "engine": "JEV",
                        "reversible": False,
                        "permitToken": permit,
                    }
                )
                self.assertEqual(preflight["job"]["state"], JobState.AUTHORIZED.value)
                receipt = runtime.commit(
                    {"jobId": preflight["job"]["job_id"], "sessionId": session_id}
                )["receipt"]
                self.assertEqual(receipt["state"], JobState.QUARANTINED.value)
                self.assertEqual(
                    receipt["failure_code"],
                    FailureCode.BLOCKED_POSTCONDITION_UNVERIFIED.value,
                )
            finally:
                runtime.close()

    def test_jev_executor_unavailable_does_not_turn_the_route_into_a_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = self._runtime(
                Path(td),
                jev_enabled=True,
                jev_public_hosts=frozenset({"example.com"}),
            )
            try:
                session_id = "jev-unavailable"
                permit = self._create_session(
                    runtime, session_id=session_id, actions=["inspect"], max_calls=2
                )
                preflight = runtime.preflight(
                    {
                        "sessionId": session_id,
                        "idempotencyKey": "jev-unavailable-inspect",
                        "actionType": "inspect",
                        "targetUrl": "https://example.com/",
                        "engine": "JEV",
                        "permitToken": permit,
                    }
                )
                with self.assertRaises(ControlPlaneError) as raised:
                    runtime.commit(
                        {"jobId": preflight["job"]["job_id"], "sessionId": session_id}
                    )
                self.assertEqual(raised.exception.code, FailureCode.BLOCKED_JEV_EXECUTOR_UNAVAILABLE)
            finally:
                runtime.close()

    def test_cua_driver_minimum_and_exact_binding_are_enforced(self) -> None:
        request = self._request(engine=EngineKind.CUA, action_type="navigate")
        below_minimum = EngineRouter(
            EnginePolicy(cua_enabled=True, cua_driver_version="0.21.0")
        ).resolve(request)
        self.assertEqual(
            below_minimum.failure_code,
            FailureCode.BLOCKED_CUA_DRIVER_BELOW_MINIMUM_VALIDATED_REFERENCE,
        )

        binding = CuaBinding(
            session_id="engine-session",
            process_id=42,
            window_id="window-1",
            target_id="target-1",
            tab_id="tab-1",
            authorized_url="https://example.com/",
        )
        router = EngineRouter(EnginePolicy(cua_enabled=True, cua_driver_version="0.28.2"))
        allowed = router.resolve(request, cua_binding=binding)
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.selected, EngineKind.CUA)

        override = router.resolve(
            self._request(
                engine=EngineKind.CUA,
                action_type="navigate",
                payload={"targetUrl": "https://example.com/other"},
            ),
            cua_binding=binding,
        )
        self.assertEqual(
            override.failure_code, FailureCode.BLOCKED_CUA_BINDING_ARGUMENT_OVERRIDE
        )
        mismatch = router.resolve(
            self._request(
                engine=EngineKind.CUA,
                action_type="navigate",
                target_url="https://example.com/other",
            ),
            cua_binding=binding,
        )
        self.assertEqual(
            mismatch.failure_code, FailureCode.BLOCKED_CUA_SESSION_BINDING_MISMATCH
        )

    def test_existing_personal_cua_profile_requires_two_preexisting_host_grants(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = self._runtime(
                Path(td), cua_enabled=True, cua_driver_version="0.28.2"
            )
            try:
                session_id = "cua-personal"
                self._create_session(
                    runtime, session_id=session_id, actions=[], max_calls=1
                )
                binding = CuaBinding(
                    session_id=session_id,
                    process_id=73,
                    window_id="window-personal",
                    target_id="target-personal",
                    tab_id="tab-personal",
                    authorized_url="https://example.com/",
                    profile_kind="existing-personal",
                )
                with self.assertRaises(ControlPlaneError) as raised:
                    runtime.bind_cua_session(session_id=session_id, binding=binding)
                self.assertEqual(
                    raised.exception.code,
                    FailureCode.BLOCKED_CUA_EXISTING_PROFILE_DUAL_APPROVAL_REQUIRED,
                )
            finally:
                runtime.close()

    def test_missing_cua_executor_does_not_poison_playwright_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = self._runtime(
                Path(td), cua_enabled=True, cua_driver_version="0.28.2"
            )
            try:
                session_id = "cua-no-executor"
                permit = self._create_session(
                    runtime, session_id=session_id, actions=["navigate"], max_calls=2
                )
                runtime.bind_cua_session(
                    session_id=session_id,
                    binding=CuaBinding(
                        session_id=session_id,
                        process_id=101,
                        window_id="window-isolated",
                        target_id="target-isolated",
                        tab_id="tab-isolated",
                        authorized_url="https://example.com/",
                    ),
                )
                cua_job = runtime.preflight(
                    {
                        "sessionId": session_id,
                        "idempotencyKey": "cua-no-executor-navigate",
                        "actionType": "navigate",
                        "targetUrl": "https://example.com/",
                        "engine": "CUA",
                        "permitToken": permit,
                    }
                )["job"]
                with self.assertRaises(ControlPlaneError) as raised:
                    runtime.commit({"jobId": cua_job["job_id"], "sessionId": session_id})
                self.assertEqual(raised.exception.code, FailureCode.BLOCKED_CUA_EXECUTOR_UNAVAILABLE)

                fallback = runtime.preflight(
                    {
                        "sessionId": session_id,
                        "idempotencyKey": "playwright-after-missing-cua",
                        "actionType": "navigate",
                        "targetUrl": "https://example.com/",
                        "engine": "PLAYWRIGHT",
                    }
                )
                self.assertEqual(fallback["job"]["state"], JobState.PREFLIGHTED.value)
            finally:
                runtime.close()

    def test_possible_mutation_requires_reconciliation_and_duplicate_cannot_retry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = self._runtime(
                Path(td),
                jev_enabled=True,
                jev_public_hosts=frozenset({"example.com"}),
            )
            try:
                session_id = "jev-reconcile"
                permit = self._create_session(
                    runtime, session_id=session_id, actions=["navigate"], max_calls=2
                )
                adapter = _FailingJevAdapter()
                runtime.register_engine_adapter(EngineKind.JEV, lambda _: adapter)
                args = {
                    "sessionId": session_id,
                    "idempotencyKey": "jev-possible-mutation",
                    "actionType": "navigate",
                    "targetUrl": "https://example.com/",
                    "engine": "JEV",
                    "reversible": False,
                    "permitToken": permit,
                }
                failing_job = runtime.preflight(args)["job"]
                failed = runtime.commit(
                    {"jobId": failing_job["job_id"], "sessionId": session_id}
                )["receipt"]
                self.assertEqual(failed["state"], JobState.QUARANTINED.value)
                self.assertEqual(adapter.execution_count, 1)

                duplicate_args = dict(args)
                duplicate_args.pop("permitToken")
                duplicate = runtime.preflight(duplicate_args)["job"]
                self.assertEqual(duplicate["job_id"], failing_job["job_id"])
                duplicate_receipt = runtime.commit(
                    {"jobId": duplicate["job_id"], "sessionId": session_id}
                )["receipt"]
                self.assertEqual(duplicate_receipt["state"], JobState.QUARANTINED.value)
                self.assertEqual(adapter.execution_count, 1)

                fallback_args = {
                    "sessionId": session_id,
                    "idempotencyKey": "playwright-before-reconcile",
                    "actionType": "navigate",
                    "targetUrl": "https://example.com/",
                    "engine": "PLAYWRIGHT",
                    "reversible": False,
                }
                with self.assertRaises(ControlPlaneError) as raised:
                    runtime.preflight(fallback_args)
                self.assertEqual(
                    raised.exception.code,
                    FailureCode.BLOCKED_SIDE_EFFECT_RECONCILIATION_REQUIRED,
                )

                runtime.components.reconciliation.reconcile(
                    job_id=failing_job["job_id"],
                    verifier_id="unit-independent-verifier",
                    evidence_hash="f" * 64,
                )
                recovered = runtime.preflight(fallback_args)["job"]
                self.assertEqual(recovered["state"], JobState.PREFLIGHTED.value)
            finally:
                runtime.close()

    def test_public_mcp_catalog_has_no_shell_eval_filesystem_or_binding_grant(self) -> None:
        names = {entry["name"] for entry in tool_catalog()}
        forbidden_fragments = ("shell", "eval", "filesystem", "binding", "grant", "profile")
        self.assertFalse(
            any(fragment in name.lower() for fragment in forbidden_fragments for name in names)
        )
        self.assertFalse(any(name.startswith("browser.cua") for name in names))


if __name__ == "__main__":
    unittest.main()
