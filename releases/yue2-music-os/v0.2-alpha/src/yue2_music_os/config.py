from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


EngineMode = Literal["mock", "local"]
ModelUseScope = Literal["noncommercial", "commercial-licensed"]
RenderProviderMode = Literal["manual", "command", "mock"]
CommercialStatus = Literal["unknown", "operator-verified", "noncommercial"]
_PROVIDER_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_ALLOWED_COMMAND_PLACEHOLDERS = {"request_json", "output_dir", "provider_id"}


class ConfigurationError(RuntimeError):
    """Raised when the runtime configuration is unsafe or incomplete."""


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc


@dataclass(frozen=True, slots=True)
class RenderProviderConfig:
    provider_id: str
    label: str
    mode: RenderProviderMode
    argv: tuple[str, ...] = ()
    timeout_seconds: int | None = None
    terms_reference: str | None = None
    commercial_status: CommercialStatus = "unknown"

    def validate(self) -> None:
        if not _PROVIDER_ID.fullmatch(self.provider_id):
            raise ConfigurationError(f"invalid render provider id: {self.provider_id!r}")
        if not self.label.strip() or len(self.label) > 120:
            raise ConfigurationError(
                f"render provider {self.provider_id!r} has an invalid label"
            )
        if self.mode not in {"manual", "command", "mock"}:
            raise ConfigurationError(
                f"render provider {self.provider_id!r} has an invalid mode"
            )
        if self.commercial_status not in {
            "unknown",
            "operator-verified",
            "noncommercial",
        }:
            raise ConfigurationError(
                f"render provider {self.provider_id!r} has an invalid commercial status"
            )
        if self.timeout_seconds is not None and self.timeout_seconds < 1:
            raise ConfigurationError(
                f"render provider {self.provider_id!r} timeout must be positive"
            )
        if self.mode == "command":
            if not self.argv:
                raise ConfigurationError(
                    f"command render provider {self.provider_id!r} requires argv"
                )
            executable = Path(self.argv[0]).expanduser()
            if not executable.is_absolute():
                raise ConfigurationError(
                    f"command render provider {self.provider_id!r} requires an absolute executable path"
                )
            for part in self.argv:
                if not isinstance(part, str) or not part or "\x00" in part:
                    raise ConfigurationError(
                        f"command render provider {self.provider_id!r} has invalid argv"
                    )
                names = set(re.findall(r"\{([A-Za-z0-9_]+)\}", part))
                unsupported = names - _ALLOWED_COMMAND_PLACEHOLDERS
                if unsupported:
                    raise ConfigurationError(
                        f"render provider {self.provider_id!r} uses unsupported placeholders: {sorted(unsupported)}"
                    )
                stripped = re.sub(r"\{[A-Za-z0-9_]+\}", "", part)
                if "{" in stripped or "}" in stripped:
                    raise ConfigurationError(
                        f"render provider {self.provider_id!r} has malformed placeholders"
                    )
        elif self.argv:
            raise ConfigurationError(
                f"render provider {self.provider_id!r} mode {self.mode!r} cannot define argv"
            )

    def public_info(self, *, executable_ready: bool | None = None) -> dict[str, object]:
        ready = True if executable_ready is None else executable_ready
        return {
            "id": self.provider_id,
            "label": self.label,
            "mode": self.mode,
            "ready": ready,
            "live_execution": self.mode in {"command", "mock"},
            "commercial_status": self.commercial_status,
            "terms_reference_recorded": bool(self.terms_reference),
        }


def default_render_providers() -> tuple[RenderProviderConfig, ...]:
    """Built-ins are export contracts, not claims of authenticated API access."""
    return (
        RenderProviderConfig(
            provider_id="flow-lyria-manual",
            label="Flow / Lyria manual export",
            mode="manual",
            commercial_status="unknown",
        ),
        RenderProviderConfig(
            provider_id="suno-manual",
            label="Suno manual export",
            mode="manual",
            commercial_status="unknown",
        ),
        RenderProviderConfig(
            provider_id="eleven-music-manual",
            label="Eleven Music manual export",
            mode="manual",
            commercial_status="unknown",
        ),
        RenderProviderConfig(
            provider_id="generic-manual",
            label="Generic commercial renderer export",
            mode="manual",
            commercial_status="unknown",
        ),
        RenderProviderConfig(
            provider_id="mock-renderer",
            label="Mock renderer (test tone only)",
            mode="mock",
            commercial_status="noncommercial",
        ),
    )


