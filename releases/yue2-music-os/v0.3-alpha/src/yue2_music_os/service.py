from __future__ import annotations

import html
import json
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import BinaryIO, Callable

from .abc_tools import VOICES, compare, parse, report, strip_chords
from .config import Settings
from .engines import MusicEngine, build_engine
from .production import (
    ProductionOrchestrator,
    rank_generation_candidates,
    write_ranking_report,
)
from .models import (
    CompareRequest,
    GenerateRequest,
    JobKind,
    JobRecord,
    JobStatus,
    ProductionRenderRequest,
    RankCandidatesRequest,
    StripChordsRequest,
    TranscribeRequest,
)
from .storage import Store


class ServiceError(RuntimeError):
    """A user-actionable orchestration error."""


class _ProcessLock:
    """Advisory single-process lock for one data directory on macOS/Linux."""

    def __init__(self, path: Path) -> None:
        try:
            import fcntl
        except ImportError as exc:  # pragma: no cover - target platforms provide it
            raise ServiceError(
                "single-instance locking requires a POSIX platform"
            ) from exc
        self._fcntl = fcntl
        self._handle: BinaryIO = path.open("a+b")
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._handle.close()
            raise ServiceError(
                f"another YuE2 Music OS process already owns {path.parent}"
            ) from exc
        self._handle.seek(0)
        self._handle.truncate()
        self._handle.write(f"pid={os.getpid()}\n".encode("ascii"))
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        if self._handle.closed:
            return
        self._fcntl.flock(self._handle.fileno(), self._fcntl.LOCK_UN)
        self._handle.close()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class MusicService:
    """Owns the single sequential worker and keeps every result auditable."""

    def __init__(
        self,
        settings: Settings,
        store: Store | None = None,
        engine: MusicEngine | None = None,
        enforce_single_instance: bool = True,
    ) -> None:
        self.settings = settings
        self.store = store or Store(settings.data_dir)
        self.engine = engine or build_engine(settings)
        self.production = ProductionOrchestrator(settings)
        self._process_lock = (
            _ProcessLock(self.store.root / "service.lock")
            if enforce_single_instance
            else None
        )
        try:
            self._recovered_jobs = (
                self.store.recover_incomplete_jobs()
                if enforce_single_instance
                else 0
            )
            self._executor = ThreadPoolExecutor(
                max_workers=settings.gpu_workers,
                thread_name_prefix="yue2-music-os",
            )
        except Exception:
            if self._process_lock is not None:
                self._process_lock.close()
            raise
        self._futures: dict[str, Future[None]] = {}
        self._lock = threading.RLock()
        self._closed = False

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        try:
            self._executor.shutdown(wait=True, cancel_futures=False)
        finally:
            if self._process_lock is not None:
                self._process_lock.close()

    def doctor(self) -> dict[str, object]:
        return {
            "service": "ready" if not self._closed else "closed",
            "worker_count": self.settings.gpu_workers,
            "single_instance_lock": self._process_lock is not None,
            "recovered_incomplete_jobs": self._recovered_jobs,
            "engine": self.engine.doctor(),
            "policy": self.settings.public_policy(),
            "render_providers": self.production.public_providers(),
        }

    def submit_generate(self, request: GenerateRequest) -> JobRecord:
        abc_path: Path | None = None
        if request.abc_artifact_id:
            abc_path = self._artifact_path(
                request.project_id, request.abc_artifact_id, allowed_kinds={"score"}
            )
            score = parse(abc_path.read_text(encoding="utf-8"))
            if request.cot == "melody" and any(
                voice.chords for voice in score.voices.values()
            ):
                raise ServiceError(
                    "cot=melody requires a chord-free score. Run Strip Chords first."
                )
        job = self.store.create_job(
            request.project_id,
            JobKind.GENERATE,
            request.model_dump(mode="json"),
        )
        return self._submit(
            job,
            lambda job_dir: self.engine.generate(
                job_dir=job_dir,
                style=request.style,
                lyrics=request.lyrics,
                cot=request.cot,
                seed=request.seed,
                candidate_count=request.candidate_count,
                abc_path=abc_path,
            ),
        )

    def submit_transcribe(self, request: TranscribeRequest) -> JobRecord:
        source_path = self._artifact_path(
            request.project_id, request.source_artifact_id, allowed_kinds={"audio"}
        )
        job = self.store.create_job(
            request.project_id,
            JobKind.TRANSCRIBE,
            request.model_dump(mode="json"),
        )
        return self._submit(
            job,
            lambda job_dir: self.engine.transcribe(
                job_dir=job_dir,
                source_path=source_path,
                melody_only=request.melody_only,
            ),
        )

    def submit_compare(self, request: CompareRequest) -> JobRecord:
        before_path = self._artifact_path(
            request.project_id, request.before_artifact_id, allowed_kinds={"score"}
        )
        after_path = self._artifact_path(
            request.project_id, request.after_artifact_id, allowed_kinds={"score"}
        )
        job = self.store.create_job(
            request.project_id,
            JobKind.COMPARE,
            request.model_dump(mode="json"),
        )

        def work(job_dir: Path) -> dict[str, object]:
            before_text = before_path.read_text(encoding="utf-8")
            after_text = after_path.read_text(encoding="utf-8")
            before = parse(before_text)
            after = parse(after_text)
            names = VOICES if request.voices == "both" else (request.voices,)
            comparison = compare(
                before,
                after,
                names=names,
                allow_tempo_change=request.allow_tempo_change,
            )
            payload: dict[str, object] = {
                "status": "complete",
                "comparison": comparison,
                "before": {
                    "artifact_id": request.before_artifact_id,
                    "name": self.store.get_artifact(request.before_artifact_id).name,
                    "score": report(before),
                },
                "after": {
                    "artifact_id": request.after_artifact_id,
                    "name": self.store.get_artifact(request.after_artifact_id).name,
                    "score": report(after),
                },
                "limitations": [
                    "This verifies symbolic events only.",
                    "It does not prove note realization, audio quality, timbre, or waveform preservation.",
                ],
            }
            _write_json(job_dir / "comparison.json", payload)
            self._write_comparison_html(job_dir / "comparison.html", payload)
            _write_json(job_dir / "job-result.json", payload)
            return payload

        return self._submit(job, work)

    def submit_strip_chords(self, request: StripChordsRequest) -> JobRecord:
        source_path = self._artifact_path(
            request.project_id, request.source_artifact_id, allowed_kinds={"score"}
        )
        job = self.store.create_job(
            request.project_id,
            JobKind.STRIP_CHORDS,
            request.model_dump(mode="json"),
        )

        def work(job_dir: Path) -> dict[str, object]:
            original_text = source_path.read_text(encoding="utf-8")
            stripped_text = strip_chords(original_text, keep_voice=request.keep_voice)
            output = job_dir / "score-no-chords.abc"
            output.write_text(stripped_text, encoding="utf-8")
            before = parse(original_text)
            after = parse(stripped_text)
            names = VOICES if request.keep_voice == "both" else (request.keep_voice,)
            invariant = compare(before, after, names=names)
            result: dict[str, object] = {
                "status": "complete",
                "source_artifact_id": request.source_artifact_id,
                "kept_voice": request.keep_voice,
                "melody_invariant": invariant,
                "remaining_chords": sum(
                    len(voice.chords) for voice in after.voices.values()
                ),
                "limitations": ["Symbolic check only; no audio was generated."],
            }
            _write_json(job_dir / "strip-report.json", result)
            _write_json(job_dir / "job-result.json", result)
            return result

        return self._submit(job, work)

    def list_render_providers(self) -> list[dict[str, object]]:
        return self.production.public_providers()

    def submit_rank_candidates(self, request: RankCandidatesRequest) -> JobRecord:
        source_job = self._generation_job(request.project_id, request.generation_job_id)
        source_job_dir = self.store.job_dir(source_job.project_id, source_job.id)
        job = self.store.create_job(
            request.project_id,
            JobKind.RANK_CANDIDATES,
            request.model_dump(mode="json"),
        )

        def work(job_dir: Path) -> dict[str, object]:
            ranking = rank_generation_candidates(
                source_job_dir, source_job.request, source_job.result
            )
            ranking["source_generation_job_id"] = source_job.id
            write_ranking_report(job_dir, ranking)
            _write_json(job_dir / "job-result.json", ranking)
            return ranking

        return self._submit(job, work)

    def submit_production_render(
        self, request: ProductionRenderRequest
    ) -> JobRecord:
        source_job = self._generation_job(request.project_id, request.generation_job_id)
        self.production.require_provider_ids(request.provider_ids)
        source_job_dir = self.store.job_dir(source_job.project_id, source_job.id)
        job = self.store.create_job(
            request.project_id,
            JobKind.PRODUCTION_RENDER,
            request.model_dump(mode="json"),
        )
        return self._submit(
            job,
            lambda job_dir: self.production.build(
                job_dir=job_dir,
                source_job=source_job,
                source_job_dir=source_job_dir,
                request=request,
            ),
        )

    def wait(self, job_id: str, timeout: float | None = None) -> JobRecord:
        with self._lock:
            future = self._futures.get(job_id)
        if future is not None:
            future.result(timeout=timeout)
        return self.store.get_job(job_id)

    def _generation_job(self, project_id: str, job_id: str) -> JobRecord:
        source = self.store.get_job(job_id)
        if source.project_id != project_id:
            raise ServiceError("generation job does not belong to project")
        if source.kind != JobKind.GENERATE:
            raise ServiceError("source job must be a generate job")
        if source.status != JobStatus.SUCCEEDED or source.result is None:
            raise ServiceError("generation job must have succeeded before ranking or rendering")
        return source

    def _artifact_path(
        self,
        project_id: str,
        artifact_id: str,
        *,
        allowed_kinds: set[str],
    ) -> Path:
        artifact = self.store.get_artifact(artifact_id)
        if artifact.project_id != project_id:
            raise ServiceError("artifact does not belong to project")
        if artifact.kind not in allowed_kinds:
            expected = ", ".join(sorted(allowed_kinds))
            raise ServiceError(
                f"artifact kind {artifact.kind!r} is not valid here; expected {expected}"
            )
        return self.store.get_artifact_path(artifact_id)

    def _submit(
        self,
        job: JobRecord,
        operation: Callable[[Path], dict[str, object]],
    ) -> JobRecord:
        with self._lock:
            if self._closed:
                raise ServiceError("service is closed")
            future = self._executor.submit(self._execute, job, operation)
            self._futures[job.id] = future
            future.add_done_callback(lambda _future, job_id=job.id: self._forget(job_id))
        return job

    def _forget(self, job_id: str) -> None:
        with self._lock:
            self._futures.pop(job_id, None)

    def _execute(
        self,
        job: JobRecord,
        operation: Callable[[Path], dict[str, object]],
    ) -> None:
        self.store.update_job(job.id, status=JobStatus.RUNNING)
        job_dir = self.store.job_dir(job.project_id, job.id)
        try:
            result = operation(job_dir)
            artifacts = self._register_job_files(job.project_id, job.id, job_dir)
            enriched = dict(result)
            enriched["artifacts"] = [artifact.model_dump(mode="json") for artifact in artifacts]
            enriched["artifact_count"] = len(artifacts)
            self.store.update_job(
                job.id,
                status=JobStatus.SUCCEEDED,
                result=enriched,
            )
        except Exception as exc:
            failure = {
                "status": "failed",
                "type": type(exc).__name__,
                "error": str(exc),
            }
            try:
                _write_json(job_dir / "service-failure.json", failure)
                self._register_job_files(job.project_id, job.id, job_dir)
            except Exception as registration_exc:
                failure["artifact_registration_error"] = str(registration_exc)
            self.store.update_job(
                job.id,
                status=JobStatus.FAILED,
                result=failure,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _register_job_files(
        self, project_id: str, job_id: str, job_dir: Path
    ) -> list:
        records = []
        for path in sorted(job_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(job_dir).as_posix()
            display_name = relative.replace("/", "__")
            records.append(
                self.store.register_generated_file(
                    project_id,
                    job_id,
                    path,
                    display_name=display_name,
                )
            )
        return records

    @staticmethod
    def _write_comparison_html(path: Path, payload: dict[str, object]) -> None:
        comparison = payload["comparison"]
        pretty = html.escape(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        )
        match = bool(comparison.get("match")) if isinstance(comparison, dict) else False
        badge = "PASS" if match else "CHANGED"
        document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YuE2 Music OS symbolic comparison</title>
<style>
body{{font:16px/1.55 system-ui,sans-serif;max-width:980px;margin:40px auto;padding:0 20px;background:#101112;color:#f4efe8}}
.badge{{display:inline-block;padding:.35rem .7rem;border:1px solid currentColor;border-radius:999px;font-weight:800}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#1a1c1e;padding:18px;border-radius:14px;border:1px solid #34373a}}
small{{color:#b9b5ae}}
</style>
</head>
<body>
<h1>Symbolic comparison <span class="badge">{badge}</span></h1>
<p>This report checks the supported YuE2/SheetSage2 ABC event model. It is not an audio-quality or waveform-preservation certificate.</p>
<pre>{pretty}</pre>
<small>Generated locally by YuE2 Music OS v0.2 alpha.</small>
</body>
</html>
"""
        path.write_text(document, encoding="utf-8")
