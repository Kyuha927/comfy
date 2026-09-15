from __future__ import annotations

from yue2_music_os.note_ir import (
    DetectedNote,
    DetectedTrack,
    NotePatchRequest,
    ProviderTier,
    ReviewState,
    TimeSignature,
    TranscriptionResult,
    apply_note_patch,
    fuse_transcriptions,
    midi_note_name,
    music_ir_to_midi_bytes,
    review_queue,
)


def sample_ir():
    first = TranscriptionResult(
        provider_id="free-a",
        provider_version="1",
        tier=ProviderTier.FREE,
        mode="test",
        tracks=[
            DetectedTrack(
                instrument="electric guitar",
                polyphonic=True,
                notes=[
                    DetectedNote(
                        provider_note_id="a1",
                        pitch_midi=68,
                        start_sec=1.0,
                        end_sec=1.5,
                        velocity=90,
                        confidence=0.94,
                    )
                ],
            )
        ],
    )
    second = TranscriptionResult(
        provider_id="free-b",
        provider_version="2",
        tier=ProviderTier.FREE,
        mode="test",
        tracks=[
            DetectedTrack(
                instrument="electric-guitar",
                polyphonic=True,
                notes=[
                    DetectedNote(
                        provider_note_id="b1",
                        pitch_midi=68,
                        start_sec=1.02,
                        end_sec=1.49,
                        velocity=92,
                        confidence=0.91,
                    )
                ],
            )
        ],
    )
    return fuse_transcriptions(
        project_id="a" * 32,
        source_artifact_id="b" * 32,
        title="Test",
        results=[first, second],
        tempo_bpm=165,
        time_signature=TimeSignature(numerator=4, denominator=4),
    )


def test_midi_note_name():
    assert midi_note_name(60) == "C4"
    assert midi_note_name(68) == "G#4"


def test_fusion_assigns_stable_note_and_consensus():
    ir = sample_ir()
    note = next(ir.iter_notes())
    assert note.note_id.startswith("note_")
    assert note.pitch.midi == 68
    assert len(note.provenance) == 2
    assert note.confidence.overall >= 0.82
    assert note.review_state == ReviewState.AUTO
    assert ir.stats()["note_count"] == 1


def test_patch_preserves_identity_and_creates_receipt():
    ir = sample_ir()
    note = next(ir.iter_notes())
    edited, receipt = apply_note_patch(
        ir,
        note.note_id,
        NotePatchRequest(pitch_midi=69, velocity=101, edit_reason="fix detected note"),
    )
    changed = next(edited.iter_notes())
    assert changed.note_id == note.note_id
    assert changed.pitch.midi == 69
    assert changed.pitch.name == "A4"
    assert changed.velocity == 101
    assert changed.review_state == ReviewState.EDITED
    assert edited.revision == 2
    assert receipt.before["pitch"]["name"] == "G#4"
    assert receipt.after["pitch"]["name"] == "A4"
    assert receipt.audio_changed is False
    assert receipt.audio_render_required is True


def test_review_queue_surfaces_disagreement():
    result_a = TranscriptionResult(
        provider_id="a",
        tracks=[DetectedTrack(instrument="piano", notes=[DetectedNote(pitch_midi=60, start_sec=0, end_sec=1, confidence=0.6)])],
    )
    result_b = TranscriptionResult(
        provider_id="b",
        tracks=[DetectedTrack(instrument="piano", notes=[DetectedNote(pitch_midi=61, start_sec=0.02, end_sec=1, confidence=0.6)])],
    )
    ir = fuse_transcriptions(
        project_id="a" * 32,
        source_artifact_id=None,
        title="Conflict",
        results=[result_a, result_b],
    )
    queue = review_queue(ir)
    assert len(queue) == 1
    assert "provider-disagreement" in queue[0]["tags"]


def test_midi_export_is_valid_type_one_header():
    data = music_ir_to_midi_bytes(sample_ir())
    assert data[:4] == b"MThd"
    assert int.from_bytes(data[8:10], "big") == 1
    assert b"MTrk" in data
