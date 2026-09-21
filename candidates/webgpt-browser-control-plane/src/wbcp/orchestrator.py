from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .errors import ControlPlaneError, FailureCode
from .evidence import EvidenceLedger
from .models import (
    ActionReceipt,
    ActionRequest,
    ApprovalKind,
    BrowserSnapshot,
    ExecutionResult,
    EngineKind,
    JobState,
    RiskTier,
)
from .permits import ApprovalAuthority, PermitAuthority
from .policy import PolicyEngine
from .store import JobRecord, JobStore
from .url_guard import URLGuard


class BrowserAdapter(Protocol):
    def snapshot(self) -> BrowserSnapshot: ...

    def execute(self, request: ActionRequest) -> ExecutionResult: ...

    def rollback(self, rollback_token: dict[str, Any]) -> bool: ...


@dataclass(slots=True)
class PreflightResult:
    job: JobRecord
    created: bool

    def to_dict(self) -> dict[str, Any]:
        return {"job": self.job.to_dict(), "created": self.created}


class JobOrchestrator:
    def __init__(
        self,
        *,
        url_guard: URLGuard,
        policy: PolicyEngine,
        permits: PermitAuthority,
        approvals: ApprovalAuthority,
        store: JobStore,
        evidence: EvidenceLedger,
        host_subject: str,
    ) -> None:
        self.url_guard = url_guard
        self.policy = policy
        self.permits = permits
        self.approvals = approvals
        self.store = store
        self.evidence = evidence
        self.host_subject = host_subject

    def preflight(self, request: ActionRequest) -> PreflightResult:
        validated = self.url_guard.validate(request.target_url)
        request.target_url = validated.normalized
        decision = self.policy.evaluate(request, validated)
        job, created = self.store.create_or_get(request, decision)
        if not created:
            return PreflightResult(job, False)

        self.evidence.append(
            "PREFLIGHT",
            job.job_id,
            {
                "request": request.to_dict(),
                "decision": decision.to_dict(),
                "normalized_url": validated.normalized,
            },
        )
        if not decision.allowed:
            blocked = self.store.transition(
                job.job_id,
                expected_states={JobState.CREATED},
                new_state=JobState.BLOCKED,
                expected_revision=job.revision,
                error_code=decision.failure_code,
            )
            self.evidence.append(
                "BLOCKED",
                job.job_id,
                {"failure_code": decision.failure_code, "reason": decision.reason},
            )
            return PreflightResult(blocked, True)

        preflighted = self.store.transition(
            job.job_id,
            expected_states={JobState.CREATED},
            new_state=JobState.PREFLIGHTED,
            expected_revision=job.revision,
        )
        if decision.approval_kind in {
            ApprovalKind.FINITE_WRITE,
            ApprovalKind.HIGH_IMPACT,
            ApprovalKind.DUAL_CONTROL,
        }:
            awaiting = self.store.transition(
                job.job_id,
                expected_states={JobState.PREFLIGHTED},
                new_state=JobState.AWAITING_APPROVAL,
                expected_revision=preflighted.revision,
            )
            return PreflightResult(awaiting, True)
        return PreflightResult(preflighted, True)

    def authorize(
        self,
        job_id: str,
        *,
        permit_token: str,
        approval_token: str | None = None,
    ) -> JobRecord:
        job = self.store.get(job_id)
        if job.state == JobState.AUTHORIZED:
            return job
        if job.state not in {JobState.PREFLIGHTED, JobState.AWAITING_APPROVAL}:
            raise ControlPlaneError(
                FailureCode.BLOCKED_ILLEGAL_STATE_TRANSITION,
                "Job is not waiting for authorization",
                {"state": job.state.value},
            )

        # Validate both credentials before consuming either. The registry then
        # commits the permit and optional one-shot approval in one transaction.
        permit = self.permits.validate(
            permit_token,
            request=job.request,
            risk=job.risk,
            expected_subject=self.host_subject,
        )
        approval_claims: dict[str, Any] | None = None
        required = job.decision.approval_kind
        if required in {ApprovalKind.HIGH_IMPACT, ApprovalKind.DUAL_CONTROL}:
            if not approval_token:
                code = (
                    FailureCode.BLOCKED_PENDING_HIGH_IMPACT_APPROVAL
                    if required == ApprovalKind.HIGH_IMPACT
                    else FailureCode.BLOCKED_PENDING_DUAL_CONTROL_APPROVAL
                )
                raise ControlPlaneError(code, "One-shot approval token is required")
            approval_claims = self.approvals.validate(
                approval_token,
                job_id=job.job_id,
                action_digest=job.decision.action_digest,
                required_kind=required,
            )

        if self.permits.registry is not self.approvals.registry:
            raise ControlPlaneError(
                FailureCode.FAILED_INTERNAL,
                "Permit and approval authorities must share one atomic registry",
            )
        permit.usage = self.permits.registry.consume_authorization(
            permit_id=permit.permit_id,
            idempotency_key=job.request.idempotency_key,
            amount=float(job.request.estimated_cost or 0.0),
            max_calls=int(permit.claims["max_calls"]),
            max_cost=float(permit.claims["max_cost"]),
            approval_id=str(approval_claims["jti"]) if approval_claims else None,
            approval_job_id=job.job_id if approval_claims else None,
        )

        authorized = self.store.transition(
            job.job_id,
            expected_states={job.state},
            new_state=JobState.AUTHORIZED,
            expected_revision=job.revision,
        )
        self.evidence.append(
            "AUTHORIZED",
            job.job_id,
            {
                "permit_id": permit.permit_id,
                "permit_usage": permit.usage,
                "approval_id": approval_claims.get("jti") if approval_claims else None,
                "approval_kind": required.value,
            },
        )
        return authorized

    @staticmethod
    def _signals_pass(job: JobRecord, result: ExecutionResult) -> bool:
        if job.request.engine is EngineKind.JEV and not bool(
            result.output.get("independent_verifier_passed")
        ):
            # Jev DONE is an executor claim, not a WBCP completion signal.
            return False
        if job.risk >= RiskTier.R3_CONSEQUENTIAL:
            return result.signals.all_three and bool(result.signals.provider_receipt)
        return result.signals.passing_count >= job.decision.required_signals

    def _receipt(self, job: JobRecord) -> ActionReceipt:
        root = self.evidence.root_hash()
        return ActionReceipt(
            job_id=job.job_id,
            state=job.state,
            risk=job.risk,
            action_digest=job.decision.action_digest,
            evidence_root=root,
            result=job.result or {},
            failure_code=job.error_code,
        )

    def run(self, job_id: str, adapter: BrowserAdapter) -> ActionReceipt:
        job = self.store.get(job_id)
        if job.state in {
            JobState.SUCCEEDED,
            JobState.ROLLED_BACK,
            JobState.BLOCKED,
            JobState.QUARANTINED,
            JobState.CANCELLED,
        }:
            return self._receipt(job)
        if job.state != JobState.AUTHORIZED:
            raise ControlPlaneError(
                FailureCode.BLOCKED_PENDING_FINITE_WRITE_PERMIT_OR_EXPLICIT_SESSION_AUTHORIZATION,
                "Job has not passed the finite authorization gate",
                {"state": job.state.value},
            )

        current_snapshot = adapter.snapshot()
        if job.request.page_revision and job.request.page_revision != current_snapshot.revision:
            blocked = self.store.transition(
                job.job_id,
                expected_states={JobState.AUTHORIZED},
                new_state=JobState.BLOCKED,
                expected_revision=job.revision,
                error_code=FailureCode.BLOCKED_STALE_PAGE_REVISION.value,
            )
            self.evidence.append(
                "BLOCKED_STALE_REVISION",
                job.job_id,
                {
                    "expected": job.request.page_revision,
                    "actual": current_snapshot.revision,
                },
            )
            return self._receipt(blocked)

        running = self.store.transition(
            job.job_id,
            expected_states={JobState.AUTHORIZED},
            new_state=JobState.RUNNING,
            expected_revision=job.revision,
        )
        self.evidence.append("RUNNING", job.job_id, {"snapshot": current_snapshot.to_dict()})

        try:
            execution = adapter.execute(job.request)
        except Exception as exc:  # noqa: BLE001 - execution boundary converts all failures
            failure_code = (
                exc.code.value
                if isinstance(exc, ControlPlaneError)
                else FailureCode.FAILED_BROWSER_EXECUTION.value
            )
            failure_payload = (
                exc.to_dict()
                if isinstance(exc, ControlPlaneError)
                else {"error_type": type(exc).__name__, "error": str(exc)}
            )
            failed = self.store.transition(
                job.job_id,
                expected_states={JobState.RUNNING},
                new_state=JobState.FAILED,
                expected_revision=running.revision,
                error_code=failure_code,
                result=failure_payload,
            )
            self.evidence.append(
                "EXECUTION_FAILED",
                job.job_id,
                failure_payload,
            )
            quarantined = self.store.transition(
                job.job_id,
                expected_states={JobState.FAILED},
                new_state=JobState.QUARANTINED,
                expected_revision=failed.revision,
                error_code=failure_code,
            )
            return self._receipt(quarantined)

        verifying = self.store.transition(
            job.job_id,
            expected_states={JobState.RUNNING},
            new_state=JobState.VERIFYING,
            expected_revision=running.revision,
            result=execution.to_dict(),
        )
        self.evidence.append(
            "VERIFYING",
            job.job_id,
            {
                "before": execution.before.to_dict(),
                "after": execution.after.to_dict(),
                "signals": execution.signals.to_dict(),
                "output": execution.output,
            },
        )

        if self._signals_pass(job, execution):
            succeeded = self.store.transition(
                job.job_id,
                expected_states={JobState.VERIFYING},
                new_state=JobState.SUCCEEDED,
                expected_revision=verifying.revision,
                result=execution.to_dict(),
            )
            self.evidence.append(
                "SUCCEEDED",
                job.job_id,
                {
                    "signals": execution.signals.to_dict(),
                    "after_revision": execution.after.revision,
                },
            )
            return self._receipt(succeeded)

        failed = self.store.transition(
            job.job_id,
            expected_states={JobState.VERIFYING},
            new_state=JobState.FAILED,
            expected_revision=verifying.revision,
            result=execution.to_dict(),
            error_code=FailureCode.BLOCKED_POSTCONDITION_UNVERIFIED.value,
        )
        self.evidence.append(
            "POSTCONDITION_FAILED",
            job.job_id,
            {
                "required_signals": job.decision.required_signals,
                "signals": execution.signals.to_dict(),
            },
        )

        if job.request.reversible and execution.rollback_token is not None:
            rollback_ok = False
            try:
                rollback_ok = adapter.rollback(execution.rollback_token)
            except Exception as exc:  # noqa: BLE001
                self.evidence.append(
                    "ROLLBACK_EXCEPTION",
                    job.job_id,
                    {"error_type": type(exc).__name__, "error": str(exc)},
                )
            if rollback_ok:
                rolled_back = self.store.transition(
                    job.job_id,
                    expected_states={JobState.FAILED},
                    new_state=JobState.ROLLED_BACK,
                    expected_revision=failed.revision,
                    error_code=FailureCode.BLOCKED_POSTCONDITION_UNVERIFIED.value,
                )
                self.evidence.append("ROLLED_BACK", job.job_id, {"verified": True})
                return self._receipt(rolled_back)

        quarantined = self.store.transition(
            job.job_id,
            expected_states={JobState.FAILED},
            new_state=JobState.QUARANTINED,
            expected_revision=failed.revision,
            error_code=(
                FailureCode.BLOCKED_ROLLBACK_UNAVAILABLE_FOR_REQUIRED_REVERSIBILITY.value
                if job.request.reversible
                else FailureCode.BLOCKED_POSTCONDITION_UNVERIFIED.value
            ),
        )
        self.evidence.append(
            "QUARANTINED",
            job.job_id,
            {"reason": quarantined.error_code},
        )
        return self._receipt(quarantined)

    def cancel(self, job_id: str) -> ActionReceipt:
        job = self.store.get(job_id)
        if job.state in {
            JobState.SUCCEEDED,
            JobState.ROLLED_BACK,
            JobState.BLOCKED,
            JobState.QUARANTINED,
            JobState.CANCELLED,
        }:
            return self._receipt(job)
        cancelled = self.store.transition(
            job.job_id,
            expected_states={job.state},
            new_state=JobState.CANCELLED,
            expected_revision=job.revision,
        )
        self.evidence.append("CANCELLED", job.job_id, {})
        return self._receipt(cancelled)
