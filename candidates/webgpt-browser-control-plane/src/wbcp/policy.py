from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from .errors import FailureCode
from .models import ActionRequest, ApprovalKind, AuthoritySource, PolicyDecision, RiskTier
from .redaction import Redactor
from .url_guard import ValidatedURL


_RISK_BY_ACTION: dict[str, RiskTier] = {
    # R0: observation only
    "health": RiskTier.R0_READ_ONLY,
    "inspect": RiskTier.R0_READ_ONLY,
    "query": RiskTier.R0_READ_ONLY,
    "screenshot": RiskTier.R0_READ_ONLY,
    "read_network": RiskTier.R0_READ_ONLY,
    "read_console": RiskTier.R0_READ_ONLY,
    "job_get": RiskTier.R0_READ_ONLY,
    "evidence_get": RiskTier.R0_READ_ONLY,
    "session_create": RiskTier.R1_LOCAL_REVERSIBLE,
    "session_close": RiskTier.R1_LOCAL_REVERSIBLE,
    "job_cancel": RiskTier.R1_LOCAL_REVERSIBLE,
    # R1: local/reversible browser state
    "navigate": RiskTier.R1_LOCAL_REVERSIBLE,
    "scroll": RiskTier.R1_LOCAL_REVERSIBLE,
    "focus": RiskTier.R1_LOCAL_REVERSIBLE,
    "switch_tab": RiskTier.R1_LOCAL_REVERSIBLE,
    "open_tab": RiskTier.R1_LOCAL_REVERSIBLE,
    "close_tab": RiskTier.R1_LOCAL_REVERSIBLE,
    "wait": RiskTier.R1_LOCAL_REVERSIBLE,
    # R2: reversible or draft remote mutation
    "type": RiskTier.R2_REMOTE_REVERSIBLE,
    "select": RiskTier.R2_REMOTE_REVERSIBLE,
    "upload_staged": RiskTier.R2_REMOTE_REVERSIBLE,
    "download": RiskTier.R2_REMOTE_REVERSIBLE,
    "create_draft": RiskTier.R2_REMOTE_REVERSIBLE,
    "edit_draft": RiskTier.R2_REMOTE_REVERSIBLE,
    "add_to_cart": RiskTier.R2_REMOTE_REVERSIBLE,
    "checkpoint": RiskTier.R2_REMOTE_REVERSIBLE,
    # R3: consequential external effect
    "submit": RiskTier.R3_CONSEQUENTIAL,
    "send": RiskTier.R3_CONSEQUENTIAL,
    "publish": RiskTier.R3_CONSEQUENTIAL,
    "comment": RiskTier.R3_CONSEQUENTIAL,
    "book": RiskTier.R3_CONSEQUENTIAL,
    "reserve": RiskTier.R3_CONSEQUENTIAL,
    "start_paid_generation": RiskTier.R3_CONSEQUENTIAL,
    "commit_upload": RiskTier.R3_CONSEQUENTIAL,
    "create_external_resource": RiskTier.R3_CONSEQUENTIAL,
    # R4: irreversible/account/payment/legal
    "purchase": RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT,
    "payment": RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT,
    "transfer": RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT,
    "delete": RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT,
    "account_security_change": RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT,
    "permission_change": RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT,
    "accept_legal_terms": RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT,
    "identity_verification": RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT,
    # R5: never automate
    "captcha_bypass": RiskTier.R5_PROHIBITED,
    "extract_credentials": RiskTier.R5_PROHIBITED,
    "disable_security": RiskTier.R5_PROHIBITED,
    "malware_action": RiskTier.R5_PROHIBITED,
    "bulk_destructive_action": RiskTier.R5_PROHIBITED,
}

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore\s+(?:all\s+)?previous\s+instructions",
        r"reveal\s+(?:the\s+)?(?:system|developer)\s+(?:prompt|message)",
        r"send\s+(?:your|the)\s+(?:password|token|cookie|secret)",
        r"disable\s+(?:the\s+)?(?:safety|guardrail|approval)",
        r"call\s+(?:this|the)\s+tool\s+without\s+approval",
        r"you\s+are\s+now\s+(?:an?|the)\s+system",
        r"exfiltrat(?:e|ion)",
    )
)


