from __future__ import annotations

import json
import math
import os
import signal
import struct
import subprocess
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from .abc_tools import parse, report, strip_chords
from .config import Settings
from .sample_data import SAMPLE_SCORE


class EngineError(RuntimeError):
    pass


@dataclass(slots=True)
class CommandResult:
    argv: list[str]
    returncode: int
    elapsed_seconds: float
    stdout: str
    stderr: str


class MusicEngine(Protocol):
    def generate(
        self,
        *,
        job_dir: Path,
        style: str,
        lyrics: str,
        cot: str,
        seed: int,
        candidate_count: int,
        abc_path: Path | None,
    ) -> dict[str, object]: ...

    def transcribe(
        self,
        *,
        job_dir: Path,
        source_path: Path,
        melody_only: bool,
    ) -> dict[str, object]: ...

    def doctor(self) -> dict[str, object]: ...


def _write_json(path: Path, data: object) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_log_tail(path: Path, max_bytes: int = 256 * 1024) -> str:
    """Read only the UTF-8-safe tail of a potentially large process log."""
    if not path.is_file():
        return ""
    with path.open("rb") as handle:
        size = handle.seek(0, os.SEEK_END)
        handle.seek(max(0, size - max_bytes))
        data = handle.read()
    return data.decode("utf-8", errors="replace")


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    log_prefix: Path,
    allowed_returncodes: Iterable[int] = (0,),
) -> CommandResult:
    if not argv or any(not isinstance(part, str) or "\x00" in part for part in argv):
        raise EngineError("invalid command arguments")
    cwd = cwd.resolve()
    cwd.mkdir(parents=True, exist_ok=True)
    log_prefix.parent.mkdir(parents=True, exist_ok=True)
    accepted_returncodes = tuple(allowed_returncodes)
    if not accepted_returncodes:
        raise EngineError("allowed_returncodes cannot be empty")
    stdout_path = log_prefix.with_suffix(".stdout.log")
    stderr_path = log_prefix.with_suffix(".stderr.log")
    command_record = {
        "argv": argv,
        "cwd": str(cwd),
        "timeout_seconds": timeout_seconds,
        "allowed_returncodes": list(accepted_returncodes),
        "stdout_log": stdout_path.name,
        "stderr_log": stderr_path.name,
    }
    _write_json(log_prefix.with_suffix(".command.json"), command_record)
    env = os.environ.copy()
    env.update({"PYTHONUNBUFFERED": "1", "TOKENIZERS_PARALLELISM": "false"})
    started = time.monotonic()
    timed_out: subprocess.TimeoutExpired | None = None
    with stdout_path.open("w", encoding="utf-8", errors="replace", buffering=1) as stdout_log, \
        stderr_path.open("w", encoding="utf-8", errors="replace", buffering=1) as stderr_log:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=stdout_log,
            stderr=stderr_log,
            text=True,
            start_new_session=True,
        )
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            timed_out = exc
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
    elapsed = time.monotonic() - started
    stdout = _read_log_tail(stdout_path)
    stderr = _read_log_tail(stderr_path)
    result = CommandResult(argv, process.returncode, elapsed, stdout, stderr)
    _write_json(
        log_prefix.with_suffix(".result.json"),
        {
            "returncode": result.returncode,
            "elapsed_seconds": result.elapsed_seconds,
            "allowed_returncodes": list(accepted_returncodes),
            "timed_out": timed_out is not None,
            "captured_in_memory": "log tails only",
        },
    )
    if timed_out is not None:
        raise EngineError(f"command timed out after {timeout_seconds}s") from timed_out
    if result.returncode not in set(accepted_returncodes):
        tail = (stderr or stdout)[-2000:]
        raise EngineError(
            f"command failed with exit code {result.returncode}: {tail.strip()}"
        )
    return result


