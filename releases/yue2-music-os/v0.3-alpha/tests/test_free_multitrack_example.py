from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "examples" / "free_multitrack_command_provider.py"
SPEC = importlib.util.spec_from_file_location("free_multitrack_command_provider", SCRIPT)
assert SPEC and SPEC.loader
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


def test_basic_pitch_event_is_normalized_and_clamped():
    event = worker.parse_basic_pitch_event((0.1, 0.5, 60.6, 1.4), stem="piano", index=2)
    assert event["provider_note_id"] == "piano-basic-pitch-2"
    assert event["pitch_midi"] == 61
    assert event["velocity"] == 127
    assert event["confidence"] == 1.0


def test_invalid_event_timing_is_rejected():
    with pytest.raises(ValueError, match="timing"):
        worker.parse_basic_pitch_event((1.0, 0.5, 60, 0.5), stem="piano", index=0)


def test_stem_output_classifier_prefers_exact_names(tmp_path):
    exact = tmp_path / "guitar.wav"
    verbose = tmp_path / "song_(Guitar)_htdemucs_6s.wav"
    exact.write_bytes(b"exact")
    verbose.write_bytes(b"verbose")
    result = worker.classify_stem_outputs([verbose, exact, tmp_path / "noise.wav"])
    assert result["guitar"] == exact


def test_transcribe_keeps_partial_stem_failure_and_source_immutable(tmp_path):
    source = tmp_path / "song.wav"
    source.write_bytes(b"unchanged-audio")
    output = tmp_path / "out"
    stems = output / "stems"
    stems.mkdir(parents=True)
    vocals = stems / "vocals.wav"
    drums = stems / "drums.wav"
    vocals.write_bytes(b"voice")
    drums.write_bytes(b"drums")

    def fake_separator(*_args, **_kwargs):
        return {"vocals": vocals, "drums": drums}, {"separator_model": "fake"}

    def fake_pitch(_path):
        return [(0.01, 0.25, 64, 0.8)]

    def failed_drums(_path):
        raise RuntimeError("drum probe failed")

    payload = worker.transcribe(
        source=source,
        output_dir=output,
        separator_model="fake",
        precision="fp32",
        use_torch_compile=False,
        demucs_shifts=0,
        demucs_overlap=0.25,
        separator_runner=fake_separator,
        pitch_runner=fake_pitch,
        drum_runner=failed_drums,
    )
    assert payload["provider_id"] == "free-multitrack-v1"
    assert payload["metadata"]["source_mutated"] is False
    assert payload["metadata"]["note_count"] == 1
    assert source.read_bytes() == b"unchanged-audio"
    drum_track = next(track for track in payload["tracks"] if track["instrument"] == "drums")
    assert drum_track["notes"] == []
    assert payload["metadata"]["stem_receipts"]["drums"]["status"] == "failed"


def test_self_test_contract():
    worker.self_test()
