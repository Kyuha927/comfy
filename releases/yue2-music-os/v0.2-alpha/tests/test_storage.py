from __future__ import annotations

import io
from pathlib import Path

import pytest

from yue2_music_os.models import JobKind
from yue2_music_os.sample_data import SAMPLE_SCORE
from yue2_music_os.storage import InvalidUpload, Store, StoreError, safe_filename


def test_safe_filename_preserves_extension_for_unicode() -> None:
    assert safe_filename("../../노래 초안.wav").endswith(".wav")
    assert "/" not in safe_filename("../../노래 초안.wav")
    assert "\\" not in safe_filename("..\\..\\노래.wav")


def test_upload_is_hashed_and_contained(settings) -> None:
    store = Store(settings.data_dir)
    project = store.create_project("Storage")
    artifact = store.save_upload(
        project.id,
        "../../악보.abc",
        io.BytesIO(SAMPLE_SCORE.encode()),
        settings.max_upload_bytes,
    )
    path = store.get_artifact_path(artifact.id)
    assert path.is_file()
    assert settings.data_dir.resolve() in path.resolve().parents
    assert artifact.kind == "score"
    assert len(artifact.sha256) == 64


def test_upload_rejects_type_and_size(settings) -> None:
    store = Store(settings.data_dir)
    project = store.create_project("Limits")
    with pytest.raises(InvalidUpload):
        store.save_upload(project.id, "payload.exe", io.BytesIO(b"x"), 100)
    with pytest.raises(InvalidUpload):
        store.save_upload(project.id, "big.wav", io.BytesIO(b"x" * 11), 10)


def test_generated_file_must_match_job_project(settings, tmp_path: Path) -> None:
    store = Store(settings.data_dir)
    first = store.create_project("First")
    second = store.create_project("Second")
    job = store.create_job(first.id, JobKind.COMPARE, {})
    job_dir = store.job_dir(first.id, job.id)
    output = job_dir / "report.json"
    output.write_text("{}")
    with pytest.raises(StoreError):
        store.register_generated_file(second.id, job.id, output)
    with pytest.raises(StoreError):
        store.register_generated_file(first.id, job.id, tmp_path / "outside.json")


def test_upload_ignores_untrusted_client_mime_type(settings) -> None:
    store = Store(settings.data_dir)
    project = store.create_project("MIME")
    artifact = store.save_upload(
        project.id,
        "notes.txt",
        io.BytesIO(b"<script>alert(1)</script>"),
        settings.max_upload_bytes,
        media_type="text/html",
    )
    assert artifact.media_type == "text/plain"
