from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .abc_tools import AbcError
from .config import Settings
from .engines import EngineError
from .models import (
    CompareRequest,
    GenerateRequest,
    ProductionRenderRequest,
    ProjectCreate,
    RankCandidatesRequest,
    StripChordsRequest,
    TranscribeRequest,
)
from .note_ir import NotePatchRequest
from .note_providers import NoteProviderError
from .note_workspace import (
    NoteAnalysisRequest,
    NoteImportRequest,
    NoteWorkspace,
    NoteWorkspaceError,
    RestoreRevisionRequest,
)
from .production import ProductionError
from .service import MusicService, ServiceError
from .storage import InvalidUpload, NotFound, Store, StoreError


PUBLIC_API_PATHS = {"/api/health", "/api/policy"}


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()
    store = Store(active_settings.data_dir)
    service = MusicService(active_settings, store=store)
    note_workspace = NoteWorkspace.from_runtime(
        store=store,
        command_timeout_seconds=active_settings.command_timeout_seconds,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        note_workspace.close()
        service.close()

    app = FastAPI(
        title="YuE2 Music OS",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.store = store
    app.state.service = service
    app.state.note_workspace = note_workspace
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(active_settings.allowed_hosts),
    )

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        token = active_settings.api_token
        if (
            token
            and request.url.path.startswith("/api/")
            and request.url.path not in PUBLIC_API_PATHS
        ):
            supplied = request.headers.get("X-Music-OS-Token", "")
            if not hmac.compare_digest(supplied, token):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "missing or invalid X-Music-OS-Token"},
                    headers={
                        "WWW-Authenticate": "MusicOSToken",
                        "X-Content-Type-Options": "nosniff",
                        "Referrer-Policy": "no-referrer",
                        "X-Frame-Options": "DENY",
                        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
                    },
                )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
        )
        return response

    @app.exception_handler(NotFound)
    async def not_found_handler(_request: Request, exc: NotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidUpload)
    async def invalid_upload_handler(_request: Request, exc: InvalidUpload):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    async def domain_error_handler(_request: Request, exc: Exception):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    for exception_type in (
        StoreError,
        ServiceError,
        EngineError,
        ProductionError,
        AbcError,
        NoteWorkspaceError,
        NoteProviderError,
    ):
        app.add_exception_handler(exception_type, domain_error_handler)

    @app.get("/api/health")
    def health() -> dict[str, object]:
        providers = note_workspace.provider_infos()
        return {
            "status": "ok",
            "version": __version__,
            "doctor": service.doctor(),
            "note_ir": {
                "status": "ready",
                "provider_count": len(providers),
                "ready_provider_ids": [
                    provider["provider_id"]
                    for provider in providers
                    if provider["ready"]
                ],
                "symbolic_note_edit": True,
                "original_audio_mutation": False,
            },
        }

    @app.get("/api/policy")
    def policy() -> dict[str, object]:
        payload = active_settings.public_policy()
        payload["note_ir"] = {
            "immutable_source_audio": True,
            "revisioned_note_edits": True,
            "paid_provider_slots": True,
            "direct_polyphonic_single_note_audio_edit": False,
        }
        return payload

    @app.post("/api/projects", status_code=201)
    def create_project(request: ProjectCreate):
        return store.create_project(request.name)

    @app.get("/api/projects")
    def list_projects():
        return store.list_projects()

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str):
        return store.get_project(project_id)

    @app.get("/api/projects/{project_id}/jobs")
    def list_jobs(project_id: str, limit: int = Query(default=100, ge=1, le=500)):
        store.get_project(project_id)
        return store.list_jobs(project_id, limit=limit)

    @app.get("/api/projects/{project_id}/artifacts")
    def list_artifacts(
        project_id: str, limit: int = Query(default=500, ge=1, le=1000)
    ):
        return store.list_artifacts(project_id, limit=limit)

    @app.post("/api/projects/{project_id}/uploads", status_code=201)
    def upload(project_id: str, file: UploadFile = File(...)):
        if not file.filename:
            raise HTTPException(status_code=400, detail="upload filename is required")
        try:
            return store.save_upload(
                project_id,
                file.filename,
                file.file,
                active_settings.max_upload_bytes,
                file.content_type,
            )
        finally:
            file.file.close()

    @app.post("/api/jobs/generate", status_code=202)
    def generate(request: GenerateRequest):
        return service.submit_generate(request)

    @app.post("/api/jobs/transcribe", status_code=202)
    def transcribe(request: TranscribeRequest):
        return service.submit_transcribe(request)

    @app.post("/api/jobs/compare", status_code=202)
    def compare_scores(request: CompareRequest):
        return service.submit_compare(request)

    @app.post("/api/jobs/strip-chords", status_code=202)
    def strip_score_chords(request: StripChordsRequest):
        return service.submit_strip_chords(request)

    @app.get("/api/render-providers")
    def render_providers():
        return service.list_render_providers()

    @app.post("/api/jobs/rank-candidates", status_code=202)
    def rank_candidates(request: RankCandidatesRequest):
        return service.submit_rank_candidates(request)

    @app.post("/api/jobs/production-render", status_code=202)
    def production_render(request: ProductionRenderRequest):
        return service.submit_production_render(request)

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        return store.get_job(job_id)

    @app.get("/api/artifacts/{artifact_id}")
    def get_artifact(artifact_id: str):
        return store.get_artifact(artifact_id)

    @app.get("/api/artifacts/{artifact_id}/download")
    def download_artifact(artifact_id: str):
        artifact = store.get_artifact(artifact_id)
        path = store.get_artifact_path(artifact_id)
        return FileResponse(path, media_type=artifact.media_type, filename=artifact.name)

    # Note IR is deliberately separated from score generation. It can use free
    # local engines first and later swap in licensed command adapters without
    # changing the editor or the on-disk schema.
    @app.get("/api/note-providers")
    def note_providers():
        return note_workspace.provider_infos()

    @app.post("/api/note-ir/import", status_code=201)
    def import_note_ir(request: NoteImportRequest):
        return note_workspace.import_transcription(request).public_dict()

    @app.post("/api/note-jobs/analyze", status_code=202)
    def analyze_notes(request: NoteAnalysisRequest):
        return note_workspace.submit_analysis(request)

    @app.get("/api/note-jobs/{job_id}")
    def get_note_job(job_id: str):
        return note_workspace.get_job(job_id)

    @app.get("/api/projects/{project_id}/note-jobs")
    def list_note_jobs(
        project_id: str, limit: int = Query(default=100, ge=1, le=500)
    ):
        return note_workspace.list_jobs(project_id, limit=limit)

    @app.get("/api/projects/{project_id}/note-irs")
    def list_note_irs(project_id: str):
        return note_workspace.list_irs(project_id)

    @app.get("/api/note-ir/{music_ir_id}")
    def get_note_ir(music_ir_id: str):
        return note_workspace.get_ir(music_ir_id).public_dict()

    @app.get("/api/note-ir/{music_ir_id}/review")
    def get_note_review_queue(
        music_ir_id: str, threshold: float = Query(default=0.82, ge=0.0, le=1.0)
    ):
        return note_workspace.review_notes(music_ir_id, threshold=threshold)

    @app.patch("/api/note-ir/{music_ir_id}/notes/{note_id}")
    def patch_note(music_ir_id: str, note_id: str, request: NotePatchRequest):
        ir, receipt = note_workspace.patch_note(music_ir_id, note_id, request)
        return {
            "music_ir": ir.public_dict(),
            "receipt": receipt.model_dump(mode="json"),
        }

    @app.post("/api/note-ir/{music_ir_id}/restore")
    def restore_note_ir(music_ir_id: str, request: RestoreRevisionRequest):
        return note_workspace.restore_revision(music_ir_id, request).public_dict()

    @app.get("/api/note-ir/{music_ir_id}/revisions")
    def list_note_revisions(music_ir_id: str):
        return note_workspace.list_revisions(music_ir_id)

    @app.get("/api/note-ir/{music_ir_id}/export.json")
    def export_note_ir_json(music_ir_id: str):
        ir = note_workspace.get_ir(music_ir_id)
        path = note_workspace.current_json_path(music_ir_id)
        return FileResponse(
            path,
            media_type="application/json",
            filename=f"music-ir-{music_ir_id}-r{ir.revision}.json",
        )

    @app.get("/api/note-ir/{music_ir_id}/export.mid")
    def export_note_ir_midi(music_ir_id: str):
        ir = note_workspace.get_ir(music_ir_id)
        path = note_workspace.midi_path(music_ir_id)
        return FileResponse(
            path,
            media_type="audio/midi",
            filename=f"music-ir-{music_ir_id}-r{ir.revision}.mid",
        )

    static_dir = Path(__file__).parent / "static"
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app
