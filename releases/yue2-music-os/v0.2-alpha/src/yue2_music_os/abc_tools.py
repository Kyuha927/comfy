#!/usr/bin/env python3
"""Inspect the limited two-voice ABC dialect used by YuE2 and SheetSage2.

Adapted from the YuE2 project's Apache-2.0 ``abc_tools.py`` helper.
This is deliberately not a general ABC parser. It fails closed on unsupported
notation and compares resolved musical events rather than source strings.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from fractions import Fraction


VOICES = ("Vocal", "Ins")
DURATIONS = {1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48}
QUALITIES = (
    "",
    "m",
    "dim",
    "aug",
    "7",
    "maj7",
    "m7",
    "dim7",
    "m7b5",
    "sus4",
    "sus2",
    "6",
    "m6",
    "7sus4",
    "m(maj7)",
)
PITCH_NAME = r"[A-G](?:bb|##|b|#)?"
CHORD = re.compile(
    PITCH_NAME
    + "(?:"
    + "|".join(re.escape(q) for q in QUALITIES)
    + ")(?:/"
    + PITCH_NAME
    + ")?"
)
TOKEN = re.compile(
    r'"(?P<chord>[^"\n]*)"|\[K:(?P<key>[^\]\n]+)\]|'
    r"(?P<acc>\^\^|__|\^|_|=)?(?P<note>[A-Ga-gz])"
    r"(?P<oct>[,']*)(?P<duration>[0-9]*)(?P<tie>-?)"
)
NATURAL = dict(zip("CDEFGAB", (0, 2, 4, 5, 7, 9, 11)))
KEYS = {
    **dict(
        zip(
            (
                "Cb",
                "Gb",
                "Db",
                "Ab",
                "Eb",
                "Bb",
                "F",
                "C",
                "G",
                "D",
                "A",
                "E",
                "B",
                "F#",
                "C#",
            ),
            range(-7, 8),
        )
    ),
    **dict(
        zip(
            (
                "Abm",
                "Ebm",
                "Bbm",
                "Fm",
                "Cm",
                "Gm",
                "Dm",
                "Am",
                "Em",
                "Bm",
                "F#m",
                "C#m",
                "G#m",
                "D#m",
                "A#m",
            ),
            range(-7, 8),
        )
    ),
}


class AbcError(ValueError):
    """Unsupported notation or a failed structural invariant."""


def fail(condition: bool, message: str) -> None:
    if condition:
        raise AbcError(message)


def key_accidentals(key: str) -> dict[str, int]:
    fail(key not in KEYS, f"Unsupported key {key!r}; use a standard major or minor K: field")
    count = KEYS[key]
    result = {letter: 0 for letter in NATURAL}
    for letter in ("FCGDAEB" if count > 0 else "BEADGCF")[: abs(count)]:
        result[letter] = 1 if count > 0 else -1
    return result


def meter_value(text: str) -> tuple[int, int]:
    match = re.fullmatch(r"([1-9][0-9]*)/([1-9][0-9]*)", text)
    fail(match is None, f"Unsupported meter {text!r}; write an explicit fraction")
    assert match is not None
    n, d = map(int, match.groups())
    fail(d > 1024 or d & (d - 1) != 0, f"Unsupported meter denominator {d}")
    return n, d


@dataclass
class Voice:
    meter: tuple[int, int]
    key: str
    time: Fraction = Fraction(0)
    notes: list[list[object]] = field(default_factory=list)
    bars: list[tuple[Fraction, Fraction, tuple[int, int]]] = field(default_factory=list)
    chords: list[tuple[Fraction, str]] = field(default_factory=list)
    keys: list[tuple[Fraction, str]] = field(default_factory=list)
    pending: tuple[int, int] | None = None


@dataclass
class Score:
    text: str
    unit: Fraction
    bpm: int
    voices: dict[str, Voice]
    music_lines: dict[int, str]


def parse_bar(body: str, voice: Voice, unit: Fraction, context: str) -> None:
    n, d = voice.meter
    length = Fraction(4 * n, d)
    start = voice.time
    offset = Fraction(0)
    local: dict[str, int] = {}
    if body == "Z":
        fail(voice.pending is not None, f"{context}: tie enters a full-measure rest")
        offset = length
    else:
        cursor = 0
        while cursor < len(body):
            if body[cursor].isspace():
                cursor += 1
                continue
            match = TOKEN.match(body, cursor)
            fail(match is None, f"{context}: unsupported token at {body[cursor:cursor + 24]!r}")
            assert match is not None
            cursor = match.end()
            chord, key = match.group("chord", "key")
            fail(offset >= length, f"{context}: event after the measure end")
            if chord is not None:
                fail(CHORD.fullmatch(chord) is None, f"{context}: unsupported chord {chord!r}")
                voice.chords.append((start + offset, chord))
                continue
            if key is not None:
                key_accidentals(key)
                voice.key = key
                voice.keys.append((start + offset, key))
                local = {}
                continue
            note, acc, octave, tie = match.group("note", "acc", "oct", "tie")
            units = int(match.group("duration") or "1")
            fail(
                units not in DURATIONS,
                f"{context}: unsupported duration {units}; split it into tied supported lengths",
            )
            duration = units * unit * 4
            fail(offset + duration > length, f"{context}: note/rest exceeds meter duration")
            fail("," in octave and "'" in octave, f"{context}: mixed octave marks")
            if note == "z":
                fail(
                    bool(acc or octave or tie),
                    f"{context}: a rest cannot have accidentals, octave marks or ties",
                )
                fail(voice.pending is not None, f"{context}: tie enters a rest")
            else:
                letter = note.upper()
                written = 60 + NATURAL[letter] + (12 if note.islower() else 0)
                written += 12 * (octave.count("'") - octave.count(","))
                alteration = local.get(letter, key_accidentals(voice.key)[letter])
                if acc:
                    alteration = {"=": 0, "_": -1, "__": -2, "^": 1, "^^": 2}[acc]
                    local[letter] = alteration
                pitch = written + alteration
                if voice.pending is not None:
                    old_pitch, old_written = voice.pending
                    if not acc and written == old_written:
                        pitch = old_pitch
                    fail(
                        pitch != old_pitch,
                        f"{context}: tie changes pitch from {old_pitch} to {pitch}",
                    )
                    voice.notes[-1][2] = voice.notes[-1][2] + duration
                else:
                    fail(not 0 <= pitch <= 127, f"{context}: pitch {pitch} is outside MIDI range")
                    voice.notes.append([start + offset, pitch, duration])
                voice.pending = (pitch, written) if tie else None
            offset += duration
    fail(offset != length, f"{context}: duration {offset} quarter notes != meter duration {length}")
    voice.bars.append((start, length, voice.meter))
    voice.time += length


def parse(text: str) -> Score:
    """Parse YuE2's limited native two-voice ABC dialect."""
    lines = text.splitlines()
    fail(len(lines) < 12, "Incomplete native two-voice ABC")
    fail(lines[0:2] != ["X:1", "T:"], "Expected native X:1 and blank T: header")
    fail(not lines[2].startswith("M:"), "Missing header M:")
    meter = meter_value(lines[2][2:])
    unit_match = re.fullmatch(r"L:1/([1-9][0-9]*)", lines[3])
    fail(unit_match is None, "Expected L:1/<power of two>, usually L:1/32")
    assert unit_match is not None
    denominator = int(unit_match.group(1))
    fail(
        denominator > 1024 or denominator & (denominator - 1) != 0,
        "Unsupported L: denominator",
    )
    unit = Fraction(1, denominator)
    tempo_match = re.fullmatch(r"Q:1/4=([1-9][0-9]*)", lines[4])
    fail(tempo_match is None, "Expected integer quarter-note tempo Q:1/4=<BPM>")
    assert tempo_match is not None
    expected_voices = [
        'V: Vocal clef=treble name="Vocal Melody" snm="Vocal"',
        'V: Ins clef=treble name="Ins Melody" snm="Inst."',
    ]
    fail(lines[5:7] != expected_voices, "Preserve native Vocal and Ins voice definitions")
    fail(not lines[7].startswith("K:"), "Missing header K:")
    key = lines[7][2:]
    key_accidentals(key)
    voices = {
        name: Voice(meter, key, keys=[(Fraction(0), key)]) for name in VOICES
    }
    music_lines: dict[int, str] = {}
    cursor = 8
    group = 0
    while cursor < len(lines):
        while cursor < len(lines) and lines[cursor].startswith("% "):
            cursor += 1
        fail(cursor == len(lines), "Dangling section comment without music")
        group += 1
        counts: list[int] = []
        for name in VOICES:
            context = f"group {group}, {name}"
            fail(
                cursor >= len(lines) or lines[cursor] != f"V: {name}",
                f"{context}: expected V: {name}",
            )
            cursor += 1
            voice = voices[name]
            fields: set[str] = set()
            while cursor < len(lines) and lines[cursor].startswith(("M:", "K:")):
                field_name, value = lines[cursor].split(":", 1)
                fail(field_name in fields, f"{context}: duplicate {field_name}: field")
                fields.add(field_name)
                if field_name == "M":
                    voice.meter = meter_value(value)
                else:
                    key_accidentals(value)
                    voice.key = value
                    voice.keys.append((voice.time, value))
                cursor += 1
            fail(cursor >= len(lines), f"{context}: missing music line")
            line = lines[cursor]
            fail(not line.endswith("|"), f"{context}: music line must end with a plain barline")
            music_lines[cursor] = name
            cursor += 1
            bars: list[str] = []
            for bar in line[:-1].split("|"):
                bar = bar.strip()
                fail(not bar, f"{context}: empty measure or unsupported double/repeat barline")
                rest = re.fullmatch(r"Z([2-4])?", bar)
                if rest:
                    bars.extend(["Z"] * int(rest.group(1) or "1"))
                else:
                    bars.append(bar)
            fail(
                not 1 <= len(bars) <= 4,
                f"{context}: expected 1–4 measures after expanding Z rests",
            )
            counts.append(len(bars))
            for bar in bars:
                parse_bar(bar, voice, unit, f"{context}, bar {len(voice.bars) + 1}")
        fail(counts[0] != counts[1], f"group {group}: voices have different measure counts")
    for name, voice in voices.items():
        fail(voice.pending is not None, f"{name}: unresolved tie at end of score")
    fail(voices["Ins"].chords != [], "Native chord symbols belong in Vocal, not Ins")
    fail(voices["Vocal"].bars != voices["Ins"].bars, "Voice meter/time grids differ")
    fail(
        voices["Vocal"].keys != voices["Ins"].keys,
        "Voice key-change timelines differ",
    )
    return Score(text, unit, int(tempo_match.group(1)), voices, music_lines)


