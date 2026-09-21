from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .cua_binding import CuaBinding, CUA_MINIMUM_VALIDATED_VERSION, version_is_at_least
from .errors import ControlPlaneError, FailureCode
from .models import ActionRequest, EngineKind


_JEV_UNSUPPORTED_FEATURES = frozenset(
    {
        "iframe",
        "iframes",
        "shadow_root",
        "shadow-root",
        "canvas",
        "upload",
        "file_upload",
        "popup",
        "popups",
        "nested_scroll",
        "nested-scroll",
        "arbitrary_keyboard",
        "arbitrary-keyboard",
    }
)
_LOOPBACK_FIXTURE_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_CUA_OPERATION_BY_ACTION = {
    "inspect": "SNAPSHOT",
    "screenshot": "SNAPSHOT",
    "navigate": "NAVIGATE",
    "click": "CLICK",
    "type": "TYPE_TEXT",
    "select": "SELECT",
    "scroll": "SCROLL",
    "wait": "WAIT",
}


@dataclass(frozen=True, slots=True)
class EngineRoute:
    requested: EngineKind
    selected: EngineKind | None
    allowed: bool
    reason: str
    failure_code: FailureCode | None = None
    flags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "requested": self.requested.value,
            "selected": self.selected.value if self.selected else None,
            "allowed": self.allowed,
            "reason": self.reason,
            "failure_code": self.failure_code.value if self.failure_code else None,
            "flags": list(self.flags),
        }

    def require_allowed(self) -> EngineKind:
        if not self.allowed or self.selected is None:
            raise ControlPlaneError(
                self.failure_code or FailureCode.FAILED_INTERNAL,
                self.reason,
                {"route": self.to_dict()},
            )
        return self.selected


@dataclass(frozen=True, slots=True)
class EnginePolicy:
    engine_preference: EngineKind = EngineKind.AUTO
    jev_enabled: bool = False
    jev_public_hosts: frozenset[str] = frozenset()
    jev_external_model_egress_enabled: bool = False
    jev_runtime_authorization_id: str | None = None
    cua_enabled: bool = False
    cua_driver_version: str | None = None
    cua_minimum_validated_version: str = CUA_MINIMUM_VALIDATED_VERSION


