from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from .errors import ControlPlaneError, FailureCode


CUA_MINIMUM_VALIDATED_VERSION = "0.28.2"
CUA_TYPED_OPERATION_ALLOWLIST = frozenset(
    {"SNAPSHOT", "NAVIGATE", "CLICK", "TYPE_TEXT", "SELECT", "SCROLL", "WAIT"}
)
_BINDING_ARGUMENT_NAMES = frozenset(
    {
        "session_id",
        "sessionId",
        "process_id",
        "processId",
        "pid",
        "window_id",
        "windowId",
        "target_id",
        "targetId",
        "tab_id",
        "tabId",
        "authorized_url",
        "authorizedUrl",
        "target_url",
        "targetUrl",
        "url",
        "profile_kind",
        "profileKind",
        "binding",
        "binding_id",
        "bindingId",
        "browser_pid",
        "browserPid",
        "existing_profile_grant_id",
        "existingProfileGrantId",
        "independent_grant_id",
        "independentGrantId",
    }
)
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:$|[+].*$)")


def version_is_at_least(installed: str | None, minimum: str = CUA_MINIMUM_VALIDATED_VERSION) -> bool:
    """Compare stable semantic versions without accepting prerelease labels."""

    if not installed:
        return False
    installed_match = _VERSION_RE.match(installed.strip().lstrip("v"))
    minimum_match = _VERSION_RE.match(minimum.strip().lstrip("v"))
    if not installed_match or not minimum_match:
        return False
    installed_tuple = tuple(int(value) for value in installed_match.groups())
    minimum_tuple = tuple(int(value) for value in minimum_match.groups())
    return installed_tuple >= minimum_tuple


@dataclass(frozen=True, slots=True)
class CuaBinding:
    """Host-owned CUA identity binding, never supplied by an MCP operation."""

    session_id: str
    process_id: int
    window_id: str
    target_id: str
    tab_id: str
    authorized_url: str
    profile_kind: str = "wbcp-isolated"
    existing_profile_grant_id: str | None = None
    independent_grant_id: str | None = None

    def __post_init__(self) -> None:
        if not self.session_id or self.process_id <= 0:
            raise ValueError("CUA binding requires a non-empty session and positive PID")
        if not all((self.window_id, self.target_id, self.tab_id, self.authorized_url)):
            raise ValueError("CUA binding requires window, target, tab, and authorized URL")
        if self.profile_kind not in {"wbcp-isolated", "existing-personal"}:
            raise ValueError("CUA profile_kind is invalid")

    def validate_operation(
        self,
        *,
        operation: str,
        target_url: str,
        arguments: Mapping[str, Any],
    ) -> None:
        canonical_operation = operation.strip().upper()
        if canonical_operation not in CUA_TYPED_OPERATION_ALLOWLIST:
            raise ControlPlaneError(
                FailureCode.BLOCKED_CUA_OPERATION_NOT_ALLOWLISTED,
                "CUA operation is not in the typed-tool allowlist",
                {"operation": canonical_operation},
            )
        attempted_override = sorted(set(arguments) & _BINDING_ARGUMENT_NAMES)
        if attempted_override:
            raise ControlPlaneError(
                FailureCode.BLOCKED_CUA_BINDING_ARGUMENT_OVERRIDE,
                "CUA operation arguments cannot override the host-owned binding",
                {"arguments": attempted_override},
            )
        if target_url != self.authorized_url:
            raise ControlPlaneError(
                FailureCode.BLOCKED_CUA_SESSION_BINDING_MISMATCH,
                "CUA target URL differs from the exact bound authorized URL",
                {"authorized_url": self.authorized_url, "target_url": target_url},
            )
        if self.profile_kind == "existing-personal" and not (
            self.existing_profile_grant_id and self.independent_grant_id
        ):
            raise ControlPlaneError(
                FailureCode.BLOCKED_CUA_EXISTING_PROFILE_DUAL_APPROVAL_REQUIRED,
                "Existing-profile attachment requires two host-issued independent grants",
            )