def _serialize(value: object) -> object:
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


def report(score: Score) -> dict[str, object]:
    return {
        "scope": "native-dialect structural check; not audio verification",
        "sha256": hashlib.sha256(score.text.encode("utf-8")).hexdigest(),
        "bpm": score.bpm,
        "unit_length": str(score.unit),
        "duration_quarters": str(score.voices["Vocal"].time),
        "nominal_duration_seconds": float(
            score.voices["Vocal"].time * 60 / score.bpm
        ),
        "voices": {
            name: {
                "sounding_notes": len(voice.notes),
                "measures": len(voice.bars),
                "notes": [
                    {
                        "onset_quarters": str(onset),
                        "midi_pitch": pitch,
                        "duration_quarters": str(duration),
                    }
                    for onset, pitch, duration in voice.notes
                ],
                "chords": _serialize(voice.chords),
                "keys": _serialize(voice.keys),
                "bars": _serialize(voice.bars),
            }
            for name, voice in score.voices.items()
        },
    }


def compare(
    before: Score,
    after: Score,
    names: tuple[str, ...] = VOICES,
    allow_tempo_change: bool = False,
) -> dict[str, object]:
    differences: list[str] = []
    if before.bpm != after.bpm and not allow_tempo_change:
        differences.append("quarter-note tempo differs")
    for name in names:
        a, b = before.voices[name], after.voices[name]
        if a.bars != b.bars:
            differences.append(f"{name}: bar meter/time grid differs")
        if a.notes != b.notes:
            common = min(len(a.notes), len(b.notes))
            first = next(
                (index for index in range(common) if a.notes[index] != b.notes[index]),
                common,
            )
            differences.append(
                f"{name}: sounding notes differ starting at note {first + 1} (pitch, onset or duration)"
            )
    before_chords = before.voices["Vocal"].chords
    after_chords = after.voices["Vocal"].chords
    return {
        "match": not differences,
        "compared_voices": list(names),
        "tempo_change_allowed": allow_tempo_change,
        "differences": differences,
        "harmony_changed": before_chords != after_chords,
        "harmony": {
            "before": _serialize(before_chords),
            "after": _serialize(after_chords),
        },
        "scope": "exact symbolic melody and meter; harmony is reported separately; no claim about generated audio",
    }


def strip_chords(text: str, keep_voice: str = "both") -> str:
    if keep_voice not in {"both", *VOICES}:
        raise AbcError(f"Unsupported keep_voice {keep_voice!r}")
    source = parse(text)
    lines = text.splitlines(keepends=True)
    for index, name in source.music_lines.items():

        def transform(match: re.Match[str]) -> str:
            if match.group("chord") is not None:
                return ""
            if (
                keep_voice != "both"
                and name != keep_voice
                and match.group("note") is not None
            ):
                return "z" + match.group("duration")
            return match.group(0)

        lines[index] = TOKEN.sub(transform, lines[index])
    output = "".join(lines)
    result = parse(output)
    names = VOICES if keep_voice == "both" else (keep_voice,)
    invariant = compare(source, result, names)
    fail(
        not bool(invariant["match"]),
        f"Chord removal changed melody: {invariant['differences']}",
    )
    fail(
        any(voice.chords for voice in result.voices.values()),
        "Chord removal left a chord symbol",
    )
    if keep_voice != "both":
        fail(
            any(
                voice.notes
                for name, voice in result.voices.items()
                if name != keep_voice
            ),
            "Unselected voice was not silenced",
        )
    return output