def _parse_render_providers(raw: str, default_timeout: int) -> tuple[RenderProviderConfig, ...]:
    providers = list(default_render_providers())
    if not raw.strip():
        return tuple(providers)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            "YUE2_MUSIC_OS_RENDER_PROVIDERS_JSON must be valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise ConfigurationError(
            "YUE2_MUSIC_OS_RENDER_PROVIDERS_JSON must be a JSON object"
        )
    for provider_id, value in payload.items():
        if not isinstance(provider_id, str) or not isinstance(value, dict):
            raise ConfigurationError("render provider definitions must be objects")
        if value.get("enabled", True) is False:
            continue
        mode = value.get("mode", "command")
        argv_value = value.get("argv", [])
        if not isinstance(argv_value, list) or not all(
            isinstance(part, str) for part in argv_value
        ):
            raise ConfigurationError(
                f"render provider {provider_id!r} argv must be a string list"
            )
        timeout = value.get("timeout_seconds", default_timeout)
        if not isinstance(timeout, int):
            raise ConfigurationError(
                f"render provider {provider_id!r} timeout_seconds must be an integer"
            )
        config = RenderProviderConfig(
            provider_id=provider_id,
            label=str(value.get("label", provider_id)).strip(),
            mode=mode,  # type: ignore[arg-type]
            argv=tuple(argv_value),
            timeout_seconds=timeout,
            terms_reference=(
                str(value["terms_reference"]).strip()
                if value.get("terms_reference")
                else None
            ),
            commercial_status=value.get("commercial_status", "unknown"),  # type: ignore[arg-type]
        )
        providers.append(config)
    ids = [provider.provider_id for provider in providers]
    if len(ids) != len(set(ids)):
        raise ConfigurationError("render provider ids must be unique")
    return tuple(providers)