@dataclass(slots=True)
class PolicyConfig:
    r4_mode: str = "block"  # block | dual_control
    require_known_cost_actions: set[str] = field(
        default_factory=lambda: {"start_paid_generation", "purchase", "payment", "transfer"}
    )
    maximum_action_cost: float = 100.0
    currency: str = "USD"
    block_web_content_authority: bool = True
    block_secret_shaped_payloads: bool = True
    allowed_action_types: set[str] = field(default_factory=lambda: set(_RISK_BY_ACTION))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyConfig":
        return cls(
            r4_mode=str(data.get("r4_mode", "block")),
            require_known_cost_actions=set(data.get("require_known_cost_actions", [])),
            maximum_action_cost=float(data.get("maximum_action_cost", 100.0)),
            currency=str(data.get("currency", "USD")).upper(),
            block_web_content_authority=bool(data.get("block_web_content_authority", True)),
            block_secret_shaped_payloads=bool(data.get("block_secret_shaped_payloads", True)),
            allowed_action_types=set(data.get("allowed_action_types", _RISK_BY_ACTION.keys())),
        )


class PromptInjectionDetector:
    def detect(self, text: str) -> list[str]:
        return [pattern.pattern for pattern in _INJECTION_PATTERNS if pattern.search(text)]


class PolicyEngine:
    def __init__(self, config: PolicyConfig | None = None) -> None:
        self.config = config or PolicyConfig()
        self.detector = PromptInjectionDetector()
        self.redactor = Redactor()

    @staticmethod
    def classify(action_type: str) -> RiskTier:
        return _RISK_BY_ACTION.get(action_type.strip().lower(), RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT)

    @staticmethod
    def _approval_for(risk: RiskTier) -> ApprovalKind:
        return {
            RiskTier.R0_READ_ONLY: ApprovalKind.SESSION,
            RiskTier.R1_LOCAL_REVERSIBLE: ApprovalKind.SESSION,
            RiskTier.R2_REMOTE_REVERSIBLE: ApprovalKind.FINITE_WRITE,
            RiskTier.R3_CONSEQUENTIAL: ApprovalKind.HIGH_IMPACT,
            RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT: ApprovalKind.DUAL_CONTROL,
            RiskTier.R5_PROHIBITED: ApprovalKind.DUAL_CONTROL,
        }[risk]

    @staticmethod
    def _required_signals(risk: RiskTier) -> int:
        return 3 if risk >= RiskTier.R3_CONSEQUENTIAL else 2

    @staticmethod
    def _digest(request: ActionRequest, validated_url: ValidatedURL) -> str:
        payload = {
            "request_fingerprint": request.fingerprint(),
            "normalized_url": validated_url.normalized,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def _blocked(
        self,
        *,
        risk: RiskTier,
        approval: ApprovalKind,
        required_signals: int,
        reason: str,
        action_digest: str,
        code: FailureCode,
        flags: list[str] | None = None,
    ) -> PolicyDecision:
        return PolicyDecision(
            False,
            risk,
            approval,
            required_signals,
            reason,
            action_digest,
            code.value,
            flags or [],
        )

    def evaluate(self, request: ActionRequest, validated_url: ValidatedURL) -> PolicyDecision:
        risk = self.classify(request.action_type)
        approval = self._approval_for(risk)
        required = self._required_signals(risk)
        digest = self._digest(request, validated_url)
        flags: list[str] = []

        if request.action_type not in self.config.allowed_action_types:
            return self._blocked(
                risk=risk,
                approval=approval,
                required_signals=required,
                reason="Action type is not enabled by policy",
                action_digest=digest,
                code=FailureCode.BLOCKED_HIGH_RISK_ACTION_DISABLED,
            )

        if risk == RiskTier.R5_PROHIBITED:
            return self._blocked(
                risk=risk,
                approval=approval,
                required_signals=required,
                reason="This action class is prohibited and cannot be approved",
                action_digest=digest,
                code=FailureCode.BLOCKED_PROHIBITED_ACTION,
            )

        if self.config.block_web_content_authority and request.authority_source == AuthoritySource.WEB_CONTENT:
            return self._blocked(
                risk=risk,
                approval=approval,
                required_signals=required,
                reason="Page content is untrusted data and cannot authorize browser actions",
                action_digest=digest,
                code=FailureCode.BLOCKED_PROMPT_INJECTION_SUSPECTED,
                flags=["WEB_CONTENT_AS_AUTHORITY"],
            )

        page_text = str(request.payload.get("page_instruction_text", ""))
        injection_hits = self.detector.detect(page_text)
        if injection_hits:
            flags.append("PROMPT_INJECTION_PATTERN")
            if request.authority_source != AuthoritySource.USER:
                return self._blocked(
                    risk=risk,
                    approval=approval,
                    required_signals=required,
                    reason="Untrusted page text contains instruction-override patterns",
                    action_digest=digest,
                    code=FailureCode.BLOCKED_PROMPT_INJECTION_SUSPECTED,
                    flags=flags,
                )

        field_type = str(request.payload.get("field_type", "")).lower()
        if field_type in {"password", "totp", "otp", "recovery_code", "private_key", "secret"}:
            return self._blocked(
                risk=risk,
                approval=approval,
                required_signals=required,
                reason="Authentication secrets must be entered directly by the user in the browser",
                action_digest=digest,
                code=FailureCode.BLOCKED_AUTH_CHALLENGE_REQUIRES_USER,
            )
        if bool(request.payload.get("captcha")):
            return self._blocked(
                risk=risk,
                approval=approval,
                required_signals=required,
                reason="CAPTCHA requires direct user completion",
                action_digest=digest,
                code=FailureCode.BLOCKED_CAPTCHA_REQUIRES_USER,
            )
        if self.config.block_secret_shaped_payloads and self.redactor.contains_secret_shape(request.payload):
            return self._blocked(
                risk=risk,
                approval=approval,
                required_signals=required,
                reason="Payload appears to contain a secret",
                action_digest=digest,
                code=FailureCode.BLOCKED_SECRET_EXPOSURE_RISK,
            )

        if request.action_type in self.config.require_known_cost_actions:
            if request.estimated_cost is None or not request.currency:
                return self._blocked(
                    risk=risk,
                    approval=approval,
                    required_signals=required,
                    reason="Consequential paid action has no exact cost and currency",
                    action_digest=digest,
                    code=FailureCode.BLOCKED_COST_UNKNOWN_OR_BUDGET_EXCEEDED,
                )
        if request.estimated_cost is not None:
            if request.estimated_cost > self.config.maximum_action_cost:
                return self._blocked(
                    risk=risk,
                    approval=approval,
                    required_signals=required,
                    reason="Action cost exceeds the policy maximum",
                    action_digest=digest,
                    code=FailureCode.BLOCKED_COST_UNKNOWN_OR_BUDGET_EXCEEDED,
                )
            if (request.currency or "").upper() != self.config.currency:
                return self._blocked(
                    risk=risk,
                    approval=approval,
                    required_signals=required,
                    reason="Action currency differs from policy currency",
                    action_digest=digest,
                    code=FailureCode.BLOCKED_COST_UNKNOWN_OR_BUDGET_EXCEEDED,
                )

        if risk == RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT and self.config.r4_mode != "dual_control":
            return self._blocked(
                risk=risk,
                approval=approval,
                required_signals=required,
                reason="R4 actions are disabled by default",
                action_digest=digest,
                code=FailureCode.BLOCKED_HIGH_RISK_ACTION_DISABLED,
            )

        reason = {
            RiskTier.R0_READ_ONLY: "Read-only action requires a finite session permit",
            RiskTier.R1_LOCAL_REVERSIBLE: "Local reversible action requires a finite session permit",
            RiskTier.R2_REMOTE_REVERSIBLE: "Remote mutation requires an exact finite write permit",
            RiskTier.R3_CONSEQUENTIAL: "Consequential action requires finite permit plus one-shot approval",
            RiskTier.R4_IRREVERSIBLE_OR_ACCOUNT: "R4 action requires explicit dual control",
        }[risk]
        return PolicyDecision(True, risk, approval, required, reason, digest, flags=flags)
