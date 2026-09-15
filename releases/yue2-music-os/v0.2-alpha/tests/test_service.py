from __future__ import annotations

import io
import wave

import pytest

from yue2_music_os.models import (
    CompareRequest,
    GenerateRequest,
    JobStatus,
    StripChordsRequest,
    TranscribeRequest,
)
from yue2_music_os.sample_data import (
    SAMPLE_JAZZ_SCORE,
    SAMPLE_LYRICS,
    SAMPLE_SCORE,
    SAMPLE_STYLE,
)
from yue2_music_os.service import MusicService, ServiceError
from yue2_music_os.storage import Store


def tiny_wav() -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\x00\x00" * 80)
    return stream.getvalue()


def test_end_to_end_mock_jobs(settings) -> None:
    store = Store(settings.data_dir)
    project = store.create_project("Service")
    score = store.save_upload(
        project.id,
        "score.abc",
        io.BytesIO(SAMPLE_SCORE.encode()),
        settings.max_upload_bytes,
    )
    jazz = store.save_upload(
        project.id,
        "score-jazz.abc",
        io.BytesIO(SAMPLE_JAZZ_SCORE.encode()),
        settings.max_upload_bytes,
    )
    audio = store.save_upload(
        project.id,
        "source.wav",
        io.BytesIO(tiny_wav()),
        settings.max_upload_bytes,
    )
    service = MusicService(settings, store=store)
    try:
        generated = service.submit_generate(
            GenerateRequest(
                project_id=project.id,
                style=SAMPLE_STYLE,
                lyrics=SAMPLE_LYRICS,
                cot="full",
                seed=42,
                candidate_count=2,
                abc_artifact_id=score.id,
            )
        )
        assert service.wait(generated.id, timeout=10).status == JobStatus.SUCCEEDED

        compared = service.submit_compare(
            CompareRequest(
                project_id=project.id,
                before_artifact_id=score.id,
                after_artifact_id=jazz.id,
            )
        )
        compared_done = service.wait(compared.id, timeout=10)
        assert compared_done.status == JobStatus.SUCCEEDED
        assert compared_done.result["comparison"]["match"] is True
        assert compared_done.result["comparison"]["harmony_changed"] is True

        stripped = service.submit_strip_chords(
            StripChordsRequest(project_id=project.id, source_artifact_id=score.id)
        )
        assert service.wait(stripped.id, timeout=10).status == JobStatus.SUCCEEDED

        transcribed = service.submit_transcribe(
            TranscribeRequest(project_id=project.id, source_artifact_id=audio.id)
        )
        assert service.wait(transcribed.id, timeout=10).status == JobStatus.SUCCEEDED
    finally:
        service.close()

    artifacts = store.list_artifacts(project.id)
    assert sum(artifact.kind == "audio" for artifact in artifacts) == 3
    assert sum(artifact.kind == "score" for artifact in artifacts) >= 6
    assert any(artifact.kind == "comparison" for artifact in artifacts)


def test_single_instance_lock_prevents_two_services(settings) -> None:
    first = MusicService(settings)
    try:
        with pytest.raises(ServiceError, match="already owns"):
            MusicService(settings)
    finally:
        first.close()
    replacement = MusicService(settings)
    replacement.close()


def test_service_restart_recovers_incomplete_jobs(settings) -> None:
    from yue2_music_os.models import JobKind

    store = Store(settings.data_dir)
    project = store.create_project("Recovery")
    queued = store.create_job(project.id, JobKind.GENERATE, {"source": "test"})
    service = MusicService(settings, store=store)
    try:
        recovered = store.get_job(queued.id)
        assert recovered.status == JobStatus.FAILED
        assert "Interrupted by service restart" in (recovered.error or "")
        assert service.doctor()["recovered_incomplete_jobs"] == 1
    finally:
        service.close()
