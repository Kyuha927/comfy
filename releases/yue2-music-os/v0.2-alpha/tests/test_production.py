from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from yue2_music_os.api import create_app
from yue2_music_os.config import RenderProviderConfig
from yue2_music_os.models import (
    GenerateRequest,
    JobStatus,
    ProductionRenderRequest,
    RankCandidatesRequest,
)
from yue2_music_os.production import ProductionError, rank_generation_candidates
from yue2_music_os.sample_data import SAMPLE_LYRICS, SAMPLE_STYLE
from yue2_music_os.service import MusicService
from yue2_music_os.storage import Store


def generate_candidates(service: MusicService, project_id: str, count: int = 2):
    job = service.submit_generate(
        GenerateRequest(
            project_id=project_id,
            style=SAMPLE_STYLE,
            lyrics=SAMPLE_LYRICS,
            candidate_count=count,
        )
    )
    done = service.wait(job.id, timeout=10)
    assert done.status == JobStatus.SUCCEEDED
    return done


def test_rank_and_manual_production_package_are_auditable(settings) -> None:
    store = Store(settings.data_dir)
    project = store.create_project("Production")
    service = MusicService(settings, store=store, enforce_single_instance=False)
    try:
        source = generate_candidates(service, project.id, count=2)
        rank_job = service.submit_rank_candidates(
            RankCandidatesRequest(
                project_id=project.id,
                generation_job_id=source.id,
            )
        )
        ranked = service.wait(rank_job.id, timeout=10)
        assert ranked.status == JobStatus.SUCCEEDED
        assert ranked.result["recommended_candidate"] == 1
        assert ranked.result["scope"] == "technical-readiness-only"
        assert ranked.result["quality_claim"] is False
        assert all(
            "technical_score" in item for item in ranked.result["ranking"]
        )

        production = service.submit_production_render(
            ProductionRenderRequest(
                project_id=project.id,
                generation_job_id=source.id,
                provider_ids=["flow-lyria-manual"],
                title="LIN ASTER Theme",
                commercial_intent=True,
                license_review_acknowledged=True,
            )
        )
        completed = service.wait(production.id, timeout=10)
        assert completed.status == JobStatus.SUCCEEDED
        assert completed.result["selected_candidate"] == 1
        assert completed.result["source_audio_in_provider_packages"] is False
        assert completed.result["review_required"] is True

        job_dir = store.job_dir(project.id, production.id)
        provider = job_dir / "production/providers/flow-lyria-manual"
        assert (provider / "render-request.json").is_file()
        assert (provider / "style.txt").is_file()
        assert (provider / "lyrics.txt").is_file()
        assert (provider / "score.abc").is_file()
        assert not any(path.suffix == ".wav" for path in provider.rglob("*"))
        assert (job_dir / "production/audit/selected-yue2-audio.wav").is_file()
        request = json.loads((provider / "render-request.json").read_text())
        assert request["composition"]["source_audio_included"] is False
        assert "Do not copy" in request["instruction"]
    finally:
        service.close()


def test_mock_renderer_is_noncommercial_and_creates_test_audio(settings) -> None:
    store = Store(settings.data_dir)
    project = store.create_project("Mock production")
    service = MusicService(settings, store=store, enforce_single_instance=False)
    try:
        source = generate_candidates(service, project.id, count=1)
        production = service.submit_production_render(
            ProductionRenderRequest(
                project_id=project.id,
                generation_job_id=source.id,
                provider_ids=["mock-renderer"],
                title="Mock only",
                commercial_intent=False,
            )
        )
        completed = service.wait(production.id, timeout=10)
        assert completed.status == JobStatus.SUCCEEDED
        artifacts = store.list_artifacts(project.id)
        assert any(
            artifact.job_id == production.id
            and artifact.kind == "audio"
            and "final-render.wav" in artifact.name
            for artifact in artifacts
        )
    finally:
        service.close()


def test_mock_renderer_rejects_commercial_intent(settings) -> None:
    store = Store(settings.data_dir)
    project = store.create_project("Blocked mock")
    service = MusicService(settings, store=store, enforce_single_instance=False)
    try:
        source = generate_candidates(service, project.id, count=1)
        production = service.submit_production_render(
            ProductionRenderRequest(
                project_id=project.id,
                generation_job_id=source.id,
                provider_ids=["mock-renderer"],
                title="Must block",
                commercial_intent=True,
                license_review_acknowledged=True,
            )
        )
        completed = service.wait(production.id, timeout=10)
        assert completed.status == JobStatus.FAILED
        assert "cannot be used for commercial" in (completed.error or "")
    finally:
        service.close()


