from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from .evidence import EvidenceLedger
from .cua_binding import CuaBinding
from .engines import EnginePolicy, EngineRouter
from .errors import ControlPlaneError, FailureCode
from .mock_browser import MockBrowserAdapter
from .models import ActionRequest, ApprovalKind, AuthoritySource, EngineKind, JobState, RiskTier
from .orchestrator import BrowserAdapter, JobOrchestrator
from .permits import ApprovalAuthority, PermitAuthority, PermitRegistry
from .playwright_adapter import PlaywrightBrowserAdapter
from .policy import PolicyConfig, PolicyEngine
from .redaction import Redactor
from .reconciliation import SideEffectReconciliationRegistry, is_possible_mutation
from .sessions import BrowserSessionRegistry
from .settings import RuntimeSettings
from .store import JobStore
from .url_guard import URLGuard, URLPolicy


@dataclass(slots=True)
class RuntimeComponents:
    settings: RuntimeSettings
    registry: PermitRegistry
    permits: PermitAuthority
    approvals: ApprovalAuthority
    store: JobStore
    evidence: EvidenceLedger
    url_guard: URLGuard
    orchestrator: JobOrchestrator
    sessions: BrowserSessionRegistry
    engines: EngineRouter
    reconciliation: SideEffectReconciliationRegistry
    engine_adapter_factories: dict[EngineKind, Callable[[object], BrowserAdapter]]

    def close(self) -> None:
        self.sessions.close_all()
        self.reconciliation.close()
        self.store.close()
        self.registry.close()


def build_runtime(settings: RuntimeSettings) -> RuntimeComponents:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    registry = PermitRegistry(str(settings.data_dir / "authorization.sqlite3"))
    permits = PermitAuthority(settings.permit_signing_key, registry)
    approvals = ApprovalAuthority(settings.approval_signing_key, registry)
    store = JobStore(str(settings.data_dir / "jobs.sqlite3"))
    evidence = EvidenceLedger(
        settings.data_dir / "evidence.jsonl", hmac_key=settings.evidence_hmac_key
    )
    url_guard = URLGuard(URLPolicy(allowed_hosts=set(settings.allowed_hosts)))
    policy = PolicyEngine(
        PolicyConfig(
            r4_mode=settings.r4_mode,
            maximum_action_cost=settings.maximum_action_cost,
            currency=settings.currency,
        )
    )
    orchestrator = JobOrchestrator(
        url_guard=url_guard,
        policy=policy,
        permits=permits,
        approvals=approvals,
        store=store,
        evidence=evidence,
        host_subject=settings.host_subject,
    )
    engines = EngineRouter(
        EnginePolicy(
            engine_preference=settings.engine_preference,
            jev_enabled=settings.jev_enabled,
            jev_public_hosts=settings.jev_public_hosts,
            jev_external_model_egress_enabled=settings.jev_external_model_egress_enabled,
            jev_runtime_authorization_id=settings.jev_runtime_authorization_id,
            cua_enabled=settings.cua_enabled,
            cua_driver_version=settings.cua_driver_version,
            cua_minimum_validated_version=settings.cua_minimum_validated_version,
        )
    )
    reconciliation = SideEffectReconciliationRegistry(
        str(settings.data_dir / "side_effect_reconciliation.sqlite3")
    )

    def adapter_factory(session_id: str, initial_url: str):
        if settings.use_mock_browser:
            return MockBrowserAdapter(initial_url=initial_url)
        session_dir = settings.data_dir / "sessions" / session_id
        return PlaywrightBrowserAdapter(
            artifacts_dir=session_dir,
            headless=settings.headless,
            storage_state_path=settings.storage_state_path,
            allow_css_locators=settings.allow_css_locators,
            executable_path=settings.browser_executable_path,
            url_guard=url_guard,
            trace_path=session_dir / "playwright-trace.zip",
        )

    sessions = BrowserSessionRegistry(adapter_factory)
    return RuntimeComponents(
        settings=settings,
        registry=registry,
        permits=permits,
        approvals=approvals,
        store=store,
        evidence=evidence,
        url_guard=url_guard,
        orchestrator=orchestrator,
        sessions=sessions,
        engines=engines,
        reconciliation=reconciliation,
        engine_adapter_factories={},
    )


