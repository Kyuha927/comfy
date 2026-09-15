from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
import re
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .note_ir import (
    DetectedNote,
    DetectedTrack,
    ProviderTier,
    TranscriptionResult,
    clamp,
    normalize_instrument,
)


_PROVIDER_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_ALLOWED_PLACEHOLDERS = {"input", "output_json", "output_dir", "instrument_hint", "provider_id"}


class NoteProviderError(RuntimeError):
    """A safe, user-actionable provider failure."""


class ProviderCapability(BaseModel):
    full_mix: bool = False
    isolated_stem: bool = True
    polyphonic: bool = True
    per_note_confidence: bool = False
    direct_audio_edit: bool = False


class NoteProviderInfo(BaseModel):
    provider_id: str
    label: str
    tier: ProviderTier
    mode: Literal["python-package", "command", "import", "manual", "test"]
    ready: bool
    capabilities: ProviderCapability = Field(default_factory=ProviderCapability)
    version: str | None = None
    license_reference: str | None = None
    reason: str | None = None


class CommandProviderConfig(BaseModel):
    provider_id: str
    label: str
    tier: ProviderTier = ProviderTier.FREE
    argv: list[str] = Field(min_length=1, max_length=64)
    timeout_seconds: int = Field(default=3 * 60 * 60, ge=1, le=24 * 60 * 60)
    capabilities: ProviderCapability = Field(default_factory=ProviderCapability)
    license_reference: str | None = Field(default=None, max_length=1000)

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _PROVIDER_ID.fullmatch(normalized):
            raise ValueError("invalid provider id")
        return normalized

    @model_validator(mode="after")
    def validate_argv(self) -> "CommandProviderConfig":
        executable = Path(self.argv[0]).expanduser()
        if not executable.is_absolute():
            raise ValueError("command provider requires an absolute executable path")
        for part in self.argv:
            if not part or "\x00" in part:
                raise ValueError("provider argv contains an invalid value")
            placeholders = set(re.findall(r"\{([A-Za-z0-9_]+)\}", part))
            unsupported = placeholders - _ALLOWED_PLACEHOLDERS
            if unsupported:
                raise ValueError(f"unsupported provider placeholders: {sorted(unsupported)}")
            stripped = re.sub(r"\{[A-Za-z0-9_]+\}", "", part)
            if "{" in stripped or "}" in stripped:
                raise ValueError("provider argv contains malformed placeholders")
        return self


class NoteProvider(ABC):
    @abstractmethod
    def info(self) -> NoteProviderInfo:
        raise NotImplementedError

    @abstractmethod
    def transcribe(
        self,
        *,
        source_path: Path,
        output_dir: Path,
        instrument_hint: str | None = None,
    ) -> TranscriptionResult:
        raise NotImplementedError


