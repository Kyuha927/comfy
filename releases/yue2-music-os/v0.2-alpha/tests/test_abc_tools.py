from __future__ import annotations

import pytest

from yue2_music_os.abc_tools import AbcError, compare, parse, report, strip_chords
from yue2_music_os.sample_data import SAMPLE_JAZZ_SCORE, SAMPLE_SCORE


def test_parse_and_report_native_score() -> None:
    score = parse(SAMPLE_SCORE)
    data = report(score)
    assert data["bpm"] == 120
    assert data["voices"]["Vocal"]["measures"] == 4
    assert data["voices"]["Vocal"]["sounding_notes"] == 16
    assert data["voices"]["Ins"]["sounding_notes"] == 8


def test_harmony_edit_preserves_melody() -> None:
    result = compare(parse(SAMPLE_SCORE), parse(SAMPLE_JAZZ_SCORE))
    assert result["match"] is True
    assert result["harmony_changed"] is True
    assert result["differences"] == []


def test_strip_chords_keeps_both_melodies() -> None:
    stripped = strip_chords(SAMPLE_SCORE)
    parsed = parse(stripped)
    assert parsed.voices["Vocal"].chords == []
    assert compare(parse(SAMPLE_SCORE), parsed)["match"] is True


def test_strip_to_one_voice_replaces_other_with_rests() -> None:
    stripped = strip_chords(SAMPLE_SCORE, keep_voice="Vocal")
    parsed = parse(stripped)
    assert parsed.voices["Vocal"].notes
    assert parsed.voices["Ins"].notes == []
    assert compare(parse(SAMPLE_SCORE), parsed, names=("Vocal",))["match"] is True


def test_invalid_duration_fails_closed() -> None:
    broken = SAMPLE_SCORE.replace("C8 D8 E8 G8", "C7 D8 E8 G8")
    with pytest.raises(AbcError):
        parse(broken)