class BrowserControlRuntime:
    """Typed MCP-facing runtime. It never exposes token issuance as a model tool."""

    VERSION = "0.3.0a1"

    def __init__(self, components: RuntimeComponents) -> None:
        self.components = components
        self.redactor = Redactor()

    def close(self) -> None:
        self.components.close()

    def health(self) -> dict[str, Any]:
        verification = self.components.evidence.verify()
        return {
            "component": "WebGPT Browser Control Plane",
            "version": self.VERSION,
            "status": "CANDIDATE_NOT_PRODUCTION",
            "production_ready": False,
            "host_subject": self.components.settings.host_subject,
            "allowed_hosts": sorted(self.components.settings.allowed_hosts),
            "active_sessions": self.components.sessions.count(),
            "evidence": verification.to_dict(),
            "transport": "MCP_JSON_RPC",
            "engines": self.components.engines.health(),
        }

    @staticmethod
    def _authority(value: Any) -> AuthoritySource:
        try:
            return AuthoritySource(str(value or AuthoritySource.MODEL_PROPOSAL.value))
        except ValueError as exc:
            raise ValueError("authoritySource is invalid") from exc

    def _action_request(self, args: dict[str, Any], *, forced_action: str | None = None) -> ActionRequest:
        session_id = str(args.get("sessionId", "")).strip()
        if not session_id:
            raise ValueError("sessionId is required")
        self.components.sessions.get(session_id)
        target_url = str(args.get("targetUrl", "")).strip()
        if not target_url:
            target_url = self.components.sessions.get(session_id).adapter.snapshot().url
        return ActionRequest(
            session_id=session_id,
            idempotency_key=str(args.get("idempotencyKey", "")).strip(),
            action_type=forced_action or str(args.get("actionType", "")),
            target_url=target_url,
            engine=EngineKind(str(args.get("engine", EngineKind.AUTO.value)).strip().upper()),
            payload=dict(args.get("payload") or {}),
            expected=dict(args.get("expected") or {}),
            authority_source=self._authority(args.get("authoritySource")),
            page_revision=args.get("pageRevision"),
            estimated_cost=(
                float(args["estimatedCost"]) if args.get("estimatedCost") is not None else None
            ),
            currency=args.get("currency"),
            reversible=bool(args.get("reversible", True)),
        )

    def register_engine_adapter(
        self, engine: EngineKind, factory: Callable[[object], BrowserAdapter]
    ) -> None:
        """Register a trusted host-owned Jev/CUA executor outside MCP.

        The public tool catalog deliberately has no equivalent operation, so a
        model request cannot replace the executable or its binding.
        """

        if engine not in {EngineKind.JEV, EngineKind.CUA}:
            raise ValueError("Only Jev or CUA may use a separately registered engine adapter")
        self.components.engine_adapter_factories[engine] = factory

    def bind_cua_session(self, *, session_id: str, binding: CuaBinding) -> dict[str, Any]:
        """Attach a CUA Driver identity binding from trusted host code only.

        This method has no MCP tool equivalent.  In particular, a model cannot
        manufacture the two independent grants required to attach an existing
        personal profile, nor can it replace a session's PID/window/tab target.
        """

        if binding.session_id != session_id:
            raise ControlPlaneError(
                FailureCode.BLOCKED_CUA_SESSION_BINDING_MISMATCH,
                "CUA binding belongs to a different browser session",
                {"binding_session_id": binding.session_id, "session_id": session_id},
            )
        validated = self.components.url_guard.validate(binding.authorized_url)
        if validated.normalized != binding.authorized_url:
            raise ControlPlaneError(
                FailureCode.BLOCKED_CUA_SESSION_BINDING_MISMATCH,
                "CUA binding URL must already be the exact normalized authorized URL",
                {"authorized_url": binding.authorized_url, "normalized_url": validated.normalized},
            )
        if binding.profile_kind == "existing-personal":
            expected = (
                self.components.settings.existing_profile_grant_id,
                self.components.settings.existing_profile_independent_grant_id,
            )
            actual = (binding.existing_profile_grant_id, binding.independent_grant_id)
            if not all(expected) or actual != expected:
                raise ControlPlaneError(
                    FailureCode.BLOCKED_CUA_EXISTING_PROFILE_DUAL_APPROVAL_REQUIRED,
                    "Existing-profile binding requires two pre-existing independent host grants",
                )
        managed = self.components.sessions.bind_cua(session_id=session_id, binding=binding)
        self.components.evidence.append(
            "CUA_SESSION_BOUND",
            f"session:{session_id}",
            {
                "session_id": session_id,
                "profile_kind": binding.profile_kind,
                "authorized_url": binding.authorized_url,
                "binding_fingerprint": self.redactor.redact(
                    {"pid": binding.process_id, "window": binding.window_id, "target": binding.target_id, "tab": binding.tab_id}
                ),
            },
        )
        return {"session": managed.to_dict(), "bound": True}

    def _route_request(self, request: ActionRequest) -> dict[str, Any]:
        managed = self.components.sessions.get(request.session_id)
        route = self.components.engines.resolve(
            request,
            session_mode=managed.mode,
            cua_binding=managed.cua_binding,
        )
        request.engine = route.require_allowed()
        return route.to_dict()

    def _consume_session_permit(
        self,
        *,
        session_id: str,
        action_type: str,
        target_url: str,
        permit_token: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        validated = self.components.url_guard.validate(target_url)
        request = ActionRequest(
            session_id=session_id,
            idempotency_key=idempotency_key,
            action_type=action_type,
            target_url=validated.normalized,
            authority_source=AuthoritySource.USER,
        )
        decision = self.components.orchestrator.policy.evaluate(request, validated)
        if not decision.allowed:
            raise ControlPlaneError(
                FailureCode(decision.failure_code or FailureCode.BLOCKED_HIGH_RISK_ACTION_DISABLED),
                decision.reason,
            )
        validation = self.components.permits.validate_and_consume(
            permit_token,
            request=request,
            risk=decision.risk,
            expected_subject=self.components.settings.host_subject,
        )
        return {
            "permit_id": validation.permit_id,
            "usage": validation.usage,
            "action_digest": decision.action_digest,
        }

    def create_session(self, args: dict[str, Any]) -> dict[str, Any]:
        session_id = str(args.get("sessionId", "")).strip()
        initial_url = str(args.get("initialUrl", "")).strip()
        permit_token = str(args.get("permitToken", ""))
        idempotency_key = str(args.get("idempotencyKey", "")).strip()
        if not all((session_id, initial_url, permit_token, idempotency_key)):
            raise ValueError(
                "sessionId, initialUrl, permitToken, and idempotencyKey are required"
            )
        validated = self.components.url_guard.validate(initial_url)
        permit = self._consume_session_permit(
            session_id=session_id,
            action_type="session_create",
            target_url=validated.normalized,
            permit_token=permit_token,
            idempotency_key=idempotency_key,
        )
        if bool(permit["usage"].get("replayed")):
            try:
                managed = self.components.sessions.get(session_id)
                if managed.initial_url != validated.normalized:
                    raise ControlPlaneError(
                        FailureCode.BLOCKED_IDEMPOTENCY_CONFLICT,
                        "Replayed session creation changed the initial URL",
                    )
            except ControlPlaneError as exc:
                if exc.code != FailureCode.BLOCKED_SESSION_NOT_FOUND:
                    raise
                managed = self.components.sessions.create(
                    session_id=session_id, initial_url=validated.normalized
                )
        else:
            managed = self.components.sessions.create(
                session_id=session_id, initial_url=validated.normalized
            )
        self.components.evidence.append(
            "SESSION_CREATED",
            f"session:{session_id}",
            {
                "session_id": session_id,
                "initial_url": validated.normalized,
                "permit_id": permit["permit_id"],
                "mode": managed.mode,
            },
        )
        return {"session": managed.to_dict(), "authorization": permit}

    def close_session(self, args: dict[str, Any]) -> dict[str, Any]:
        session_id = str(args.get("sessionId", "")).strip()
        permit_token = str(args.get("permitToken", ""))
        idempotency_key = str(args.get("idempotencyKey", "")).strip()
        managed = self.components.sessions.get(session_id)
        snapshot = managed.adapter.snapshot()
        permit = self._consume_session_permit(
            session_id=session_id,
            action_type="session_close",
            target_url=snapshot.url,
            permit_token=permit_token,
            idempotency_key=idempotency_key,
        )
        closed = self.components.sessions.close(session_id)
        self.components.evidence.append(
            "SESSION_CLOSED",
            f"session:{session_id}",
            {"session_id": session_id, "permit_id": permit["permit_id"]},
        )
        return {"session_id": session_id, "closed": closed, "authorization": permit}

    def preflight(self, args: dict[str, Any], *, forced_action: str | None = None) -> dict[str, Any]:
        request = self._action_request(args, forced_action=forced_action)
        route = self._route_request(request)
        self.components.reconciliation.require_fallback_reconciled(request)
        result = self.components.orchestrator.preflight(request)
        output: dict[str, Any] = result.to_dict()
        output["engine_route"] = route
        permit_token = args.get("permitToken")
        if permit_token and result.job.decision.allowed:
            authorized = self.components.orchestrator.authorize(
                result.job.job_id,
                permit_token=str(permit_token),
                approval_token=(str(args["approvalToken"]) if args.get("approvalToken") else None),
            )
            output["job"] = authorized.to_dict()
            if bool(args.get("commit", False)):
                receipt = self.commit(
                    {"jobId": authorized.job_id, "sessionId": request.session_id}
                )
                output["receipt"] = receipt
        return output

    def authorize(self, args: dict[str, Any]) -> dict[str, Any]:
        job = self.components.orchestrator.authorize(
            str(args.get("jobId", "")),
            permit_token=str(args.get("permitToken", "")),
            approval_token=(str(args["approvalToken"]) if args.get("approvalToken") else None),
        )
        return {"job": job.to_dict()}

    def commit(self, args: dict[str, Any]) -> dict[str, Any]:
        job_id = str(args.get("jobId", ""))
        session_id = str(args.get("sessionId", ""))
        job = self.components.store.get(job_id)
        if job.request.session_id != session_id:
            raise ControlPlaneError(
                FailureCode.BLOCKED_SESSION_BINDING_MISMATCH,
                "Job belongs to a different browser session",
                {"job_session_id": job.request.session_id, "requested_session_id": session_id},
            )
        session = self.components.sessions.get(session_id)
        if job.request.engine is EngineKind.PLAYWRIGHT:
            adapter = session.adapter
        else:
            factory = self.components.engine_adapter_factories.get(job.request.engine)
            if factory is None:
                code = (
                    FailureCode.BLOCKED_JEV_EXECUTOR_UNAVAILABLE
                    if job.request.engine is EngineKind.JEV
                    else FailureCode.BLOCKED_CUA_EXECUTOR_UNAVAILABLE
                )
                raise ControlPlaneError(
                    code,
                    "The selected engine has no separately registered host-owned executor",
                    {"engine": job.request.engine.value},
                )
            adapter = factory(session)
        # Do not create an uncertain-side-effect record until a real trusted
        # executor has been selected.  A missing executor cannot have issued a
        # browser mutation and must not poison an unrelated fallback path.
        if is_possible_mutation(job.request):
            self.components.reconciliation.record_possible_mutation(
                job_id=job.job_id,
                request=job.request,
                engine=job.request.engine,
            )
        receipt = self.components.orchestrator.run(job_id, adapter)
        if receipt.state in {
            JobState.SUCCEEDED,
            JobState.ROLLED_BACK,
            JobState.BLOCKED,
            JobState.CANCELLED,
        }:
            self.components.reconciliation.mark_terminal_safe(job.job_id)
        return {"receipt": receipt.to_dict()}

    def _consume_job_read_permit(
        self, args: dict[str, Any], *, action_type: str, job_id: str
    ) -> dict[str, Any]:
        job = self.components.store.get(job_id)
        token = str(args.get("permitToken", ""))
        idempotency_key = str(args.get("idempotencyKey", "")).strip()
        if not token or not idempotency_key:
            raise ValueError("permitToken and idempotencyKey are required")
        return self._consume_session_permit(
            session_id=job.request.session_id,
            action_type=action_type,
            target_url=job.request.target_url,
            permit_token=token,
            idempotency_key=idempotency_key,
        )

    def get_job(self, args: dict[str, Any]) -> dict[str, Any]:
        job_id = str(args.get("jobId", ""))
        authorization = self._consume_job_read_permit(
            args, action_type="job_get", job_id=job_id
        )
        return {"job": self.components.store.get(job_id).to_dict(), "authorization": authorization}

    def cancel_job(self, args: dict[str, Any]) -> dict[str, Any]:
        job_id = str(args.get("jobId", ""))
        authorization = self._consume_job_read_permit(
            args, action_type="job_cancel", job_id=job_id
        )
        receipt = self.components.orchestrator.cancel(job_id)
        return {"receipt": receipt.to_dict(), "authorization": authorization}

    def get_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        job_id = str(args.get("jobId", ""))
        authorization = self._consume_job_read_permit(
            args, action_type="evidence_get", job_id=job_id
        )
        limit = min(max(int(args.get("limit", 100)), 1), 500)
        return {
            "verification": self.components.evidence.verify().to_dict(),
            "events": self.components.evidence.read_events(job_id=job_id, limit=limit),
            "authorization": authorization,
        }

    def issue_permit(self, args: dict[str, Any]) -> dict[str, Any]:
        token = self.components.permits.issue(
            subject=self.components.settings.host_subject,
            session_id=str(args["session_id"]),
            allowed_actions=list(args["allowed_actions"]),
            exact_hosts=list(args["exact_hosts"]),
            risk_ceiling=RiskTier(int(args["risk_ceiling"])),
            max_calls=int(args["max_calls"]),
            max_cost=float(args.get("max_cost", 0.0)),
            currency=str(args.get("currency", self.components.settings.currency)),
            ttl_seconds=int(args.get("ttl_seconds", 300)),
        )
        claims = self.components.permits.codec.decode(token, expected_kind="permit")
        return {"token": token, "claims": self.redactor.redact(claims)}

    def issue_approval(self, args: dict[str, Any]) -> dict[str, Any]:
        job = self.components.store.get(str(args["job_id"]))
        confirmed_digest = str(args.get("confirm_action_digest", ""))
        if not confirmed_digest or confirmed_digest != job.decision.action_digest:
            raise ControlPlaneError(
                FailureCode.BLOCKED_APPROVAL_INVALID,
                "Operator confirmation digest does not match the durable action digest",
                {"job_id": job.job_id, "expected_action_digest": job.decision.action_digest},
            )
        confirmed_revision = args.get("confirm_page_revision")
        if confirmed_revision is not None and confirmed_revision != job.request.page_revision:
            raise ControlPlaneError(
                FailureCode.BLOCKED_STALE_PAGE_REVISION,
                "Operator-confirmed page revision does not match the durable request",
            )
        kind = ApprovalKind(str(args.get("approval_kind", job.decision.approval_kind.value)))
        token = self.components.approvals.issue(
            job_id=job.job_id,
            action_digest=job.decision.action_digest,
            approval_kind=kind,
            approvers=list(args["approvers"]),
            ttl_seconds=int(args.get("ttl_seconds", 120)),
        )
        claims = self.components.approvals.codec.decode(token, expected_kind="approval")
        return {"token": token, "claims": self.redactor.redact(claims)}