def test_registered_command_provider_runs_without_shell(settings, tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text(
        """import json
import pathlib
import sys
request_path = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
request = json.loads(request_path.read_text())
assert request['composition']['source_audio_included'] is False
output.mkdir(parents=True, exist_ok=True)
(output / 'commercial-render.wav').write_bytes(b'RIFF-command-render')
(output / 'render-result.json').write_text(json.dumps({'status': 'complete', 'outputs': ['commercial-render.wav']}))
""",
        encoding="utf-8",
    )
    provider = RenderProviderConfig(
        provider_id="lyria-bridge",
        label="Operator Lyria bridge",
        mode="command",
        argv=(
            str(Path(sys.executable).resolve()),
            str(adapter.resolve()),
            "{request_json}",
            "{output_dir}",
        ),
        timeout_seconds=10,
        terms_reference="internal-contract-001",
        commercial_status="operator-verified",
    )
    command_settings = replace(settings, render_providers=(provider,))
    command_settings.validate()
    store = Store(command_settings.data_dir)
    project = store.create_project("Command provider")
    service = MusicService(
        command_settings, store=store, enforce_single_instance=False
    )
    try:
        source = generate_candidates(service, project.id, count=1)
        production = service.submit_production_render(
            ProductionRenderRequest(
                project_id=project.id,
                generation_job_id=source.id,
                provider_ids=["lyria-bridge"],
                title="Command bridge",
                commercial_intent=True,
                license_review_acknowledged=True,
            )
        )
        completed = service.wait(production.id, timeout=10)
        assert completed.status == JobStatus.SUCCEEDED
        receipt = completed.result["provider_receipts"][0]
        assert receipt["status"] == "complete"
        assert receipt["live_execution"] is True
        assert receipt["outputs"] == ["output/commercial-render.wav"]
        command_record = (
            store.job_dir(project.id, production.id)
            / "production/providers/lyria-bridge/provider-command.command.json"
        )
        assert command_record.is_file()
        assert json.loads(command_record.read_text())["argv"][0] == str(
            Path(sys.executable).resolve()
        )
    finally:
        service.close()


def test_ranker_rejects_candidate_without_audio(settings) -> None:
    store = Store(settings.data_dir)
    project = store.create_project("Broken candidate")
    service = MusicService(settings, store=store, enforce_single_instance=False)
    try:
        source = generate_candidates(service, project.id, count=1)
        source_dir = store.job_dir(project.id, source.id)
        (source_dir / "output/candidate-01/audio.wav").unlink()
        with pytest.raises(ProductionError, match="no generation candidate"):
            rank_generation_candidates(source_dir, source.request, source.result)
    finally:
        service.close()


def test_production_api_contract(settings) -> None:
    with TestClient(create_app(settings)) as client:
        providers = client.get("/api/render-providers")
        assert providers.status_code == 200
        assert any(item["id"] == "flow-lyria-manual" for item in providers.json())
        project_id = client.post(
            "/api/projects", json={"name": "Production API"}
        ).json()["id"]
        generated = client.post(
            "/api/jobs/generate",
            json={
                "project_id": project_id,
                "style": SAMPLE_STYLE,
                "lyrics": SAMPLE_LYRICS,
                "candidate_count": 1,
            },
        ).json()
        source = service_wait(client, generated["id"])
        ranked = client.post(
            "/api/jobs/rank-candidates",
            json={"project_id": project_id, "generation_job_id": source["id"]},
        )
        assert ranked.status_code == 202
        assert service_wait(client, ranked.json()["id"])["status"] == "succeeded"
        rejected = client.post(
            "/api/jobs/production-render",
            json={
                "project_id": project_id,
                "generation_job_id": source["id"],
                "provider_ids": ["flow-lyria-manual"],
                "commercial_intent": True,
                "license_review_acknowledged": False,
            },
        )
        assert rejected.status_code == 422
        accepted = client.post(
            "/api/jobs/production-render",
            json={
                "project_id": project_id,
                "generation_job_id": source["id"],
                "provider_ids": ["flow-lyria-manual"],
                "commercial_intent": True,
                "license_review_acknowledged": True,
            },
        )
        assert accepted.status_code == 202
        assert service_wait(client, accepted.json()["id"])["status"] == "succeeded"


def service_wait(client: TestClient, job_id: str) -> dict:
    import time

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in {"succeeded", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError("job timed out")
