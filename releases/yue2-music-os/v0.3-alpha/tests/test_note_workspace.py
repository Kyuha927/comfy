from __future__ import annotations

import io
from pathlib import Path

from yue2_music_os.note_ir import (
    DetectedNote,
    DetectedTrack,
    NotePatchRequest,
    ProviderTier,
    TranscriptionResult,
)
from yue2_music_os.note_providers import (
    NoteProvider,
    NoteProviderInfo,
    NoteProviderRegistry,
    ProviderCapability,
)
from yue2_music_os.note_workspace import (
    NoteAnalysisRequest,
    NoteImportRequest,
    NoteWorkspace,
    RestoreRevisionRequest,
)
from yue2_music_os.storage import Store


class FakeProvider(NoteProvider):
    def info(self):
        return NoteProviderInfo(
            provider_id="fake-free",
            label="Fake free",
            tier=ProviderTier.FREE,
            mode="test",
            ready=True,
            capabilities=ProviderCapability(full_mix=True, per_note_confidence=True),
        )

    def transcribe(self, *, source_path: Path, output_dir: Path, instrument_hint: str | None = None):
        output_dir.mkdir(parents=True, exist_ok=True)
        return TranscriptionResult(
            provider_id="fake-free",
            tier=ProviderTier.FREE,
            mode="test",
            tracks=[
                DetectedTrack(
                    instrument=instrument_hint or "piano",
                    notes=[
                        DetectedNote(
                            pitch_midi=60,
                            start_sec=0.1,
                            end_sec=0.8,
                            confidence=0.95,
                        )
                    ],
                )
            ],
        )


def make_workspace(tmp_path: Path):
    store = Store(tmp_path / "data")
    project = store.create_project("Test")
    audio = store.save_upload(project.id, "song.wav", io.BytesIO(b"RIFF-fake"), 1024)
    workspace = NoteWorkspace(store=store, providers=NoteProviderRegistry([FakeProvider()]))
    return store, project, audio, workspace


def test_import_patch_restore_and_export(tmp_path: Path):
    _store, project, audio, workspace = make_workspace(tmp_path)
    try:
        ir = workspace.import_transcription(
            NoteImportRequest(
                project_id=project.id,
                source_artifact_id=audio.id,
                title="Imported",
                provider_id="external-free",
                tracks=[
                    DetectedTrack(
                        instrument="guitar",
                        notes=[DetectedNote(pitch_midi=68, start_sec=1, end_sec=2, confidence=0.9)],
                    )
                ],
            )
        )
        note = next(ir.iter_notes())
        edited, receipt = workspace.patch_note(
            ir.music_ir_id,
            note.note_id,
            NotePatchRequest(pitch_midi=69, edit_reason="correct pitch"),
        )
        assert edited.revision == 2
        assert receipt.after["pitch"]["name"] == "A4"
        assert len(workspace.list_revisions(ir.music_ir_id)) == 2
        restored = workspace.restore_revision(
            ir.music_ir_id, RestoreRevisionRequest(revision=1, reason="undo")
        )
        assert restored.revision == 3
        assert next(restored.iter_notes()).pitch.midi == 68
        midi = workspace.midi_path(ir.music_ir_id)
        assert midi.read_bytes().startswith(b"MThd")
        assert workspace.current_json_path(ir.music_ir_id).is_file()
    finally:
        workspace.close()


def test_analysis_job_runs_ready_free_provider(tmp_path: Path):
    _store, project, audio, workspace = make_workspace(tmp_path)
    try:
        job = workspace.submit_analysis(
            NoteAnalysisRequest(
                project_id=project.id,
                source_artifact_id=audio.id,
                instrument_hint="piano",
            )
        )
        completed = workspace.wait(job.id, timeout=5)
        assert completed.status == "succeeded"
        ir = workspace.get_ir(completed.result["music_ir_id"])
        assert ir.stats()["note_count"] == 1
        assert next(ir.iter_notes()).pitch.midi == 60
    finally:
        workspace.close()
