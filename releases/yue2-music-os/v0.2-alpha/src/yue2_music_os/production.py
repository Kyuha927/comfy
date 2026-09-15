from __future__ import annotations

import html
import json
import math
import os
import re
import shutil
import struct
import wave
from pathlib import Path
from typing import Any

from .abc_tools import AbcError, parse
from .config import RenderProviderConfig, Settings
from .engines import EngineError, run_command
from .models import JobRecord, ProductionRenderRequest


_AUDIO_SUFFIXES = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
_CANDIDATE_NAME = re.compile(r"candidate-(\d{2})")


class ProductionError(RuntimeError):
    """Raised when ranking or final-render packaging cannot be proved safe."""


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _safe_child(root: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise ProductionError("artifact path must be relative")
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ProductionError("artifact path escaped its package root")
    return candidate


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ProductionError("candidate artifact escaped the generation job") from exc


def _wav_metadata(path: Path) -> dict[str, object]:
    try:
        with wave.open(str(path), "rb") as source:
            frames = source.getnframes()
            sample_rate = source.getframerate()
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
    except (wave.Error, OSError) as exc:
        raise ProductionError(f"invalid WAV candidate: {path.name}") from exc
    if frames < 1 or sample_rate < 1 or channels < 1 or sample_width < 1:
        raise ProductionError(f"empty or invalid WAV candidate: {path.name}")
    return {
        "format": "wav",
        "frames": frames,
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "duration_seconds": round(frames / sample_rate, 6),
    }


def _candidate_number(path: Path) -> int:
    match = _CANDIDATE_NAME.fullmatch(path.name)
    if not match:
        raise ProductionError(f"invalid candidate directory name: {path.name}")
    return int(match.group(1))


def _find_audio(candidate_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in candidate_dir.iterdir()
        if path.is_file() and path.suffix.lower() in _AUDIO_SUFFIXES
    )


def rank_generation_candidates(
    source_job_dir: Path,
    source_request: dict[str, Any],
    source_result: dict[str, Any] | None,
) -> dict[str, object]:
    """Rank only technical readiness. This never claims musical-quality judgment."""
    output_root = source_job_dir / "output"
    if not output_root.is_dir():
        raise ProductionError("generation job has no output directory")
    candidate_dirs = sorted(
        path
        for path in output_root.iterdir()
        if path.is_dir() and _CANDIDATE_NAME.fullmatch(path.name)
    )
    if not candidate_dirs:
        raise ProductionError("generation job contains no candidate directories")

    cot = str(source_request.get("cot", "full"))
    ranking: list[dict[str, object]] = []
    for candidate_dir in candidate_dirs:
        number = _candidate_number(candidate_dir)
        points = 0
        checks: dict[str, object] = {}
        warnings: list[str] = []
        eligible = True

        receipt = _read_json(candidate_dir / "result.json")
        if receipt is None:
            checks["result_receipt"] = "FAIL"
            warnings.append("Missing or invalid result.json receipt.")
            eligible = False
        else:
            points += 10
            checks["result_receipt"] = "PASS"

        status = receipt.get("status") if receipt else None
        if status in {"complete", "mock-complete"}:
            points += 10
            checks["candidate_status"] = "PASS"
        elif status == "needs_review":
            points += 4
            checks["candidate_status"] = "REVIEW"
            warnings.append("Upstream generator marked this candidate needs_review.")
        else:
            checks["candidate_status"] = "FAIL"
            warnings.append(f"Unsupported or missing candidate status: {status!r}.")
            eligible = False

        request_receipt = _read_json(candidate_dir / "request.json")
        if request_receipt is not None:
            points += 5
            checks["request_receipt"] = "PASS"
        else:
            checks["request_receipt"] = "FAIL"
            warnings.append("Missing or invalid request.json receipt.")

        failure = candidate_dir / "failure.json"
        if failure.exists():
            checks["failure_receipt_absent"] = "FAIL"
            warnings.append("failure.json is present.")
            eligible = False
        else:
            points += 10
            checks["failure_receipt_absent"] = "PASS"

        audio_files = _find_audio(candidate_dir)
        audio_path: Path | None = None
        audio_metadata: dict[str, object] | None = None
        if len(audio_files) != 1:
            checks["audio_file"] = "FAIL"
            warnings.append(
                f"Expected exactly one candidate audio file; found {len(audio_files)}."
            )
            eligible = False
        else:
            audio_path = audio_files[0]
            if audio_path.stat().st_size <= 0:
                checks["audio_file"] = "FAIL"
                warnings.append("Candidate audio is empty.")
                eligible = False
            else:
                points += 25
                checks["audio_file"] = "PASS"
                if audio_path.suffix.lower() == ".wav":
                    try:
                        audio_metadata = _wav_metadata(audio_path)
                    except ProductionError as exc:
                        checks["audio_metadata"] = "FAIL"
                        warnings.append(str(exc))
                        eligible = False
                    else:
                        points += 10
                        checks["audio_metadata"] = "PASS"
                else:
                    points += 6
                    checks["audio_metadata"] = "PARTIAL"
                    audio_metadata = {
                        "format": audio_path.suffix.lower().lstrip("."),
                        "size_bytes": audio_path.stat().st_size,
                    }
                    warnings.append(
                        "Compressed audio was size-checked but not decoded by the controller."
                    )

        score_path = candidate_dir / "score.abc"
        score_required = cot != "off"
        score_valid = False
        if not score_required:
            points += 30
            checks["score"] = "NOT_APPLICABLE"
            score_valid = True
        elif not score_path.is_file():
            checks["score"] = "FAIL"
            warnings.append("Planned generation candidate is missing score.abc.")
            eligible = False
        else:
            points += 10
            try:
                parsed = parse(score_path.read_text(encoding="utf-8"))
            except (OSError, AbcError, ValueError) as exc:
                checks["score"] = "FAIL"
                warnings.append(f"score.abc failed symbolic parsing: {exc}")
                eligible = False
            else:
                score_valid = True
                points += 15
                checks["score"] = "PASS"
                abc_receipt = _read_json(candidate_dir / "abc_check.json")
                if abc_receipt is not None:
                    points += 5
                    checks["abc_check_receipt"] = "PASS"
                else:
                    checks["abc_check_receipt"] = "MISSING"
                    warnings.append("abc_check.json is missing; score was parsed again locally.")
                checks["score_voice_count"] = len(parsed.voices)

        if score_required and not score_valid:
            eligible = False

        score = max(0, min(100, points))
        ranking.append(
            {
                "candidate": number,
                "candidate_id": candidate_dir.name,
                "seed": receipt.get("seed") if receipt else None,
                "status": status,
                "eligible": eligible,
                "technical_score": score,
                "checks": checks,
                "warnings": warnings,
                "audio": _relative(audio_path, source_job_dir) if audio_path else None,
                "audio_metadata": audio_metadata,
                "score": (
                    _relative(score_path, source_job_dir)
                    if score_path.is_file()
                    else None
                ),
            }
        )

    ordered = sorted(
        ranking,
        key=lambda item: (
            not bool(item["eligible"]),
            -int(item["technical_score"]),
            int(item["candidate"]),
        ),
    )
    eligible = [item for item in ordered if bool(item["eligible"])]
    if not eligible:
        raise ProductionError("no generation candidate passed technical eligibility")
    recommended = int(eligible[0]["candidate"])
    return {
        "status": "complete",
        "scope": "technical-readiness-only",
        "quality_claim": False,
        "source_engine": (source_result or {}).get("engine"),
        "source_candidate_count": len(candidate_dirs),
        "recommended_candidate": recommended,
        "ranking": ordered,
        "limitations": [
            "The score measures receipts, file integrity, symbolic parseability, and review flags only.",
            "It does not judge composition, vocal naturalness, mix quality, emotion, prompt adherence, or commercial value.",
            "Final musical selection still requires human A/B listening or a separately validated listening model.",
        ],
    }


def write_ranking_report(job_dir: Path, ranking: dict[str, object]) -> None:
    _write_json(job_dir / "candidate-ranking.json", ranking)
    escaped = html.escape(
        json.dumps(ranking, ensure_ascii=False, indent=2, sort_keys=True)
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>YuE2 candidate technical ranking</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:1000px;margin:40px auto;padding:0 20px;background:#101112;color:#f4efe8}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#1a1c1e;padding:18px;border-radius:14px;border:1px solid #34373a}}strong{{color:#f0a078}}</style></head>
<body><h1>Candidate technical ranking</h1><p><strong>Not a musical-quality verdict.</strong> This report only checks technical readiness and provenance.</p><pre>{escaped}</pre></body></html>
"""
    (job_dir / "candidate-ranking.html").write_text(document, encoding="utf-8")


def _write_mock_wave(path: Path, *, seed: int, seconds: float = 3.0) -> None:
    sample_rate = 48_000
    frames = int(sample_rate * seconds)
    frequency = 246.94 + (seed % 7) * 17.0
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        for index in range(frames):
            envelope = min(1.0, index / (sample_rate * 0.04))
            envelope *= min(1.0, (frames - index) / (sample_rate * 0.08))
            sample = int(
                32767
                * 0.13
                * envelope
                * math.sin(2 * math.pi * frequency * index / sample_rate)
            )
            output.writeframesraw(struct.pack("<hh", sample, sample))


class ProductionOrchestrator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._providers = {
            provider.provider_id: provider for provider in settings.render_providers
        }

    def public_providers(self) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for provider in self._providers.values():
            executable_ready: bool | None = None
            if provider.mode == "command":
                executable = Path(provider.argv[0]).expanduser()
                executable_ready = executable.is_file() and os.access(executable, os.X_OK)
            info = provider.public_info(executable_ready=executable_ready)
            if provider.mode == "manual":
                info["note"] = "Creates an auditable copy/paste package; it does not claim authenticated API access."
            elif provider.mode == "mock":
                info["note"] = "Creates a deterministic test tone only."
            else:
                info["note"] = "Runs an operator-configured argv-only adapter without a shell."
            results.append(info)
        return sorted(results, key=lambda item: str(item["id"]))

    def require_provider_ids(self, provider_ids: list[str]) -> list[RenderProviderConfig]:
        missing = [provider_id for provider_id in provider_ids if provider_id not in self._providers]
        if missing:
            raise ProductionError(f"unknown render providers: {', '.join(missing)}")
        return [self._providers[provider_id] for provider_id in provider_ids]

    def build(
        self,
        *,
        job_dir: Path,
        source_job: JobRecord,
        source_job_dir: Path,
        request: ProductionRenderRequest,
    ) -> dict[str, object]:
        providers = self.require_provider_ids(request.provider_ids)
        ranking = rank_generation_candidates(
            source_job_dir,
            source_job.request,
            source_job.result,
        )
        selected_number = (
            int(ranking["recommended_candidate"])
            if request.candidate == "best-technical"
            else int(request.candidate)
        )
        ranking_items = ranking["ranking"]
        if not isinstance(ranking_items, list):
            raise ProductionError("candidate ranking receipt is malformed")
        selected = next(
            (
                item
                for item in ranking_items
                if isinstance(item, dict) and item.get("candidate") == selected_number
            ),
            None,
        )
        if selected is None:
            raise ProductionError(f"candidate {selected_number} does not exist")
        if not selected.get("eligible"):
            raise ProductionError(f"candidate {selected_number} is technically ineligible")

        production_root = job_dir / "production"
        composition_dir = production_root / "composition"
        audit_dir = production_root / "audit"
        providers_dir = production_root / "providers"
        composition_dir.mkdir(parents=True)
        audit_dir.mkdir(parents=True)
        providers_dir.mkdir(parents=True)

        style = str(source_job.request.get("style", ""))
        lyrics = str(source_job.request.get("lyrics", ""))
        (composition_dir / "style.txt").write_text(style + "\n", encoding="utf-8")
        (composition_dir / "lyrics.txt").write_text(lyrics + "\n", encoding="utf-8")

        score_relative = selected.get("score")
        score_source: Path | None = None
        if isinstance(score_relative, str):
            score_source = _safe_child(source_job_dir, score_relative)
            if not score_source.is_file():
                raise ProductionError("selected candidate score is missing")
            shutil.copy2(score_source, composition_dir / "score.abc")

        audio_relative = selected.get("audio")
        if not isinstance(audio_relative, str):
            raise ProductionError("selected candidate audio receipt is missing")
        audio_source = _safe_child(source_job_dir, audio_relative)
        if not audio_source.is_file():
            raise ProductionError("selected candidate audio is missing")
        audit_audio = audit_dir / f"selected-yue2-audio{audio_source.suffix.lower()}"
        shutil.copy2(audio_source, audit_audio)

        _write_json(audit_dir / "source-job-request.json", source_job.request)
        _write_json(audit_dir / "source-job-result.json", source_job.result or {})
        _write_json(audit_dir / "candidate-ranking.json", ranking)

        rights_warnings = [
            "Provider terms and source rights must be verified for the intended release territory and use.",
            "The controller does not certify copyright ownership or commercial eligibility.",
        ]
        if self.settings.model_use_scope == "noncommercial":
            rights_warnings.append(
                "The YuE2/SheetSage2 source run is recorded as noncommercial; its audio is kept in audit only and is not sent to renderer packages."
            )
        provider_receipts: list[dict[str, object]] = []
        for provider in providers:
            provider_receipts.append(
                self._build_provider_package(
                    provider=provider,
                    providers_dir=providers_dir,
                    composition_dir=composition_dir,
                    selected=selected,
                    request=request,
                    rights_warnings=rights_warnings,
                )
            )

        manual_exports = sum(receipt["mode"] == "manual" for receipt in provider_receipts)
        review_required = manual_exports > 0 or any(
            receipt.get("status") == "needs_review" for receipt in provider_receipts
        )
        review_required = review_required or any(
            receipt.get("commercial_status") != "operator-verified"
            for receipt in provider_receipts
            if receipt.get("mode") != "mock"
        )
        manifest: dict[str, object] = {
            "schema": "yue2-music-os.production-manifest.v1",
            "status": "complete",
            "title": request.title,
            "notes": request.notes,
            "source_generation_job_id": source_job.id,
            "selected_candidate": selected_number,
            "candidate_selection": request.candidate,
            "technical_score": selected.get("technical_score"),
            "technical_ranking_only": True,
            "commercial_intent": request.commercial_intent,
            "license_review_acknowledged": request.license_review_acknowledged,
            "source_model_use_scope": self.settings.model_use_scope,
            "source_model": self.settings.yue2_model,
            "source_model_revision": self.settings.yue2_revision,
            "provider_ids": request.provider_ids,
            "provider_receipts": provider_receipts,
            "source_audio_in_provider_packages": False,
            "review_required": review_required,
            "rights_warnings": rights_warnings,
            "limitations": ranking["limitations"],
        }
        _write_json(production_root / "production-manifest.json", manifest)
        _write_json(job_dir / "job-result.json", manifest)
        return manifest

    def _build_provider_package(
        self,
        *,
        provider: RenderProviderConfig,
        providers_dir: Path,
        composition_dir: Path,
        selected: dict[str, object],
        request: ProductionRenderRequest,
        rights_warnings: list[str],
    ) -> dict[str, object]:
        if request.commercial_intent and provider.mode == "mock":
            raise ProductionError("mock-renderer cannot be used for commercial intent")
        if (
            request.commercial_intent
            and provider.mode == "command"
            and provider.commercial_status != "operator-verified"
        ):
            raise ProductionError(
                f"live command provider {provider.provider_id!r} requires commercial_status=operator-verified"
            )

        provider_dir = providers_dir / provider.provider_id
        provider_dir.mkdir()
        shutil.copy2(composition_dir / "style.txt", provider_dir / "style.txt")
        shutil.copy2(composition_dir / "lyrics.txt", provider_dir / "lyrics.txt")
        score_file = composition_dir / "score.abc"
        if score_file.is_file():
            shutil.copy2(score_file, provider_dir / "score.abc")

        payload: dict[str, object] = {
            "schema": "yue2-music-os.render-request.v1",
            "provider": {
                "id": provider.provider_id,
                "label": provider.label,
                "mode": provider.mode,
                "commercial_status": provider.commercial_status,
                "terms_reference": provider.terms_reference,
            },
            "title": request.title,
            "notes": request.notes,
            "composition": {
                "style_file": "style.txt",
                "lyrics_file": "lyrics.txt",
                "score_file": "score.abc" if score_file.is_file() else None,
                "selected_candidate": selected.get("candidate"),
                "selected_seed": selected.get("seed"),
                "source_audio_included": False,
            },
            "instruction": (
                "Create a new performance from the supplied style, lyrics, and optional ABC score. "
                "Do not copy, upload, or depend on the audit-only YuE2 audio."
            ),
            "commercial_intent": request.commercial_intent,
            "operator_license_review_acknowledged": request.license_review_acknowledged,
            "rights_warnings": rights_warnings,
            "output_contract": {
                "result_receipt": "output/render-result.json",
                "receipt_status": ["complete", "needs_review"],
                "outputs": "relative file paths under output/",
            },
        }
        request_json = provider_dir / "render-request.json"
        _write_json(request_json, payload)

        if provider.mode == "manual":
            readme = f"""# {provider.label}

This is an auditable manual export package. No authenticated provider API call was made.

1. Review `render-request.json`, `style.txt`, `lyrics.txt`, and optional `score.abc`.
2. Confirm the provider plan and rights for the intended commercial use.
3. Render a new performance. Do not upload the audit-only YuE2 audio as a reference.
4. Save the provider output and its receipt alongside this package.

Commercial status recorded by the controller: `{provider.commercial_status}`.
"""
            (provider_dir / "README.md").write_text(readme, encoding="utf-8")
            receipt: dict[str, object] = {
                "provider_id": provider.provider_id,
                "label": provider.label,
                "mode": provider.mode,
                "status": "exported",
                "live_execution": False,
                "commercial_status": provider.commercial_status,
                "package": provider_dir.name,
            }
            _write_json(provider_dir / "export-receipt.json", receipt)
            return receipt

        if provider.mode == "mock":
            output_dir = provider_dir / "output"
            output_dir.mkdir()
            audio = output_dir / "final-render.wav"
            seed = selected.get("seed")
            _write_mock_wave(audio, seed=int(seed) if isinstance(seed, int) else 0)
            result = {
                "status": "complete",
                "outputs": [audio.name],
                "warning": "Deterministic mock tone; not a music render.",
            }
            _write_json(output_dir / "render-result.json", result)
            return {
                "provider_id": provider.provider_id,
                "label": provider.label,
                "mode": provider.mode,
                "status": "complete",
                "live_execution": True,
                "commercial_status": provider.commercial_status,
                "outputs": [f"output/{audio.name}"],
            }

        return self._run_command_provider(provider, provider_dir, request_json)

    def _run_command_provider(
        self,
        provider: RenderProviderConfig,
        provider_dir: Path,
        request_json: Path,
    ) -> dict[str, object]:
        executable = Path(provider.argv[0]).expanduser()
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ProductionError(
                f"render provider executable is not ready: {executable}"
            )
        output_dir = provider_dir / "output"
        output_dir.mkdir()
        replacements = {
            "request_json": str(request_json.resolve()),
            "output_dir": str(output_dir.resolve()),
            "provider_id": provider.provider_id,
        }
        try:
            argv = [part.format_map(replacements) for part in provider.argv]
        except (KeyError, ValueError) as exc:
            raise ProductionError(
                f"render provider {provider.provider_id!r} has invalid placeholders"
            ) from exc
        try:
            command = run_command(
                argv,
                cwd=provider_dir,
                timeout_seconds=provider.timeout_seconds
                or self.settings.command_timeout_seconds,
                log_prefix=provider_dir / "provider-command",
            )
        except EngineError as exc:
            raise ProductionError(str(exc)) from exc

        result_path = output_dir / "render-result.json"
        result = _read_json(result_path)
        if result is None:
            raise ProductionError(
                f"provider {provider.provider_id!r} did not write output/render-result.json"
            )
        status = result.get("status")
        if status not in {"complete", "needs_review"}:
            raise ProductionError(
                f"provider {provider.provider_id!r} returned unsupported status {status!r}"
            )
        outputs = result.get("outputs")
        if not isinstance(outputs, list) or not outputs or not all(
            isinstance(item, str) for item in outputs
        ):
            raise ProductionError(
                f"provider {provider.provider_id!r} receipt requires a non-empty outputs list"
            )
        validated: list[str] = []
        for relative in outputs:
            path = _safe_child(output_dir, relative)
            if not path.is_file() or path.stat().st_size <= 0:
                raise ProductionError(
                    f"provider output is missing or empty: {relative}"
                )
            validated.append(f"output/{Path(relative).as_posix()}")
        return {
            "provider_id": provider.provider_id,
            "label": provider.label,
            "mode": provider.mode,
            "status": status,
            "live_execution": True,
            "commercial_status": provider.commercial_status,
            "terms_reference": provider.terms_reference,
            "elapsed_seconds": command.elapsed_seconds,
            "outputs": validated,
        }