class EngineRouter:
    """Fail-closed engine selection.

    This object only selects a permitted execution lane.  It does not turn a
    configuration preference, page text, or an engine request into authority.
    Jev and CUA must separately have a trusted executor/binding.
    """

    def __init__(self, policy: EnginePolicy) -> None:
        self.policy = policy

    @staticmethod
    def _host(url: str) -> str:
        return (urlsplit(url).hostname or "").rstrip(".").lower()

    @staticmethod
    def _payload_features(request: ActionRequest) -> set[str]:
        raw = request.payload.get("page_features", request.payload.get("unsupported_features", ()))
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, (list, tuple, set, frozenset)):
            return set()
        return {str(item).strip().lower() for item in raw}

    def _blocked(
        self,
        requested: EngineKind,
        code: FailureCode,
        reason: str,
        *flags: str,
    ) -> EngineRoute:
        return EngineRoute(requested, None, False, reason, code, tuple(flags))

    def _resolve_jev(self, request: ActionRequest, *, session_mode: str) -> EngineRoute:
        if not self.policy.jev_enabled:
            return self._blocked(
                EngineKind.JEV,
                FailureCode.BLOCKED_JEV_DISABLED,
                "Jev is disabled until an isolated runtime is explicitly configured",
            )
        if session_mode != "isolated":
            return self._blocked(
                EngineKind.JEV,
                FailureCode.BLOCKED_JEV_EXISTING_PERSONAL_PROFILE_DEFAULT_DENY,
                "Jev requires a WBCP-owned isolated browser session",
            )
        if bool(request.payload.get("authenticated_page")):
            return self._blocked(
                EngineKind.JEV,
                FailureCode.BLOCKED_JEV_AUTHENTICATED_PAGE_DEFAULT_DENY,
                "Jev is default-deny on authenticated pages",
            )
        if bool(request.payload.get("sensitive_page")):
            return self._blocked(
                EngineKind.JEV,
                FailureCode.BLOCKED_JEV_SENSITIVE_PAGE_DEFAULT_DENY,
                "Jev is default-deny on sensitive pages",
            )
        if bool(request.payload.get("existing_personal_profile")):
            return self._blocked(
                EngineKind.JEV,
                FailureCode.BLOCKED_JEV_EXISTING_PERSONAL_PROFILE_DEFAULT_DENY,
                "Jev cannot attach to an existing personal browser profile",
            )
        unsupported = self._payload_features(request) & _JEV_UNSUPPORTED_FEATURES
        if unsupported:
            return self._blocked(
                EngineKind.JEV,
                FailureCode.BLOCKED_JEV_UNSUPPORTED_FEATURE,
                "Jev cannot operate on the declared unsupported page feature",
                *sorted(unsupported),
            )

        host = self._host(request.target_url)
        public_hosts = {value.rstrip(".").lower() for value in self.policy.jev_public_hosts}
        local_fixture = bool(request.payload.get("isolated_local_fixture"))
        if host in _LOOPBACK_FIXTURE_HOSTS:
            if not local_fixture:
                return self._blocked(
                    EngineKind.JEV,
                    FailureCode.BLOCKED_JEV_TARGET_NOT_EXACT_PUBLIC_HOST,
                    "Loopback Jev targets are allowed only for an explicitly declared isolated fixture",
                )
        elif host not in public_hosts:
            return self._blocked(
                EngineKind.JEV,
                FailureCode.BLOCKED_JEV_TARGET_NOT_EXACT_PUBLIC_HOST,
                "Jev target host is not in the exact public-host allowlist",
            )

        if bool(request.payload.get("external_model_egress")):
            # A loopback fixture can exercise route eligibility without an
            # outbound provider call, but it can never become an egress
            # authorization target.  The host must be one of the same exact
            # public destinations already approved for Jev itself.
            if host in _LOOPBACK_FIXTURE_HOSTS or host not in public_hosts:
                return self._blocked(
                    EngineKind.JEV,
                    FailureCode.BLOCKED_JEV_TARGET_NOT_EXACT_PUBLIC_HOST,
                    "External Jev model egress requires an exact approved public host",
                )
            if not self.policy.jev_external_model_egress_enabled:
                return self._blocked(
                    EngineKind.JEV,
                    FailureCode.BLOCKED_JEV_EXTERNAL_MODEL_EGRESS_DEFAULT_DENY,
                    "External Jev model egress is default-deny",
                )
            if not self.policy.jev_runtime_authorization_id:
                return self._blocked(
                    EngineKind.JEV,
                    FailureCode.BLOCKED_JEV_RUNTIME_AUTHORIZATION_REQUIRED,
                    "External Jev model egress needs an independent runtime authorization",
                )
        return EngineRoute(
            EngineKind.JEV,
            EngineKind.JEV,
            True,
            "Jev route is eligible; execution still requires a separately registered Jev executor",
            flags=("JEV_DONE_REQUIRES_INDEPENDENT_VERIFIER",),
        )

    def _resolve_cua(
        self, request: ActionRequest, *, binding: CuaBinding | None
    ) -> EngineRoute:
        if not self.policy.cua_enabled:
            return self._blocked(
                EngineKind.CUA,
                FailureCode.BLOCKED_CUA_DISABLED,
                "CUA is disabled until the Driver and a bound session are explicitly configured",
            )
        if not version_is_at_least(
            self.policy.cua_driver_version, self.policy.cua_minimum_validated_version
        ):
            return self._blocked(
                EngineKind.CUA,
                FailureCode.BLOCKED_CUA_DRIVER_BELOW_MINIMUM_VALIDATED_REFERENCE,
                "CUA Driver is below the minimum validated stable reference",
            )
        if binding is None or binding.session_id != request.session_id:
            return self._blocked(
                EngineKind.CUA,
                FailureCode.BLOCKED_CUA_SESSION_BINDING_MISMATCH,
                "No exact host-owned CUA binding exists for this browser session",
            )
        operation = _CUA_OPERATION_BY_ACTION.get(request.action_type)
        if operation is None:
            return self._blocked(
                EngineKind.CUA,
                FailureCode.BLOCKED_CUA_OPERATION_NOT_ALLOWLISTED,
                "Action has no CUA typed-tool allowlist mapping",
            )
        try:
            binding.validate_operation(
                operation=operation,
                target_url=request.target_url,
                arguments=request.payload,
            )
        except ControlPlaneError as exc:
            return self._blocked(EngineKind.CUA, exc.code, exc.message)
        return EngineRoute(
            EngineKind.CUA,
            EngineKind.CUA,
            True,
            "CUA route is eligible under an exact host-owned binding",
        )

    def resolve(
        self,
        request: ActionRequest,
        *,
        session_mode: str = "isolated",
        cua_binding: CuaBinding | None = None,
    ) -> EngineRoute:
        requested = request.engine
        if requested is EngineKind.AUTO:
            return EngineRoute(
                requested,
                EngineKind.PLAYWRIGHT,
                True,
                "AUTO preserves deterministic Playwright as the primary known-flow route",
                flags=("ENGINE_PREFERENCE_NOT_AUTHORITY",),
            )
        if requested is EngineKind.PLAYWRIGHT:
            return EngineRoute(
                requested,
                EngineKind.PLAYWRIGHT,
                True,
                "Playwright is the deterministic primary route",
            )
        if requested is EngineKind.JEV:
            return self._resolve_jev(request, session_mode=session_mode)
        if requested is EngineKind.CUA:
            return self._resolve_cua(request, binding=cua_binding)
        return self._blocked(
            requested,
            FailureCode.BLOCKED_HIGH_RISK_ACTION_DISABLED,
            "Unknown engine is not enabled",
        )

    def health(self) -> dict[str, object]:
        return {
            "engine_preference": self.policy.engine_preference.value,
            "auto_primary": EngineKind.PLAYWRIGHT.value,
            "jev": {
                "enabled": self.policy.jev_enabled,
                "public_hosts": sorted(self.policy.jev_public_hosts),
                "external_model_egress_default": "DENY",
                "done_requires_independent_verifier": True,
            },
            "cua": {
                "enabled": self.policy.cua_enabled,
                "driver_version": self.policy.cua_driver_version,
                "minimum_validated_version": self.policy.cua_minimum_validated_version,
                "bounded_mode_required": True,
            },
        }