class BasicPitchProvider(NoteProvider):
    provider_id = "basic-pitch"

    @staticmethod
    def _version() -> str | None:
        try:
            return importlib.metadata.version("basic-pitch")
        except importlib.metadata.PackageNotFoundError:
            return None

    def info(self) -> NoteProviderInfo:
        ready = importlib.util.find_spec("basic_pitch") is not None
        return NoteProviderInfo(
            provider_id=self.provider_id,
            label="Spotify Basic Pitch",
            tier=ProviderTier.FREE,
            mode="python-package",
            ready=ready,
            capabilities=ProviderCapability(
                full_mix=False,
                isolated_stem=True,
                polyphonic=True,
                per_note_confidence=False,
                direct_audio_edit=False,
            ),
            version=self._version(),
            license_reference="Apache-2.0 package; model terms must be reviewed before distribution",
            reason=None if ready else "Python package 'basic-pitch' is not installed",
        )

    @staticmethod
    def _parse_event(event: Any, index: int) -> DetectedNote:
        if isinstance(event, dict):
            start = event.get("start_time_s", event.get("start_sec"))
            end = event.get("end_time_s", event.get("end_sec"))
            pitch = event.get("pitch_midi", event.get("pitch"))
            amplitude = event.get("amplitude", event.get("confidence", 0.5))
        elif isinstance(event, (list, tuple)) and len(event) >= 4:
            start, end, pitch, amplitude = event[:4]
        else:
            raise NoteProviderError(f"Basic Pitch returned an unsupported note event at index {index}")
        try:
            amplitude_float = float(amplitude)
            normalized = clamp(amplitude_float, 0.0, 1.0)
            velocity = int(clamp(round(normalized * 127), 1, 127))
            return DetectedNote(
                provider_note_id=f"basic-pitch-{index}",
                pitch_midi=int(round(float(pitch))),
                start_sec=float(start),
                end_sec=float(end),
                velocity=velocity,
                confidence=normalized,
            )
        except (TypeError, ValueError) as exc:
            raise NoteProviderError(f"Basic Pitch returned an invalid note event at index {index}") from exc

    def transcribe(
        self,
        *,
        source_path: Path,
        output_dir: Path,
        instrument_hint: str | None = None,
    ) -> TranscriptionResult:
        if not self.info().ready:
            raise NoteProviderError("Basic Pitch is not installed")
        try:
            from basic_pitch.inference import predict
        except Exception as exc:  # pragma: no cover - depends on optional runtime
            raise NoteProviderError(f"Basic Pitch import failed: {type(exc).__name__}: {exc}") from exc
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            _model_output, midi_data, note_events = predict(str(source_path))
        except Exception as exc:  # pragma: no cover - depends on optional runtime
            raise NoteProviderError(f"Basic Pitch inference failed: {type(exc).__name__}: {exc}") from exc
        notes = [self._parse_event(event, index) for index, event in enumerate(note_events)]
        midi_path = output_dir / "basic-pitch.mid"
        try:
            midi_data.write(str(midi_path))
        except Exception:
            # The normalized note data is the contract. Native MIDI is a useful extra,
            # but a version-specific pretty_midi writer failure must not corrupt it.
            midi_path = None
        instrument = normalize_instrument(instrument_hint or "unknown")
        result = TranscriptionResult(
            provider_id=self.provider_id,
            provider_version=self._version(),
            tier=ProviderTier.FREE,
            mode="python-package",
            tracks=[
                DetectedTrack(
                    track_id=None,
                    name=instrument.replace("-", " ").title(),
                    instrument=instrument,
                    polyphonic=True,
                    notes=notes,
                )
            ],
            warnings=[
                "Basic Pitch amplitude is stored as a heuristic confidence, not a calibrated probability.",
                "Basic Pitch is strongest on one isolated instrument at a time; full-mix results require review.",
            ],
            metadata={"native_midi": midi_path.name if midi_path else None},
        )
        (output_dir / "basic-pitch.normalized.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        return result


class CommandNoteProvider(NoteProvider):
    def __init__(self, config: CommandProviderConfig):
        self.config = config

    def info(self) -> NoteProviderInfo:
        executable = Path(self.config.argv[0]).expanduser()
        ready = executable.is_file() and os.access(executable, os.X_OK)
        return NoteProviderInfo(
            provider_id=self.config.provider_id,
            label=self.config.label,
            tier=self.config.tier,
            mode="command",
            ready=ready,
            capabilities=self.config.capabilities,
            license_reference=self.config.license_reference,
            reason=None if ready else f"executable is unavailable: {executable}",
        )

    def _argv(
        self,
        *,
        source_path: Path,
        output_dir: Path,
        output_json: Path,
        instrument_hint: str | None,
    ) -> list[str]:
        values = {
            "input": str(source_path.resolve()),
            "output_dir": str(output_dir.resolve()),
            "output_json": str(output_json.resolve()),
            "instrument_hint": instrument_hint or "unknown",
            "provider_id": self.config.provider_id,
        }
        return [part.format_map(values) for part in self.config.argv]

    def transcribe(
        self,
        *,
        source_path: Path,
        output_dir: Path,
        instrument_hint: str | None = None,
    ) -> TranscriptionResult:
        info = self.info()
        if not info.ready:
            raise NoteProviderError(info.reason or "command provider is not ready")
        source = source_path.resolve()
        if not source.is_file():
            raise NoteProviderError("source audio is missing")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_json = output_dir / "normalized-notes.json"
        argv = self._argv(
            source_path=source,
            output_dir=output_dir,
            output_json=output_json,
            instrument_hint=instrument_hint,
        )
        try:
            completed = subprocess.run(
                argv,
                cwd=output_dir,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.config.timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise NoteProviderError(
                f"provider {self.config.provider_id} timed out after {self.config.timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise NoteProviderError(
                f"provider {self.config.provider_id} could not start: {exc}"
            ) from exc
        (output_dir / "provider.stdout.log").write_text(completed.stdout[-200_000:], encoding="utf-8")
        (output_dir / "provider.stderr.log").write_text(completed.stderr[-200_000:], encoding="utf-8")
        if completed.returncode != 0:
            tail = completed.stderr.strip().splitlines()[-1:] or completed.stdout.strip().splitlines()[-1:]
            detail = tail[0][:500] if tail else "no diagnostic output"
            raise NoteProviderError(
                f"provider {self.config.provider_id} exited {completed.returncode}: {detail}"
            )
        if not output_json.is_file():
            raise NoteProviderError(
                f"provider {self.config.provider_id} did not create {output_json.name}"
            )
        try:
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            result = TranscriptionResult.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise NoteProviderError(
                f"provider {self.config.provider_id} returned invalid normalized JSON"
            ) from exc
        if result.provider_id != self.config.provider_id:
            raise NoteProviderError(
                f"provider id mismatch: expected {self.config.provider_id}, got {result.provider_id}"
            )
        if result.tier != self.config.tier:
            result = result.model_copy(update={"tier": self.config.tier})
        return result


class ManualProvider(NoteProvider):
    def __init__(self, info: NoteProviderInfo):
        self._info = info

    def info(self) -> NoteProviderInfo:
        return self._info

    def transcribe(
        self,
        *,
        source_path: Path,
        output_dir: Path,
        instrument_hint: str | None = None,
    ) -> TranscriptionResult:
        raise NoteProviderError(
            f"{self._info.label} is an adapter slot and has not been configured for automatic execution"
        )


class NoteProviderRegistry:
    def __init__(self, providers: list[NoteProvider]):
        self._providers: dict[str, NoteProvider] = {}
        for provider in providers:
            provider_id = provider.info().provider_id
            if provider_id in self._providers:
                raise NoteProviderError(f"duplicate note provider id: {provider_id}")
            self._providers[provider_id] = provider

    @classmethod
    def from_env(cls, *, default_timeout_seconds: int) -> "NoteProviderRegistry":
        providers: list[NoteProvider] = [BasicPitchProvider()]
        providers.append(
            ManualProvider(
                NoteProviderInfo(
                    provider_id="normalized-json",
                    label="Normalized Note JSON import",
                    tier=ProviderTier.FREE,
                    mode="import",
                    ready=True,
                    capabilities=ProviderCapability(
                        full_mix=True,
                        isolated_stem=True,
                        polyphonic=True,
                        per_note_confidence=True,
                    ),
                    reason="Use the import endpoint; no audio inference is performed by this slot.",
                )
            )
        )
        raw = os.getenv("YUE2_MUSIC_OS_NOTE_PROVIDERS_JSON", "").strip()
        if raw:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise NoteProviderError("YUE2_MUSIC_OS_NOTE_PROVIDERS_JSON must be valid JSON") from exc
            if not isinstance(payload, dict):
                raise NoteProviderError("YUE2_MUSIC_OS_NOTE_PROVIDERS_JSON must be a JSON object")
            for provider_id, definition in payload.items():
                if not isinstance(provider_id, str) or not isinstance(definition, dict):
                    raise NoteProviderError("note provider definitions must be objects")
                if definition.get("enabled", True) is False:
                    continue
                if definition.get("mode", "command") != "command":
                    raise NoteProviderError(
                        f"configured note provider {provider_id!r} supports mode='command' only"
                    )
                config_payload = dict(definition)
                config_payload["provider_id"] = provider_id
                config_payload.setdefault("label", provider_id)
                config_payload.setdefault("timeout_seconds", default_timeout_seconds)
                try:
                    config = CommandProviderConfig.model_validate(config_payload)
                except ValueError as exc:
                    raise NoteProviderError(f"invalid note provider {provider_id!r}: {exc}") from exc
                providers.append(CommandNoteProvider(config))

        configured_ids = {provider.info().provider_id for provider in providers}
        paid_capabilities = ProviderCapability(
            full_mix=True,
            isolated_stem=True,
            polyphonic=True,
            per_note_confidence=False,
            direct_audio_edit=False,
        )
        for provider_id, label in (
            ("klangio-paid-slot", "Klangio paid adapter slot"),
            ("ripx-paid-slot", "RipX paid adapter slot"),
            ("melodyne-paid-slot", "Melodyne paid adapter slot"),
        ):
            if provider_id in configured_ids:
                continue
            providers.append(
                ManualProvider(
                    NoteProviderInfo(
                        provider_id=provider_id,
                        label=label,
                        tier=ProviderTier.PAID,
                        mode="manual",
                        ready=False,
                        capabilities=paid_capabilities,
                        reason="Not configured. Replace this slot with a licensed command adapter later.",
                    )
                )
            )
        return cls(providers)

    def infos(self) -> list[NoteProviderInfo]:
        return sorted((provider.info() for provider in self._providers.values()), key=lambda info: (info.tier, info.provider_id))

    def get(self, provider_id: str) -> NoteProvider:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise NoteProviderError(f"unknown note provider: {provider_id}") from exc

    def ready_free_provider_ids(self) -> list[str]:
        return [
            info.provider_id
            for info in self.infos()
            if info.tier == ProviderTier.FREE and info.ready and info.mode not in {"import", "manual"}
        ]
