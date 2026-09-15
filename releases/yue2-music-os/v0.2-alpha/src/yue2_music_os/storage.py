from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Iterator

from .models import ArtifactRecord, JobKind, JobRecord, JobStatus, ProjectRecord


SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
UPLOAD_EXTENSIONS = {
    ".abc",
    ".flac",
    ".m4a",
    ".mid",
    ".midi",
    ".mp3",
    ".ogg",
    ".txt",
    ".wav",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def safe_filename(name: str) -> str:
    # Treat both POSIX and Windows separators as untrusted path syntax.
    leaf = Path(name.replace("\\", "/")).name.strip()
    suffix = Path(leaf).suffix
    stem = leaf[: -len(suffix)] if suffix else leaf
    normalized_stem = SAFE_NAME.sub("-", stem).strip(".-") or "artifact"
    normalized_suffix = SAFE_NAME.sub("", suffix).lower()
    if normalized_suffix and not normalized_suffix.startswith("."):
        normalized_suffix = "." + normalized_suffix
    budget = max(1, 180 - len(normalized_suffix))
    return normalized_stem[:budget] + normalized_suffix


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class StoreError(RuntimeError):
    pass


class NotFound(StoreError):
    pass


class InvalidUpload(StoreError):
    pass


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "projects").mkdir(exist_ok=True)
        self.db_path = self.root / "music_os.sqlite3"
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
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
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_project_created
                    ON jobs(project_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
                    kind TEXT NOT NULL,
                    name TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    rel_path TEXT NOT NULL UNIQUE,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_artifacts_project_created
                    ON artifacts(project_id, created_at DESC);
                """
            )

    def recover_incomplete_jobs(self) -> int:
        """Mark jobs left queued/running by a terminated service as failed."""
        finished = utc_now()
        error = "Interrupted by service restart before a terminal receipt was recorded"
        result = {
            "status": "failed",
            "type": "InterruptedJob",
            "error": error,
            "recovered_at": _iso(finished),
        }
        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE jobs
                SET status = ?, result_json = ?, error = ?, finished_at = ?
                WHERE status IN (?, ?)
                """,
                (
                    JobStatus.FAILED.value,
                    json.dumps(result, ensure_ascii=False, sort_keys=True),
                    error,
                    _iso(finished),
                    JobStatus.QUEUED.value,
                    JobStatus.RUNNING.value,
                ),
            )
            return cursor.rowcount

    def _project_path(self, project_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", project_id):
            raise NotFound("project not found")
        path = (self.root / "projects" / project_id).resolve()
        if self.root not in path.parents:
            raise StoreError("project path escaped storage root")
        return path

    def create_project(self, name: str) -> ProjectRecord:
        project_id = uuid.uuid4().hex
        created = utc_now()
        path = self._project_path(project_id)
        (path / "uploads").mkdir(parents=True)
        (path / "jobs").mkdir(parents=True)
        with self._connect() as db:
            db.execute(
                "INSERT INTO projects(id, name, created_at) VALUES (?, ?, ?)",
                (project_id, name, _iso(created)),
            )
        return ProjectRecord(id=project_id, name=name, created_at=created)

    def get_project(self, project_id: str) -> ProjectRecord:
        with self._connect() as db:
            row = db.execute(
                "SELECT id, name, created_at FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            raise NotFound("project not found")
        return ProjectRecord(
            id=row["id"], name=row["name"], created_at=_parse_dt(row["created_at"])
        )

    def list_projects(self) -> list[ProjectRecord]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, name, created_at FROM projects ORDER BY created_at DESC"
            ).fetchall()
        return [
            ProjectRecord(
                id=row["id"], name=row["name"], created_at=_parse_dt(row["created_at"])
            )
            for row in rows
        ]

    def save_upload(
        self,
        project_id: str,
        filename: str,
        stream: BinaryIO,
        max_bytes: int,
        media_type: str | None = None,
    ) -> ArtifactRecord:
        self.get_project(project_id)
        clean_name = safe_filename(filename)
        suffix = Path(clean_name).suffix.lower()
        if suffix not in UPLOAD_EXTENSIONS:
            raise InvalidUpload(
                f"unsupported upload type {suffix or '<none>'}; allowed: {', '.join(sorted(UPLOAD_EXTENSIONS))}"
            )
        artifact_id = uuid.uuid4().hex
        destination = self._project_path(project_id) / "uploads" / f"{artifact_id}-{clean_name}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        digest = hashlib.sha256()
        fd, temp_name = tempfile.mkstemp(prefix="upload-", dir=destination.parent)
        try:
            with os.fdopen(fd, "wb") as output:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        raise InvalidUpload(f"upload exceeds {max_bytes} bytes")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if written == 0:
                raise InvalidUpload("empty upload")
            os.replace(temp_name, destination)
        except Exception:
            Path(temp_name).unlink(missing_ok=True)
            raise
        kind = self._kind_for_path(destination)
        return self._insert_artifact(
            artifact_id=artifact_id,
            project_id=project_id,
            job_id=None,
            kind=kind,
            name=clean_name,
            # Do not trust the client-supplied Content-Type. The accepted
            # extension list is server-owned, so MIME is derived from it too.
            media_type=mimetypes.guess_type(clean_name)[0] or "application/octet-stream",
            path=destination,
            sha256=digest.hexdigest(),
            size_bytes=written,
        )

    def job_dir(self, project_id: str, job_id: str) -> Path:
        self.get_project(project_id)
        if not re.fullmatch(r"[0-9a-f]{32}", job_id):
            raise StoreError("invalid job id")
        path = (self._project_path(project_id) / "jobs" / job_id).resolve()
        project_path = self._project_path(project_id)
        if project_path not in path.parents:
            raise StoreError("job path escaped project root")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def create_job(
        self, project_id: str, kind: JobKind, request: dict[str, object]
    ) -> JobRecord:
        self.get_project(project_id)
        job_id = uuid.uuid4().hex
        created = utc_now()
        record = JobRecord(
            id=job_id,
            project_id=project_id,
            kind=kind,
            status=JobStatus.QUEUED,
            request=request,
            created_at=created,
        )
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO jobs(
                    id, project_id, kind, status, request_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.project_id,
                    record.kind.value,
                    record.status.value,
                    json.dumps(request, ensure_ascii=False, sort_keys=True),
                    _iso(record.created_at),
                ),
            )
        return record

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus,
        result: dict[str, object] | None = None,
        error: str | None = None,
    ) -> JobRecord:
        current = self.get_job(job_id)
        started_at = current.started_at
        finished_at = current.finished_at
        now = utc_now()
        if status == JobStatus.RUNNING and started_at is None:
            started_at = now
        if status in {JobStatus.SUCCEEDED, JobStatus.FAILED}:
            finished_at = now
        with self._connect() as db:
            db.execute(
                """
                UPDATE jobs
                SET status = ?, result_json = ?, error = ?, started_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (
                    status.value,
                    json.dumps(result, ensure_ascii=False, sort_keys=True)
                    if result is not None
                    else None,
                    error,
                    _iso(started_at),
                    _iso(finished_at),
                    job_id,
                ),
            )
        return self.get_job(job_id)

    def _job_from_row(self, row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            id=row["id"],
            project_id=row["project_id"],
            kind=JobKind(row["kind"]),
            status=JobStatus(row["status"]),
            request=json.loads(row["request_json"]),
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            error=row["error"],
            created_at=_parse_dt(row["created_at"]),
            started_at=_parse_dt(row["started_at"]),
            finished_at=_parse_dt(row["finished_at"]),
        )

    def get_job(self, job_id: str) -> JobRecord:
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise NotFound("job not found")
        return self._job_from_row(row)

    def list_jobs(self, project_id: str | None = None, limit: int = 100) -> list[JobRecord]:
        limit = max(1, min(limit, 500))
        with self._connect() as db:
            if project_id:
                rows = db.execute(
                    "SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                    (project_id, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        return [self._job_from_row(row) for row in rows]

    def register_generated_file(
        self,
        project_id: str,
        job_id: str,
        path: Path,
        *,
        display_name: str | None = None,
    ) -> ArtifactRecord:
        job = self.get_job(job_id)
        if job.project_id != project_id:
            raise StoreError("job does not belong to project")
        resolved = path.resolve()
        job_root = self.job_dir(project_id, job_id).resolve()
        if resolved != job_root and job_root not in resolved.parents:
            raise StoreError("generated artifact is outside its job directory")
        if not resolved.is_file():
            raise StoreError(f"generated artifact does not exist: {resolved}")
        try:
            rel_path = resolved.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise StoreError("generated artifact escaped storage root") from exc
        with self._connect() as db:
            existing = db.execute(
                "SELECT * FROM artifacts WHERE rel_path = ?", (rel_path,)
            ).fetchone()
        if existing is not None:
            record = self._artifact_from_row(existing)
            if record.project_id != project_id or record.job_id != job_id:
                raise StoreError("generated artifact path is already owned by another job")
            if record.sha256 != sha256_file(resolved) or record.size_bytes != resolved.stat().st_size:
                raise StoreError("generated artifact changed after it was indexed")
            return record
        artifact_id = uuid.uuid4().hex
        name = safe_filename(display_name or resolved.name)
        return self._insert_artifact(
            artifact_id=artifact_id,
            project_id=project_id,
            job_id=job_id,
            kind=self._kind_for_path(resolved),
            name=name,
            media_type=mimetypes.guess_type(name)[0] or "application/octet-stream",
            path=resolved,
            sha256=sha256_file(resolved),
            size_bytes=resolved.stat().st_size,
        )

    def _insert_artifact(
        self,
        *,
        artifact_id: str,
        project_id: str,
        job_id: str | None,
        kind: str,
        name: str,
        media_type: str,
        path: Path,
        sha256: str,
        size_bytes: int,
    ) -> ArtifactRecord:
        created = utc_now()
        try:
            rel_path = path.resolve().relative_to(self.root).as_posix()
        except ValueError as exc:
            raise StoreError("artifact path escaped storage root") from exc
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO artifacts(
                    id, project_id, job_id, kind, name, media_type,
                    rel_path, size_bytes, sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    project_id,
                    job_id,
                    kind,
                    name,
                    media_type,
                    rel_path,
                    size_bytes,
                    sha256,
                    _iso(created),
                ),
            )
        return ArtifactRecord(
            id=artifact_id,
            project_id=project_id,
            job_id=job_id,
            kind=kind,
            name=name,
            media_type=media_type,
            size_bytes=size_bytes,
            sha256=sha256,
            created_at=created,
            download_url=f"/api/artifacts/{artifact_id}/download",
        )

    def _artifact_from_row(self, row: sqlite3.Row) -> ArtifactRecord:
        return ArtifactRecord(
            id=row["id"],
            project_id=row["project_id"],
            job_id=row["job_id"],
            kind=row["kind"],
            name=row["name"],
            media_type=row["media_type"],
            size_bytes=row["size_bytes"],
            sha256=row["sha256"],
            created_at=_parse_dt(row["created_at"]),
            download_url=f"/api/artifacts/{row['id']}/download",
        )

    def get_artifact(self, artifact_id: str) -> ArtifactRecord:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
        if row is None:
            raise NotFound("artifact not found")
        return self._artifact_from_row(row)

    def get_artifact_path(self, artifact_id: str) -> Path:
        with self._connect() as db:
            row = db.execute(
                "SELECT rel_path FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
        if row is None:
            raise NotFound("artifact not found")
        path = (self.root / row["rel_path"]).resolve()
        if self.root not in path.parents:
            raise StoreError("artifact path escaped storage root")
        if not path.is_file():
            raise NotFound("artifact file is missing")
        return path

    def list_artifacts(self, project_id: str, limit: int = 500) -> list[ArtifactRecord]:
        self.get_project(project_id)
        limit = max(1, min(limit, 1000))
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM artifacts WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        return [self._artifact_from_row(row) for row in rows]

    @staticmethod
    def _kind_for_path(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".wav", ".flac", ".mp3", ".ogg", ".m4a"}:
            return "audio"
        if suffix == ".abc":
            return "score"
        if suffix in {".mid", ".midi"}:
            return "midi"
        if suffix == ".json":
            return "metadata"
        if suffix in {".html", ".htm"}:
            return "comparison"
        if suffix in {".log", ".txt"}:
            return "text"
        return "artifact"
