from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass
from pathlib import Path

from .models import EngineKind


class RuntimeConfigurationError(ValueError):
    """Raised when a live control-plane process is not safely configured."""


def _decode_key(name: str, value: str | None) -> bytes:
    if not value:
        raise RuntimeConfigurationError(f"{name} is required")
    try:
        if value.startswith("base64:"):
            decoded = base64.b64decode(value[7:], validate=True)
        elif value.startswith("hex:"):
            decoded = bytes.fromhex(value[4:])
        else:
            raise RuntimeConfigurationError(
                f"{name} must use an explicit base64: or hex: prefix"
            )
    except (ValueError, binascii.Error) as exc:
        raise RuntimeConfigurationError(f"{name} is not a valid encoded key") from exc
    if len(decoded) < 32:
        raise RuntimeConfigurationError(f"{name} must decode to at least 32 bytes")
    return decoded


def _csv(value: str | None) -> frozenset[str]:
    return frozenset(item.strip() for item in (value or "").split(",") if item.strip())


def _bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    data_dir: Path
    allowed_hosts: frozenset[str]
    host_subject: str
    permit_signing_key: bytes
    approval_signing_key: bytes
    evidence_hmac_key: bytes
    http_bearer_token: str | None = None
    http_allowed_origins: frozenset[str] = frozenset()
    http_allowed_hosts: frozenset[str] = frozenset({"127.0.0.1", "localhost"})
    http_require_origin: bool = False
    http_max_request_bytes: int = 1_048_576
    http_max_batch_items: int = 32
    http_principal_id: str = "chatgpt-mcp-client"
    http_allowed_tools: frozenset[str] = frozenset()
    http_requests_per_minute: int = 120
    http_max_concurrent_requests: int = 8
    headless: bool = True
    browser_executable_path: str | None = None
    storage_state_path: str | None = None
    existing_profile_grant_id: str | None = None
    existing_profile_independent_grant_id: str | None = None
    allow_css_locators: bool = False
    use_mock_browser: bool = False
    engine_preference: EngineKind = EngineKind.AUTO
    jev_enabled: bool = False
    jev_public_hosts: frozenset[str] = frozenset()
    jev_external_model_egress_enabled: bool = False
    jev_runtime_authorization_id: str | None = None
    cua_enabled: bool = False
    cua_driver_version: str | None = None
    cua_minimum_validated_version: str = "0.28.2"
    r4_mode: str = "block"
    maximum_action_cost: float = 100.0
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not self.allowed_hosts:
            raise RuntimeConfigurationError("At least one exact WBCP_ALLOWED_HOSTS entry is required")
        if any("*" in host for host in self.allowed_hosts):
            raise RuntimeConfigurationError("Production runtime settings do not permit wildcard hosts")
        if not self.host_subject.strip():
            raise RuntimeConfigurationError("WBCP_HOST_SUBJECT is required")
        if self.http_bearer_token is not None and len(self.http_bearer_token) < 32:
            raise RuntimeConfigurationError("WBCP_HTTP_BEARER_TOKEN must be at least 32 characters")
        if self.http_max_request_bytes < 1_024 or self.http_max_request_bytes > 16_777_216:
            raise RuntimeConfigurationError("HTTP request cap must be between 1 KiB and 16 MiB")
        if self.http_max_batch_items < 1 or self.http_max_batch_items > 256:
            raise RuntimeConfigurationError("HTTP batch-item limit is outside safe range")
        if not self.http_principal_id.strip():
            raise RuntimeConfigurationError("HTTP principal ID must be non-empty")
        if self.http_requests_per_minute < 1 or self.http_requests_per_minute > 100_000:
            raise RuntimeConfigurationError("HTTP requests-per-minute limit is outside safe range")
        if self.http_max_concurrent_requests < 1 or self.http_max_concurrent_requests > 1_000:
            raise RuntimeConfigurationError("HTTP concurrent-request limit is outside safe range")
        if self.r4_mode not in {"block", "dual_control"}:
            raise RuntimeConfigurationError("WBCP_R4_MODE must be block or dual_control")
        if not isinstance(self.engine_preference, EngineKind):
            raise RuntimeConfigurationError("WBCP_ENGINE_PREFERENCE must be AUTO, PLAYWRIGHT, JEV, or CUA")
        if self.storage_state_path and not (
            self.existing_profile_grant_id and self.existing_profile_independent_grant_id
        ):
            raise RuntimeConfigurationError(
                "Existing browser state requires separate host-issued profile and independent grants"
            )
        if self.jev_external_model_egress_enabled and not self.jev_runtime_authorization_id:
            raise RuntimeConfigurationError(
                "Jev external model egress requires an independent runtime authorization ID"
            )
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, *, require_http_token: bool = False) -> "RuntimeSettings":
        data_dir_raw = os.environ.get("WBCP_DATA_DIR")
        if not data_dir_raw:
            raise RuntimeConfigurationError("WBCP_DATA_DIR is required")
        allowed_hosts = _csv(os.environ.get("WBCP_ALLOWED_HOSTS"))
        token = os.environ.get("WBCP_HTTP_BEARER_TOKEN")
        if require_http_token and not token:
            raise RuntimeConfigurationError("WBCP_HTTP_BEARER_TOKEN is required for HTTP")
        origins = _csv(os.environ.get("WBCP_HTTP_ALLOWED_ORIGINS"))
        http_hosts = _csv(os.environ.get("WBCP_HTTP_ALLOWED_HOSTS")) or frozenset(
            {"127.0.0.1", "localhost"}
        )
        return cls(
            data_dir=Path(data_dir_raw).expanduser().resolve(),
            allowed_hosts=allowed_hosts,
            host_subject=os.environ.get("WBCP_HOST_SUBJECT", "").strip(),
            permit_signing_key=_decode_key(
                "WBCP_PERMIT_SIGNING_KEY", os.environ.get("WBCP_PERMIT_SIGNING_KEY")
            ),
            approval_signing_key=_decode_key(
                "WBCP_APPROVAL_SIGNING_KEY", os.environ.get("WBCP_APPROVAL_SIGNING_KEY")
            ),
            evidence_hmac_key=_decode_key(
                "WBCP_EVIDENCE_HMAC_KEY", os.environ.get("WBCP_EVIDENCE_HMAC_KEY")
            ),
            http_bearer_token=token,
            http_allowed_origins=origins,
            http_allowed_hosts=http_hosts,
            http_require_origin=_bool(os.environ.get("WBCP_HTTP_REQUIRE_ORIGIN")),
            http_max_request_bytes=int(
                os.environ.get("WBCP_HTTP_MAX_REQUEST_BYTES", "1048576")
            ),
            http_max_batch_items=int(
                os.environ.get("WBCP_HTTP_MAX_BATCH_ITEMS", "32")
            ),
            http_principal_id=os.environ.get(
                "WBCP_HTTP_PRINCIPAL_ID", "chatgpt-mcp-client"
            ),
            http_allowed_tools=_csv(os.environ.get("WBCP_HTTP_ALLOWED_TOOLS")),
            http_requests_per_minute=int(
                os.environ.get("WBCP_HTTP_REQUESTS_PER_MINUTE", "120")
            ),
            http_max_concurrent_requests=int(
                os.environ.get("WBCP_HTTP_MAX_CONCURRENT_REQUESTS", "8")
            ),
            headless=_bool(os.environ.get("WBCP_HEADLESS"), default=True),
            browser_executable_path=os.environ.get("WBCP_BROWSER_EXECUTABLE_PATH") or None,
            storage_state_path=os.environ.get("WBCP_STORAGE_STATE_PATH") or None,
            existing_profile_grant_id=os.environ.get("WBCP_EXISTING_PROFILE_GRANT_ID") or None,
            existing_profile_independent_grant_id=(
                os.environ.get("WBCP_EXISTING_PROFILE_INDEPENDENT_GRANT_ID") or None
            ),
            allow_css_locators=_bool(os.environ.get("WBCP_ALLOW_CSS_LOCATORS")),
            use_mock_browser=_bool(os.environ.get("WBCP_USE_MOCK_BROWSER")),
            engine_preference=EngineKind(
                os.environ.get("WBCP_ENGINE_PREFERENCE", EngineKind.AUTO.value).strip().upper()
            ),
            jev_enabled=_bool(os.environ.get("WBCP_JEV_ENABLED")),
            jev_public_hosts=_csv(os.environ.get("WBCP_JEV_PUBLIC_HOSTS")),
            jev_external_model_egress_enabled=_bool(
                os.environ.get("WBCP_JEV_EXTERNAL_MODEL_EGRESS_ENABLED")
            ),
            jev_runtime_authorization_id=(
                os.environ.get("WBCP_JEV_RUNTIME_AUTHORIZATION_ID") or None
            ),
            cua_enabled=_bool(os.environ.get("WBCP_CUA_ENABLED")),
            cua_driver_version=os.environ.get("WBCP_CUA_DRIVER_VERSION") or None,
            cua_minimum_validated_version=os.environ.get(
                "WBCP_CUA_MINIMUM_VALIDATED_VERSION", "0.28.2"
            ),
            r4_mode=os.environ.get("WBCP_R4_MODE", "block"),
            maximum_action_cost=float(
                os.environ.get("WBCP_MAXIMUM_ACTION_COST", "100.0")
            ),
            currency=os.environ.get("WBCP_CURRENCY", "USD").upper(),
        )

    @classmethod
    def for_tests(cls, root: Path) -> "RuntimeSettings":
        return cls(
            data_dir=root,
            allowed_hosts=frozenset({"example.com", "api.example.com"}),
            host_subject="test-host-model-attested",
            permit_signing_key=b"P" * 32,
            approval_signing_key=b"A" * 32,
            evidence_hmac_key=b"E" * 32,
            http_bearer_token="T" * 48,
            http_allowed_origins=frozenset({"https://chatgpt.com"}),
            http_allowed_hosts=frozenset({"testserver", "127.0.0.1", "localhost"}),
            http_principal_id="test-mcp-client",
            use_mock_browser=True,
        )
