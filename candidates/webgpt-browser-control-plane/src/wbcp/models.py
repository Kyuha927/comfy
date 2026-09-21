from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import IntEnum, StrEnum
from typing import Any


class RiskTier(IntEnum):
    R0_READ_ONLY = 0
    R1_LOCAL_REVERSIBLE = 1
    R2_REMOTE_REVERSIBLE = 2
    R3_CONSEQUENTIAL = 3
    R4_IRREVERSIBLE_OR_ACCOUNT = 4
    R5_PROHIBITED = 5


class JobState(StrEnum):
    CREATED = "CREATED"
    PREFLIGHTED = "PREFLIGHTED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    AUTHORIZED = "AUTHORIZED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"
    QUARANTINED = "QUARANTINED"


class AuthoritySource(StrEnum):
    USER = "USER"
    POLICY = "POLICY"
    MODEL_PROPOSAL = "MODEL_PROPOSAL"
    WEB_CONTENT = "WEB_CONTENT"


class ApprovalKind(StrEnum):
    NONE = "NONE"
    SESSION = "SESSION"
    FINITE_WRITE = "FINITE_WRITE"
    HIGH_IMPACT = "HIGH_IMPACT"
    DUAL_CONTROL = "DUAL_CONTROL"


class EngineKind(StrEnum):
    """Execution engines understood by the WBCP router.

    ``AUTO`` is deliberately conservative: it always resolves to the
    deterministic Playwright path.  A preference is observability only, never
    an authority grant for Jev or CUA.
    """

    AUTO = "AUTO"
    PLAYWRIGHT = "PLAYWRIGHT"
    JEV = "JEV"
    CUA = "CUA"


@dataclass(slots=True)
class ActionRequest:
    session_id: str
    idempotency_key: str
    action_type: str
    target_url: str
    engine: EngineKind = EngineKind.AUTO
    payload: dict[str, Any] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)
    authority_source: AuthoritySource = AuthoritySource.MODEL_PROPOSAL
    page_revision: str | None = None
    estimated_cost: float | None = None
    currency: str | None = None
    reversible: bool = True
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requested_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.action_type = self.action_type.strip().lower()
        if not isinstance(self.engine, EngineKind):
            self.engine = EngineKind(str(self.engine).strip().upper())
        if not isinstance(self.authority_source, AuthoritySource):
            self.authority_source = AuthoritySource(str(self.authority_source))
        if not self.session_id.strip():
            raise ValueError("session_id must be non-empty")
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key must be non-empty")
        if not self.action_type:
            raise ValueError("action_type must be non-empty")
        if self.estimated_cost is not None:
            if not math.isfinite(self.estimated_cost) or self.estimated_cost < 0:
                raise ValueError("estimated_cost must be finite and non-negative")
        if self.currency is not None:
            self.currency = self.currency.upper().strip()

    def stable_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "idempotency_key": self.idempotency_key,
            "action_type": self.action_type,
            "target_url": self.target_url,
            "engine": self.engine.value,
            "payload": self.payload,
            "expected": self.expected,
            "authority_source": self.authority_source.value,
            "page_revision": self.page_revision,
            "estimated_cost": self.estimated_cost,
            "currency": self.currency,
            "reversible": self.reversible,
        }

    def fingerprint(self) -> str:
        body = json.dumps(
            self.stable_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(body).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["authority_source"] = self.authority_source.value
        data["engine"] = self.engine.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionRequest":
        copy = dict(data)
        copy["authority_source"] = AuthoritySource(copy.get("authority_source", "MODEL_PROPOSAL"))
        copy["engine"] = EngineKind(copy.get("engine", EngineKind.AUTO.value))
        return cls(**copy)


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    risk: RiskTier
    approval_kind: ApprovalKind
    required_signals: int
    reason: str
    action_digest: str
    failure_code: str | None = None
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk": int(self.risk),
            "risk_name": self.risk.name,
            "approval_kind": self.approval_kind.value,
            "required_signals": self.required_signals,
            "reason": self.reason,
            "action_digest": self.action_digest,
            "failure_code": self.failure_code,
            "flags": list(self.flags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyDecision":
        return cls(
            allowed=bool(data["allowed"]),
            risk=RiskTier(int(data["risk"])),
            approval_kind=ApprovalKind(data["approval_kind"]),
            required_signals=int(data["required_signals"]),
            reason=str(data["reason"]),
            action_digest=str(data["action_digest"]),
            failure_code=data.get("failure_code"),
            flags=list(data.get("flags", [])),
        )


@dataclass(slots=True)
class BrowserSnapshot:
    url: str
    revision: str
    dom_digest: str
    screenshot_digest: str
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SignalBundle:
    dom_ok: bool
    pixel_ok: bool
    network_ok: bool
    provider_receipt: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def passing_count(self) -> int:
        return sum((self.dom_ok, self.pixel_ok, self.network_ok))

    @property
    def all_three(self) -> bool:
        return self.dom_ok and self.pixel_ok and self.network_ok

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutionResult:
    before: BrowserSnapshot
    after: BrowserSnapshot
    signals: SignalBundle
    output: dict[str, Any] = field(default_factory=dict)
    rollback_token: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "signals": self.signals.to_dict(),
            "output": self.output,
            # Rollback tokens may contain browser handles or sensitive state and are
            # intentionally never persisted in receipts or evidence.
            "rollback_available": self.rollback_token is not None,
        }


@dataclass(slots=True)
class ActionReceipt:
    job_id: str
    state: JobState
    risk: RiskTier
    action_digest: str
    evidence_root: str
    result: dict[str, Any] = field(default_factory=dict)
    failure_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "state": self.state.value,
            "risk": int(self.risk),
            "risk_name": self.risk.name,
            "action_digest": self.action_digest,
            "evidence_root": self.evidence_root,
            "result": self.result,
            "failure_code": self.failure_code,
        }