def _write_demo_wave(path: Path, *, seed: int, seconds: float = 2.0) -> None:
    sample_rate = 48_000
    frames = int(sample_rate * seconds)
    base_frequency = 220 + (seed % 12) * 11
    amplitude = 0.16
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        for index in range(frames):
            envelope = min(1.0, index / (sample_rate * 0.05))
            envelope *= min(1.0, (frames - index) / (sample_rate * 0.08))
            sample = int(
                32767
                * amplitude
                * envelope
                * (
                    math.sin(2 * math.pi * base_frequency * index / sample_rate)
                    + 0.35
                    * math.sin(2 * math.pi * base_frequency * 1.5 * index / sample_rate)
                )
                / 1.35
            )
            packed = struct.pack("<hh", sample, sample)
            output.writeframesraw(packed)


class MockEngine:
    """Deterministic engine for UI, API, storage, and invariant smoke tests."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def doctor(self) -> dict[str, object]:
        return {
            "engine": "mock",
            "ready": True,
            "gpu_required": False,
            "note": "No model weights are loaded; audio is a deterministic test tone.",
        }

    def generate(
        self,
        *,
        job_dir: Path,
        style: str,
        lyrics: str,
        cot: str,
        seed: int,
        candidate_count: int,
        abc_path: Path | None,
    ) -> dict[str, object]:
        score = abc_path.read_text(encoding="utf-8") if abc_path else SAMPLE_SCORE
        if cot == "off":
            score = ""
        elif cot == "melody":
            parsed = parse(score)
            if any(voice.chords for voice in parsed.voices.values()):
                score = strip_chords(score)
        output_root = job_dir / "output"
        output_root.mkdir()
        candidates: list[dict[str, object]] = []
        for index in range(candidate_count):
            candidate_seed = seed + index
            candidate = output_root / f"candidate-{index + 1:02d}"
            candidate.mkdir()
            request = {
                "id": f"candidate-{index + 1:02d}",
                "style": style,
                "lyrics": lyrics,
                "cot": cot,
                "seed": candidate_seed,
            }
            _write_json(candidate / "request.json", request)
            if score:
                (candidate / "score.abc").write_text(score, encoding="utf-8")
                _write_json(candidate / "abc_check.json", report(parse(score)))
            _write_demo_wave(candidate / "audio.wav", seed=candidate_seed)
            result = {
                "status": "mock-complete",
                "candidate": index + 1,
                "seed": candidate_seed,
                "audio_seconds": 2.0,
                "sample_rate": 48_000,
                "warning": "Mock audio is not YuE2 output.",
            }
            _write_json(candidate / "result.json", result)
            candidates.append(result)
        summary = {
            "engine": "mock",
            "candidate_count": candidate_count,
            "candidates": candidates,
            "limitations": [
                "No YuE2 model was loaded.",
                "Audio quality and prompt adherence were not evaluated.",
            ],
        }
        _write_json(job_dir / "job-result.json", summary)
        return summary

    def transcribe(
        self,
        *,
        job_dir: Path,
        source_path: Path,
        melody_only: bool,
    ) -> dict[str, object]:
        output = job_dir / "output"
        output.mkdir()
        score = SAMPLE_SCORE
        if melody_only:
            score = strip_chords(score)
        (output / "score.abc").write_text(score, encoding="utf-8")
        result = {
            "engine": "mock",
            "status": "mock-complete",
            "source_name": source_path.name,
            "melody_only": melody_only,
            "abc_check": report(parse(score)),
            "warning": "The source audio was not analyzed by SheetSage2.",
        }
        _write_json(output / "transcription_manifest.json", result)
        _write_json(job_dir / "job-result.json", result)
        return result


class LocalEngine:
    """Runs first-party YuE2 helper scripts in separate local Python environments."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def helper_dir(self) -> Path:
        return self.settings.yue2_repo / "skills" / "yue2-music" / "scripts"

    def doctor(self) -> dict[str, object]:
        checks = {
            "yue2_python": self.settings.yue2_python.is_file(),
            "yue2_repo": self.settings.yue2_repo.is_dir(),
            "run_yue2_helper": (self.helper_dir / "run_yue2.py").is_file(),
            "transcribe_helper": (self.helper_dir / "transcribe.py").is_file(),
            "sheetsage2_python": self.settings.sheetsage2_python.is_file(),
        }
        yue2_ready = all(checks[name] for name in ("yue2_python", "yue2_repo", "run_yue2_helper"))
        sheetsage2_ready = all(
            checks[name] for name in ("yue2_repo", "transcribe_helper", "sheetsage2_python")
        )
        return {
            "engine": "local",
            "ready": yue2_ready and sheetsage2_ready,
            "yue2_ready": yue2_ready,
            "sheetsage2_ready": sheetsage2_ready,
            "checks": checks,
            "model_use_scope": self.settings.model_use_scope,
            "revisions": {
                "yue2": self.settings.yue2_revision,
                "yue2_vae": self.settings.yue2_vae_revision,
                "sheetsage2": self.settings.sheetsage2_revision,
            },
        }

    def _require_yue2_ready(self) -> None:
        self.settings.assert_real_engine_allowed()
        status = self.doctor()
        required = ("yue2_python", "yue2_repo", "run_yue2_helper")
        missing = {name: status["checks"][name] for name in required if not status["checks"][name]}
        if missing:
            raise EngineError(f"YuE2 engine is not ready: {missing}")

    def _require_sheetsage_ready(self) -> None:
        self.settings.assert_real_engine_allowed()
        status = self.doctor()
        required = ("yue2_repo", "transcribe_helper", "sheetsage2_python")
        missing = {name: status["checks"][name] for name in required if not status["checks"][name]}
        if missing:
            raise EngineError(f"SheetSage2 engine is not ready: {missing}")

    def generate(
        self,
        *,
        job_dir: Path,
        style: str,
        lyrics: str,
        cot: str,
        seed: int,
        candidate_count: int,
        abc_path: Path | None,
    ) -> dict[str, object]:
        self._require_yue2_ready()
        if cot == "off" and abc_path is not None:
            raise EngineError("cot=off cannot accept ABC")
        output_root = job_dir / "output"
        output_root.mkdir()
        candidates: list[dict[str, object]] = []
        for index in range(candidate_count):
            candidate_seed = seed + index
            request_path = job_dir / f"request-{index + 1:02d}.json"
            _write_json(
                request_path,
                {
                    "id": f"candidate-{index + 1:02d}",
                    "style": style,
                    "lyrics": lyrics,
                    "cot": cot,
                    "seed": candidate_seed,
                },
            )
            destination = output_root / f"candidate-{index + 1:02d}"
            argv = [
                str(self.settings.yue2_python),
                str(self.helper_dir / "run_yue2.py"),
                "generate",
                "--request",
                str(request_path),
                "--cot",
                cot,
                "--output",
                str(destination),
                "--model",
                self.settings.yue2_model,
                "--vae",
                self.settings.yue2_vae,
            ]
            if self.settings.yue2_revision:
                argv.extend(["--revision", self.settings.yue2_revision])
            if self.settings.yue2_vae_revision:
                argv.extend(["--vae-revision", self.settings.yue2_vae_revision])
            if abc_path is not None:
                argv.extend(["--abc-file", str(abc_path)])
            command = run_command(
                argv,
                cwd=self.settings.yue2_repo,
                timeout_seconds=self.settings.command_timeout_seconds,
                log_prefix=job_dir / f"candidate-{index + 1:02d}",
                allowed_returncodes=(0, 1),
            )
            run_file = destination / "run.json"
            failure_file = destination / "failure.json"
            audio_file = destination / "audio.flac"
            if not run_file.is_file():
                raise EngineError("YuE2 helper returned without the required run.json receipt")
            try:
                run_data = json.loads(run_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise EngineError("YuE2 run.json is unreadable or invalid") from exc
            results = run_data.get("results") if isinstance(run_data, dict) else None
            if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
                raise EngineError("YuE2 run.json does not contain exactly one candidate result")
            candidate_result = results[0]
            candidate_status = candidate_result.get("status")
            failure = None
            if failure_file.is_file():
                try:
                    failure = json.loads(failure_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise EngineError("YuE2 failure.json is unreadable or invalid") from exc
            if candidate_status == "failed":
                detail = candidate_result.get("error") or failure or "unknown model failure"
                raise EngineError(f"YuE2 candidate failed: {detail}")
            if candidate_status not in {"complete", "needs_review"}:
                raise EngineError(f"YuE2 returned unsupported candidate status: {candidate_status!r}")
            if command.returncode == 0 and candidate_status != "complete":
                raise EngineError("YuE2 exit status disagrees with run.json")
            if command.returncode == 1 and candidate_status != "needs_review":
                raise EngineError("YuE2 review exit status disagrees with run.json")
            if not audio_file.is_file() or audio_file.stat().st_size == 0:
                raise EngineError("YuE2 did not preserve the required non-empty audio.flac")
            candidates.append(
                {
                    "candidate": index + 1,
                    "seed": candidate_seed,
                    "status": candidate_status,
                    "review_required": candidate_status == "needs_review",
                    "returncode": command.returncode,
                    "elapsed_seconds": command.elapsed_seconds,
                    "run": run_data,
                    "failure": failure,
                }
            )
        summary = {
            "engine": "local-yue2",
            "candidate_count": candidate_count,
            "candidates": candidates,
            "review_required": any(bool(item["review_required"]) for item in candidates),
            "model": self.settings.yue2_model,
            "model_revision": self.settings.yue2_revision,
            "vae": self.settings.yue2_vae,
            "vae_revision": self.settings.yue2_vae_revision,
        }
        _write_json(job_dir / "job-result.json", summary)
        return summary

    def transcribe(
        self,
        *,
        job_dir: Path,
        source_path: Path,
        melody_only: bool,
    ) -> dict[str, object]:
        self._require_sheetsage_ready()
        output = job_dir / "output"
        model = (
            str(self.settings.sheetsage2_dir)
            if self.settings.sheetsage2_dir.is_dir()
            else self.settings.sheetsage2_model
        )
        argv = [
            str(self.settings.sheetsage2_python),
            str(self.helper_dir / "transcribe.py"),
            str(source_path),
            "--output",
            str(output),
            "--task",
            "melody-full" if melody_only else "full",
            "--model",
            model,
        ]
        if self.settings.sheetsage2_revision and model == self.settings.sheetsage2_model:
            argv.extend(["--revision", self.settings.sheetsage2_revision])
        if self.settings.sheetsage2_base_model:
            argv.extend(["--base-model", str(self.settings.sheetsage2_base_model)])
        command = run_command(
            argv,
            cwd=self.settings.yue2_repo,
            timeout_seconds=self.settings.command_timeout_seconds,
            log_prefix=job_dir / "transcribe",
        )
        manifest_path = output / "transcription_manifest.json"
        if not manifest_path.is_file() or not (output / "score.abc").is_file():
            raise EngineError("SheetSage2 did not preserve the required manifest and score")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EngineError("SheetSage2 transcription manifest is unreadable or invalid") from exc
        if not isinstance(manifest, dict) or manifest.get("status") != "complete":
            raise EngineError("SheetSage2 transcription manifest does not report completion")
        try:
            parse((output / "score.abc").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise EngineError("SheetSage2 score.abc failed the native symbolic check") from exc
        summary = {
            "engine": "local-sheetsage2",
            "elapsed_seconds": command.elapsed_seconds,
            "model": model,
            "model_revision": self.settings.sheetsage2_revision,
            "manifest": manifest,
        }
        _write_json(job_dir / "job-result.json", summary)
        return summary


def build_engine(settings: Settings) -> MusicEngine:
    if settings.engine == "mock":
        return MockEngine(settings)
    return LocalEngine(settings)
