from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel, Field, field_validator, model_validator

from .note_ir import (
    DetectedTrack,
    MusicIR,
    NoteEditReceipt,
    NotePatchRequest,
    ProviderTier,
    TimeSignature,
    TranscriptionResult,
    apply_note_patch,
    fuse_transcriptions,
    music_ir_to_midi_bytes,
    review_queue,
    utc_now,
)
from .note_providers import NoteProviderError, NoteProviderRegistry
from .storage import NotFound, Store


_PROVIDER_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


class NoteWorkspaceError(RuntimeError):
    """A user-actionable Note IR persistence or orchestration error."""


class NoteAnalysisRequest(BaseModel):
    project_id: str
    source_artifact_id: str
    provider_ids: list[str] = Field(default_factory=list, max_length=8)
    title: str | None = Field(default=None, max_length=200)
    instrument_hint: str | None = Field(default=None, max_length=120)
    tempo_bpm: float = Field(default=120.0, gt=0.0, le=400.0)
    time_signature: TimeSignature = Field(default_factory=TimeSignature)
    minimum_review_confidence: float = Field(default=0.82, ge=0.0, le=1.0)

    @field_validator("provider_ids")
    @classmethod
    def validate_provider_ids(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for provider_id in value:
            candidate = provider_id.strip().lower()
            if not _PROVIDER_ID.fullmatch(candidate):
                raise ValueError(f"invalid provider id: {provider_id!r}")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized


class NoteImportRequest(BaseModel):
    project_id: str
    source_artifact_id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    provider_id: str = "normalized-json"
    provider_version: str | None = Field(default=None, max_length=120)
    provider_tier: ProviderTier = ProviderTier.FREE
    tempo_bpm: float = Field(default=120.0, gt=0.0, le=400.0)
    time_signature: TimeSignature = Field(default_factory=TimeSignature)
    tracks: list[DetectedTrack]
    warnings: list[str] = Field(default_factory=list, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _PROVIDER_ID.fullmatch(normalized):
            raise ValueError("invalid provider id")
        return normalized


class RestoreRevisionRequest(BaseModel):
    revision: int = Field(ge=1)
    reason: str = Field(default="restore earlier revision", min_length=1, max_length=500)


class NoteJobRecord(BaseModel):
    id: str
    project_id: str
    source_artifact_id: str
    status: str
    request: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class MusicIRSummary(BaseModel):
    music_ir_id: str
    project_id: str
    source_artifact_id: str | None
    title: str
    current_revision: int
    note_count: int
    review_note_count: int
    created_at: datetime
    updated_at: datetime


class RevisionSummary(BaseModel):
    revision_id: str
    music_ir_id: str
    revision: int
    operation: dict[str, Any]
    snapshot_path: str
    created_at: datetime


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


class NoteWorkspace:
    """Immutable Note IR revisions plus a single sequential provider worker."""

    def __init__(
        self,
        *,
        store: Store,
        providers: NoteProviderRegistry,
        max_workers: int = 1,
    ) -> None:
        if max_workers != 1:
            raise NoteWorkspaceError("Note IR v1 requires exactly one provider worker")
        self.store = store
        self.providers = providers
        self.root = (store.root / "note-ir").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "note_ir.sqlite3"
        self._init_db()
        self._recover_incomplete_jobs()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="yue2-note-ir")
        self._futures: dict[str, Future[None]] = {}
        self._future_lock = threading.RLock()
        self._ir_lock = threading.RLock()
        self._closed = False

    @classmethod
    def from_runtime(cls, *, store: Store, command_timeout_seconds: int) -> "NoteWorkspace":
        registry = NoteProviderRegistry.from_env(default_timeout_seconds=command_timeout_seconds)
        return cls(store=store, providers=registry)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS note_jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    source_artifact_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_note_jobs_project_created
                    ON note_jobs(project_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS music_irs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    source_artifact_id TEXT,
                    title TEXT NOT NULL,
                    current_revision INTEGER NOT NULL,
                    note_count INTEGER NOT NULL,
                    review_note_count INTEGER NOT NULL,
                    current_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_music_irs_project_updated
                    ON music_irs(project_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS note_revisions (
                    id TEXT PRIMARY KEY,
                    music_ir_id TEXT NOT NULL REFERENCES music_irs(id) ON DELETE CASCADE,
                    revision INTEGER NOT NULL,
                    operation_json TEXT NOT NULL,
                    snapshot_path TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    UNIQUE(music_ir_id, revision)
                );
                """
            )

    def _recover_incomplete_jobs(self) -> None:
        now = utc_now()
        message = "Interrupted by process restart before Note IR analysis completed"
        result = {"status": "failed", "type": "InterruptedJob", "error": message}
        with self._connect() as db:
            db.execute(
                """
                UPDATE note_jobs
                SET status = 'failed', result_json = ?, error = ?, finished_at = ?
                WHERE status IN ('queued', 'running')
                """,
                (json.dumps(result, sort_keys=True), message, _iso(now)),
            )

    def close(self) -> None:
        with self._future_lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=True, cancel_futures=False)

    def provider_infos(self) -> list[dict[str, Any]]:
        return [info.model_dump(mode="json") for info in self.providers.infos()]

    def _validate_source_artifact(self, project_id: str, artifact_id: str) -> Path:
        self.store.get_project(project_id)
        artifact = self.store.get_artifact(artifact_id)
        if artifact.project_id != project_id:
            raise NoteWorkspaceError("source artifact does not belong to project")
        if artifact.kind != "audio":
            raise NoteWorkspaceError("Note IR audio analysis requires an audio artifact")
        return self.store.get_artifact_path(artifact_id)

    def _project_note_dir(self, project_id: str) -> Path:
        self.store.get_project(project_id)
        path = (self.store.root / "projects" / project_id / "note-ir").resolve()
        expected_parent = (self.store.root / "projects" / project_id).resolve()
        if expected_parent not in path.parents:
            raise NoteWorkspaceError("Note IR path escaped project storage")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def import_transcription(self, request: NoteImportRequest) -> MusicIR:
        self.store.get_project(request.project_id)
        if request.source_artifact_id:
            self._validate_source_artifact(request.project_id, request.source_artifact_id)
        result = TranscriptionResult(
            provider_id=request.provider_id,
            provider_version=request.provider_version,
            tier=request.provider_tier,
            mode="import",
            tracks=request.tracks,
            warnings=request.warnings,
            metadata=request.metadata,
        )
        ir = fuse_transcriptions(
            project_id=request.project_id,
            source_artifact_id=request.source_artifact_id,
            title=request.title,
            results=[result],
            tempo_bpm=request.tempo_bpm,
            time_signature=request.time_signature,
        )
        self._persist_new_ir(
            ir,
            operation={
                "type": "import",
                "provider_id": request.provider_id,
                "note_count": result.note_count,
            },
        )
        return ir

    def submit_analysis(self, request: NoteAnalysisRequest) -> NoteJobRecord:
        self._validate_source_artifact(request.project_id, request.source_artifact_id)
        provider_ids = request.provider_ids or self.providers.ready_free_provider_ids()
        if not provider_ids:
            raise NoteWorkspaceError(
                "No automatic free note provider is ready. Install basic-pitch or configure a free command provider."
            )
        for provider_id in provider_ids:
            info = self.providers.get(provider_id).info()
            if info.mode in {"manual", "import"}:
                raise NoteWorkspaceError(f"provider {provider_id} cannot run audio analysis")
            if not info.ready:
                raise NoteWorkspaceError(info.reason or f"provider {provider_id} is not ready")
        normalized = request.model_copy(update={"provider_ids": provider_ids})
        created = utc_now()
        job_id = uuid.uuid4().hex
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO note_jobs(
                    id, project_id, source_artifact_id, status, request_json, created_at
                ) VALUES (?, ?, ?, 'queued', ?, ?)
                """,
                (
                    job_id,
                    request.project_id,
                    request.source_artifact_id,
                    normalized.model_dump_json(),
                    _iso(created),
                ),
            )
        with self._future_lock:
            if self._closed:
                raise NoteWorkspaceError("Note IR workspace is closed")
            future = self._executor.submit(self._execute_analysis, job_id)
            self._futures[job_id] = future
            future.add_done_callback(lambda _future, current=job_id: self._forget(current))
        return self.get_job(job_id)

    def _forget(self, job_id: str) -> None:
        with self._future_lock:
            self._futures.pop(job_id, None)

    def wait(self, job_id: str, timeout: float | None = None) -> NoteJobRecord:
        with self._future_lock:
            future = self._futures.get(job_id)
        if future is not None:
            future.result(timeout=timeout)
        return self.get_job(job_id)

    def _execute_analysis(self, job_id: str) -> None:
        job = self.get_job(job_id)
        request = NoteAnalysisRequest.model_validate(job.request)
        started = utc_now()
        with self._connect() as db:
            db.execute(
                "UPDATE note_jobs SET status='running', started_at=? WHERE id=?",
                (_iso(started), job_id),
            )
        job_dir = self._project_note_dir(request.project_id) / "jobs" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        results: list[TranscriptionResult] = []
        failures: list[dict[str, str]] = []
        try:
            source_path = self._validate_source_artifact(
                request.project_id, request.source_artifact_id
            )
            for provider_id in request.provider_ids:
                provider_dir = job_dir / provider_id
                try:
                    result = self.providers.get(provider_id).transcribe(
                        source_path=source_path,
                        output_dir=provider_dir,
                        instrument_hint=request.instrument_hint,
                    )
                    results.append(result)
                except Exception as exc:
                    failures.append(
                        {
                            "provider_id": provider_id,
                            "type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
            if not results:
                details = "; ".join(
                    f"{failure['provider_id']}: {failure['error']}" for failure in failures
                )
                raise NoteWorkspaceError(f"all note providers failed: {details}")
            source_artifact = self.store.get_artifact(request.source_artifact_id)
            ir = fuse_transcriptions(
                project_id=request.project_id,
                source_artifact_id=request.source_artifact_id,
                title=request.title or f"{Path(source_artifact.name).stem} Note IR",
                results=results,
                tempo_bpm=request.tempo_bpm,
                time_signature=request.time_signature,
                minimum_review_confidence=request.minimum_review_confidence,
            )
            self._persist_new_ir(
                ir,
                operation={
                    "type": "audio-analysis",
                    "job_id": job_id,
                    "provider_ids": request.provider_ids,
                    "provider_failures": failures,
                },
            )
            result_payload: dict[str, Any] = {
                "status": "complete",
                "music_ir_id": ir.music_ir_id,
                "stats": ir.stats(),
                "provider_receipts": [
                    receipt.model_dump(mode="json") for receipt in ir.providers
                ],
                "provider_failures": failures,
                "limitations": ir.limitations,
            }
            _atomic_write_text(
                job_dir / "job-receipt.json",
                json.dumps(result_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )
            finished = utc_now()
            with self._connect() as db:
                db.execute(
                    """
                    UPDATE note_jobs
                    SET status='succeeded', result_json=?, finished_at=?
                    WHERE id=?
                    """,
                    (
                        json.dumps(result_payload, ensure_ascii=False, sort_keys=True),
                        _iso(finished),
                        job_id,
                    ),
                )
        except Exception as exc:
            finished = utc_now()
            failure = {
                "status": "failed",
                "type": type(exc).__name__,
                "error": str(exc),
                "provider_failures": failures,
            }
            _atomic_write_text(
                job_dir / "job-failure.json",
                json.dumps(failure, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )
            with self._connect() as db:
                db.execute(
                    """
                    UPDATE note_jobs
                    SET status='failed', result_json=?, error=?, finished_at=?
                    WHERE id=?
                    """,
                    (
                        json.dumps(failure, ensure_ascii=False, sort_keys=True),
                        f"{type(exc).__name__}: {exc}",
                        _iso(finished),
                        job_id,
                    ),
                )

    def _job_from_row(self, row: sqlite3.Row) -> NoteJobRecord:
        return NoteJobRecord(
            id=row["id"],
            project_id=row["project_id"],
            source_artifact_id=row["source_artifact_id"],
            status=row["status"],
            request=json.loads(row["request_json"]),
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            error=row["error"],
            created_at=_parse_dt(row["created_at"]),
            started_at=_parse_dt(row["started_at"]),
            finished_at=_parse_dt(row["finished_at"]),
        )

    def get_job(self, job_id: str) -> NoteJobRecord:
        with self._connect() as db:
            row = db.execute("SELECT * FROM note_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise NotFound("note analysis job not found")
        return self._job_from_row(row)

    def list_jobs(self, project_id: str, limit: int = 100) -> list[NoteJobRecord]:
        self.store.get_project(project_id)
        limit = max(1, min(limit, 500))
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM note_jobs WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        return [self._job_from_row(row) for row in rows]

    def _ir_dir(self, ir: MusicIR) -> Path:
        return self._project_note_dir(ir.project_id) / "music-irs" / ir.music_ir_id

    def _persist_new_ir(self, ir: MusicIR, *, operation: dict[str, Any]) -> None:
        ir_dir = self._ir_dir(ir)
        revision_path = ir_dir / "revisions" / f"{ir.revision:06d}.json"
        current_path = ir_dir / "current.json"
        text = ir.model_dump_json(indent=2) + "\n"
        _atomic_write_text(revision_path, text)
        _atomic_write_text(current_path, text)
        stats = ir.stats()
        revision_id = uuid.uuid4().hex
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO music_irs(
                    id, project_id, source_artifact_id, title, current_revision,
                    note_count, review_note_count, current_path, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ir.music_ir_id,
                    ir.project_id,
                    ir.source_artifact_id,
                    ir.title,
                    ir.revision,
                    stats["note_count"],
                    stats["review_note_count"],
                    current_path.relative_to(self.store.root).as_posix(),
                    _iso(ir.created_at),
                    _iso(ir.updated_at),
                ),
            )
            db.execute(
                """
                INSERT INTO note_revisions(
                    id, music_ir_id, revision, operation_json, snapshot_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    ir.music_ir_id,
                    ir.revision,
                    json.dumps(operation, ensure_ascii=False, sort_keys=True),
                    revision_path.relative_to(self.store.root).as_posix(),
                    _iso(ir.updated_at),
                ),
            )

    def _persist_revision(self, ir: MusicIR, *, operation: dict[str, Any]) -> None:
        ir_dir = self._ir_dir(ir)
        revision_path = ir_dir / "revisions" / f"{ir.revision:06d}.json"
        current_path = ir_dir / "current.json"
        with self._connect() as db:
            current = db.execute(
                "SELECT current_revision FROM music_irs WHERE id=?", (ir.music_ir_id,)
            ).fetchone()
        if current is None:
            raise NotFound("Music IR not found")
        if int(current["current_revision"]) != ir.revision - 1:
            raise NoteWorkspaceError("Music IR revision conflict; reload and retry")
        text = ir.model_dump_json(indent=2) + "\n"
        _atomic_write_text(revision_path, text)
        _atomic_write_text(current_path, text)
        stats = ir.stats()
        revision_id = uuid.uuid4().hex
        with self._connect() as db:
            db.execute(
                """
                UPDATE music_irs
                SET title=?, current_revision=?, note_count=?, review_note_count=?,
                    current_path=?, updated_at=?
                WHERE id=?
                """,
                (
                    ir.title,
                    ir.revision,
                    stats["note_count"],
                    stats["review_note_count"],
                    current_path.relative_to(self.store.root).as_posix(),
                    _iso(ir.updated_at),
                    ir.music_ir_id,
                ),
            )
            db.execute(
                """
                INSERT INTO note_revisions(
                    id, music_ir_id, revision, operation_json, snapshot_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    revision_id,
                    ir.music_ir_id,
                    ir.revision,
                    json.dumps(operation, ensure_ascii=False, sort_keys=True),
                    revision_path.relative_to(self.store.root).as_posix(),
                    _iso(ir.updated_at),
                ),
            )

    def _summary_from_row(self, row: sqlite3.Row) -> MusicIRSummary:
        return MusicIRSummary(
            music_ir_id=row["id"],
            project_id=row["project_id"],
            source_artifact_id=row["source_artifact_id"],
            title=row["title"],
            current_revision=row["current_revision"],
            note_count=row["note_count"],
            review_note_count=row["review_note_count"],
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    def list_irs(self, project_id: str) -> list[MusicIRSummary]:
        self.store.get_project(project_id)
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM music_irs WHERE project_id=? ORDER BY updated_at DESC",
                (project_id,),
            ).fetchall()
        return [self._summary_from_row(row) for row in rows]

    def _ir_row(self, music_ir_id: str) -> sqlite3.Row:
        with self._connect() as db:
            row = db.execute("SELECT * FROM music_irs WHERE id=?", (music_ir_id,)).fetchone()
        if row is None:
            raise NotFound("Music IR not found")
        return row

    def get_ir(self, music_ir_id: str) -> MusicIR:
        row = self._ir_row(music_ir_id)
        path = (self.store.root / row["current_path"]).resolve()
        if self.store.root not in path.parents or not path.is_file():
            raise NoteWorkspaceError("Music IR snapshot is missing or outside storage")
        try:
            return MusicIR.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise NoteWorkspaceError("Music IR snapshot is invalid") from exc

    def current_json_path(self, music_ir_id: str) -> Path:
        row = self._ir_row(music_ir_id)
        path = (self.store.root / row["current_path"]).resolve()
        if self.store.root not in path.parents or not path.is_file():
            raise NoteWorkspaceError("Music IR snapshot is missing")
        return path

    def patch_note(
        self, music_ir_id: str, note_id: str, patch: NotePatchRequest
    ) -> tuple[MusicIR, NoteEditReceipt]:
        with self._ir_lock:
            current = self.get_ir(music_ir_id)
            try:
                updated, receipt = apply_note_patch(current, note_id, patch)
            except KeyError as exc:
                raise NotFound(str(exc)) from exc
            except ValueError as exc:
                raise NoteWorkspaceError(str(exc)) from exc
            self._persist_revision(
                updated,
                operation={
                    "type": "note-patch",
                    "receipt": receipt.model_dump(mode="json"),
                },
            )
            return updated, receipt

    def restore_revision(
        self, music_ir_id: str, request: RestoreRevisionRequest
    ) -> MusicIR:
        with self._ir_lock:
            current = self.get_ir(music_ir_id)
            with self._connect() as db:
                row = db.execute(
                    "SELECT snapshot_path FROM note_revisions WHERE music_ir_id=? AND revision=?",
                    (music_ir_id, request.revision),
                ).fetchone()
            if row is None:
                raise NotFound("Music IR revision not found")
            source = (self.store.root / row["snapshot_path"]).resolve()
            if self.store.root not in source.parents or not source.is_file():
                raise NoteWorkspaceError("revision snapshot is missing")
            restored = MusicIR.model_validate_json(source.read_text(encoding="utf-8"))
            restored.revision = current.revision + 1
            restored.updated_at = utc_now()
            self._persist_revision(
                restored,
                operation={
                    "type": "restore",
                    "restored_revision": request.revision,
                    "reason": request.reason,
                },
            )
            return restored

    def list_revisions(self, music_ir_id: str) -> list[RevisionSummary]:
        self._ir_row(music_ir_id)
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM note_revisions WHERE music_ir_id=? ORDER BY revision DESC",
                (music_ir_id,),
            ).fetchall()
        return [
            RevisionSummary(
                revision_id=row["id"],
                music_ir_id=row["music_ir_id"],
                revision=row["revision"],
                operation=json.loads(row["operation_json"]),
                snapshot_path=row["snapshot_path"],
                created_at=_parse_dt(row["created_at"]),
            )
            for row in rows
        ]

    def review_notes(self, music_ir_id: str, *, threshold: float = 0.82) -> list[dict[str, Any]]:
        return review_queue(self.get_ir(music_ir_id), threshold=threshold)

    def midi_path(self, music_ir_id: str) -> Path:
        ir = self.get_ir(music_ir_id)
        path = self._ir_dir(ir) / "exports" / f"revision-{ir.revision:06d}.mid"
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            data = music_ir_to_midi_bytes(ir)
            fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, path)
            except Exception:
                Path(temp_name).unlink(missing_ok=True)
                raise
        return path