@dataclass(frozen=True, slots=True)
class Settings:
    engine: EngineMode
    data_dir: Path
    api_token: str | None
    allowed_hosts: tuple[str, ...]
    max_upload_bytes: int
    command_timeout_seconds: int
    model_use_scope: ModelUseScope
    commercial_license_reference: str | None
    yue2_python: Path
    yue2_repo: Path
    yue2_model: str
    yue2_revision: str | None
    yue2_vae: str
    yue2_vae_revision: str | None
    sheetsage2_python: Path
    sheetsage2_dir: Path
    sheetsage2_model: str
    sheetsage2_revision: str | None
    sheetsage2_base_model: Path | None
    gpu_workers: int
    render_providers: tuple[RenderProviderConfig, ...] = field(
        default_factory=default_render_providers
    )

    @classmethod
    def from_env(cls) -> "Settings":
        engine = os.getenv("YUE2_MUSIC_OS_ENGINE", "mock").strip().lower()
        if engine not in {"mock", "local"}:
            raise ConfigurationError("YUE2_MUSIC_OS_ENGINE must be mock or local")
        scope = os.getenv("YUE2_MUSIC_OS_MODEL_USE_SCOPE", "noncommercial").strip().lower()
        if scope not in {"noncommercial", "commercial-licensed"}:
            raise ConfigurationError(
                "YUE2_MUSIC_OS_MODEL_USE_SCOPE must be noncommercial or commercial-licensed"
            )
        token = os.getenv("YUE2_MUSIC_OS_API_TOKEN", "").strip() or None
        allowed_hosts = tuple(
            host.strip()
            for host in os.getenv(
                "YUE2_MUSIC_OS_ALLOWED_HOSTS",
                "localhost,127.0.0.1,[::1],testserver",
            ).split(",")
            if host.strip()
        )
        license_reference = (
            os.getenv("YUE2_MUSIC_OS_COMMERCIAL_LICENSE_REFERENCE", "").strip() or None
        )
        command_timeout = _env_int(
            "YUE2_MUSIC_OS_COMMAND_TIMEOUT_SECONDS", 3 * 60 * 60
        )
        settings = cls(
            engine=engine,  # type: ignore[arg-type]
            data_dir=Path(os.getenv("YUE2_MUSIC_OS_DATA", "./var")).expanduser().resolve(),
            api_token=token,
            allowed_hosts=allowed_hosts,
            max_upload_bytes=_env_int("YUE2_MUSIC_OS_MAX_UPLOAD_BYTES", 500 * 1024 * 1024),
            command_timeout_seconds=command_timeout,
            model_use_scope=scope,  # type: ignore[arg-type]
            commercial_license_reference=license_reference,
            yue2_python=Path(
                os.getenv(
                    "YUE2_MUSIC_OS_YUE2_PYTHON", "./runtime/yue2/.venv/bin/python"
                )
            ).expanduser().resolve(),
            yue2_repo=Path(
                os.getenv("YUE2_MUSIC_OS_YUE2_REPO", "./runtime/yue2/YuE")
            ).expanduser().resolve(),
            yue2_model=os.getenv("YUE2_MUSIC_OS_YUE2_MODEL", "m-a-p/YuE2-3B"),
            yue2_revision=(os.getenv("YUE2_MUSIC_OS_YUE2_REVISION", "").strip() or None),
            yue2_vae=os.getenv("YUE2_MUSIC_OS_YUE2_VAE", "m-a-p/YuE2-Vae"),
            yue2_vae_revision=(
                os.getenv("YUE2_MUSIC_OS_YUE2_VAE_REVISION", "").strip() or None
            ),
            sheetsage2_python=Path(
                os.getenv(
                    "YUE2_MUSIC_OS_SHEETSAGE2_PYTHON",
                    "./runtime/sheetsage2/.venv/bin/python",
                )
            ).expanduser().resolve(),
            sheetsage2_dir=Path(
                os.getenv("YUE2_MUSIC_OS_SHEETSAGE2_DIR", "./runtime/sheetsage2/model")
            ).expanduser().resolve(),
            sheetsage2_model=os.getenv("YUE2_MUSIC_OS_SHEETSAGE2_MODEL", "m-a-p/SheetSage2"),
            sheetsage2_revision=(
                os.getenv("YUE2_MUSIC_OS_SHEETSAGE2_REVISION", "").strip() or None
            ),
            sheetsage2_base_model=(
                Path(os.environ["YUE2_MUSIC_OS_SHEETSAGE2_BASE_MODEL"])
                .expanduser()
                .resolve()
                if os.getenv("YUE2_MUSIC_OS_SHEETSAGE2_BASE_MODEL", "").strip()
                else None
            ),
            gpu_workers=_env_int("YUE2_MUSIC_OS_GPU_WORKERS", 1),
            render_providers=_parse_render_providers(
                os.getenv("YUE2_MUSIC_OS_RENDER_PROVIDERS_JSON", ""),
                command_timeout,
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.allowed_hosts:
            raise ConfigurationError("YUE2_MUSIC_OS_ALLOWED_HOSTS cannot be empty")
        for host in self.allowed_hosts:
            if "://" in host or "/" in host or any(char.isspace() for char in host):
                raise ConfigurationError(f"invalid allowed host pattern: {host!r}")
        if "*" in self.allowed_hosts and not self.api_token:
            raise ConfigurationError("wildcard allowed hosts require YUE2_MUSIC_OS_API_TOKEN")
        if self.max_upload_bytes < 1:
            raise ConfigurationError("max_upload_bytes must be positive")
        if self.command_timeout_seconds < 1:
            raise ConfigurationError("command_timeout_seconds must be positive")
        if self.gpu_workers != 1:
            raise ConfigurationError(
                "v0.2 alpha intentionally permits exactly one GPU worker; measured concurrency is required before raising it"
            )
        if (
            self.model_use_scope == "commercial-licensed"
            and not self.commercial_license_reference
        ):
            raise ConfigurationError(
                "commercial-licensed mode requires YUE2_MUSIC_OS_COMMERCIAL_LICENSE_REFERENCE"
            )
        if not self.render_providers:
            raise ConfigurationError("at least one render provider is required")
        seen: set[str] = set()
        for provider in self.render_providers:
            provider.validate()
            if provider.provider_id in seen:
                raise ConfigurationError("render provider ids must be unique")
            seen.add(provider.provider_id)

    def assert_real_engine_allowed(self) -> None:
        if self.engine == "mock":
            return
        if self.model_use_scope == "commercial-licensed":
            if not self.commercial_license_reference:
                raise ConfigurationError("missing commercial license reference")
            return
        if self.model_use_scope != "noncommercial":
            raise ConfigurationError("unrecognized model-use scope")

    def public_policy(self) -> dict[str, object]:
        return {
            "engine": self.engine,
            "model_use_scope": self.model_use_scope,
            "commercial_license_reference_recorded": bool(
                self.commercial_license_reference
            ),
            "allowed_hosts": list(self.allowed_hosts),
            "sequential_gpu_jobs": self.gpu_workers == 1,
            "max_upload_bytes": self.max_upload_bytes,
            "render_provider_ids": [
                provider.provider_id for provider in self.render_providers
            ],
            "render_provider_command_count": sum(
                provider.mode == "command" for provider in self.render_providers
            ),
        }
