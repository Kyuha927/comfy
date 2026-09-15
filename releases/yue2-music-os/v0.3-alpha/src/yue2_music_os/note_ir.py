from __future__ import annotations

import hashlib
import math
import re
import struct
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from statistics import fmean, pstdev
from typing import Any, Iterable, Iterator, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


SCHEMA_VERSION = "yue2.music-ir/v1"
_NOTE_ID = re.compile(r"note_[0-9a-f]{20}(?:_[0-9]+)?")
_TRACK_ID = re.compile(r"track_[a-z0-9][a-z0-9._-]{0,63}")
_PROVIDER_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


class ReviewState(StrEnum):
    AUTO = "auto"
    REVIEW = "review"
    CONFIRMED = "confirmed"
    EDITED = "edited"
    REJECTED = "rejected"


class AudioEditability(StrEnum):
    SYMBOLIC_ONLY = "symbolic-only"
    MONOPHONIC_PITCH = "monophonic-pitch"
    RESYNTHESIS_REQUIRED = "resynthesis-required"


class ProviderTier(StrEnum):
    FREE = "free"
    PAID = "paid"
    TEST = "test"


def utc_now() -> datetime:
    return datetime.now(UTC)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def midi_note_name(midi: int) -> str:
    if not 0 <= midi <= 127:
        raise ValueError("MIDI pitch must be between 0 and 127")
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return f"{names[midi % 12]}{midi // 12 - 1}"


def normalize_instrument(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "unknown"


def stable_track_id(instrument: str, ordinal: int = 1) -> str:
    slug = normalize_instrument(instrument)[:48]
    return f"track_{slug}-{ordinal}"


def stable_note_id(
    *,
    project_id: str,
    source_artifact_id: str | None,
    track_id: str,
    pitch_midi: int,
    start_sec: float,
    end_sec: float,
    ordinal: int = 0,
) -> str:
    material = "|".join(
        [
            project_id,
            source_artifact_id or "none",
            track_id,
            str(pitch_midi),
            str(round(start_sec * 1000)),
            str(round(end_sec * 1000)),
            str(ordinal),
        ]
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"note_{digest}" if ordinal == 0 else f"note_{digest}_{ordinal}"


class TimeSignature(BaseModel):
    numerator: int = Field(default=4, ge=1, le=32)
    denominator: Literal[1, 2, 4, 8, 16, 32] = 4


class NotePitch(BaseModel):
    midi: int = Field(ge=0, le=127)
    cents: float = Field(default=0.0, ge=-100.0, le=100.0)

    @property
    def name(self) -> str:
        return midi_note_name(self.midi)


class NoteTiming(BaseModel):
    start_sec: float = Field(ge=0.0)
    end_sec: float = Field(gt=0.0)
    bar: int | None = Field(default=None, ge=1)
    beat: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def end_follows_start(self) -> "NoteTiming":
        if self.end_sec <= self.start_sec:
            raise ValueError("note end_sec must be greater than start_sec")
        return self

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec


class NoteConfidence(BaseModel):
    pitch: float = Field(default=0.0, ge=0.0, le=1.0)
    timing: float = Field(default=0.0, ge=0.0, le=1.0)
    instrument: float = Field(default=0.0, ge=0.0, le=1.0)
    overall: float = Field(default=0.0, ge=0.0, le=1.0)


class ProviderVote(BaseModel):
    provider_id: str
    provider_note_id: str | None = None
    pitch_midi: int = Field(ge=0, le=127)
    cents: float = Field(default=0.0, ge=-100.0, le=100.0)
    start_sec: float = Field(ge=0.0)
    end_sec: float = Field(gt=0.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _PROVIDER_ID.fullmatch(normalized):
            raise ValueError("invalid provider id")
        return normalized


class SourceRegion(BaseModel):
    artifact_id: str | None = None
    stem_id: str | None = None
    start_sample: int | None = Field(default=None, ge=0)
    end_sample: int | None = Field(default=None, ge=1)
    channel: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def sample_order(self) -> "SourceRegion":
        if (
            self.start_sample is not None
            and self.end_sample is not None
            and self.end_sample <= self.start_sample
        ):
            raise ValueError("end_sample must be greater than start_sample")
        return self


class MusicNote(BaseModel):
    note_id: str
    track_id: str
    instrument: str
    stem: str | None = None
    pitch: NotePitch
    timing: NoteTiming
    velocity: int = Field(default=96, ge=0, le=127)
    muted: bool = False
    deleted: bool = False
    review_state: ReviewState = ReviewState.AUTO
    audio_editability: AudioEditability = AudioEditability.SYMBOLIC_ONLY
    confidence: NoteConfidence = Field(default_factory=NoteConfidence)
    source_region: SourceRegion | None = None
    provenance: list[ProviderVote] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list, max_length=64)

    @field_validator("note_id")
    @classmethod
    def validate_note_id(cls, value: str) -> str:
        if not _NOTE_ID.fullmatch(value):
            raise ValueError("invalid note id")
        return value

    @field_validator("track_id")
    @classmethod
    def validate_track_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _TRACK_ID.fullmatch(normalized):
            raise ValueError("invalid track id")
        return normalized

    @field_validator("instrument")
    @classmethod
    def validate_instrument(cls, value: str) -> str:
        return normalize_instrument(value)

    def public_dict(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["pitch"]["name"] = self.pitch.name
        payload["timing"]["duration_sec"] = round(self.timing.duration_sec, 6)
        return payload


class MusicTrack(BaseModel):
    track_id: str
    name: str
    instrument: str
    stem: str | None = None
    channel_hint: int | None = Field(default=None, ge=0, le=15)
    notes: list[MusicNote] = Field(default_factory=list)

    @field_validator("track_id")
    @classmethod
    def validate_track_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _TRACK_ID.fullmatch(normalized):
            raise ValueError("invalid track id")
        return normalized

    @field_validator("instrument")
    @classmethod
    def validate_instrument(cls, value: str) -> str:
        return normalize_instrument(value)

    @model_validator(mode="after")
    def note_track_ids_match(self) -> "MusicTrack":
        mismatches = [note.note_id for note in self.notes if note.track_id != self.track_id]
        if mismatches:
            raise ValueError(f"notes reference another track: {mismatches[:3]}")
        return self


class ProviderReceipt(BaseModel):
    provider_id: str
    tier: ProviderTier
    version: str | None = None
    mode: str
    note_count: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class MusicIR(BaseModel):
    schema_version: str = SCHEMA_VERSION
    music_ir_id: str
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    source_artifact_id: str | None = None
    tempo_bpm: float = Field(default=120.0, gt=0.0, le=400.0)
    time_signature: TimeSignature = Field(default_factory=TimeSignature)
    key_signature: str | None = Field(default=None, max_length=32)
    tracks: list[MusicTrack] = Field(default_factory=list)
    providers: list[ProviderReceipt] = Field(default_factory=list)
    revision: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    limitations: list[str] = Field(default_factory=list)

    @field_validator("music_ir_id")
    @classmethod
    def validate_ir_id(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{32}", value):
            raise ValueError("invalid music_ir_id")
        return value

    @model_validator(mode="after")
    def unique_ids(self) -> "MusicIR":
        track_ids = [track.track_id for track in self.tracks]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("track ids must be unique")
        note_ids = [note.note_id for note in self.iter_notes(include_deleted=True)]
        if len(note_ids) != len(set(note_ids)):
            raise ValueError("note ids must be unique")
        return self

    def iter_notes(self, *, include_deleted: bool = False) -> Iterator[MusicNote]:
        for track in self.tracks:
            for note in track.notes:
                if include_deleted or not note.deleted:
                    yield note

    def locate_note(self, note_id: str) -> tuple[int, int, MusicNote]:
        for track_index, track in enumerate(self.tracks):
            for note_index, note in enumerate(track.notes):
                if note.note_id == note_id:
                    return track_index, note_index, note
        raise KeyError(note_id)

    def stats(self) -> dict[str, Any]:
        notes = list(self.iter_notes())
        review = [note for note in notes if note.review_state == ReviewState.REVIEW]
        confidence = [note.confidence.overall for note in notes]
        return {
            "track_count": len(self.tracks),
            "note_count": len(notes),
            "deleted_note_count": sum(
                note.deleted for note in self.iter_notes(include_deleted=True)
            ),
            "review_note_count": len(review),
            "mean_confidence": round(fmean(confidence), 4) if confidence else 0.0,
            "duration_sec": round(
                max((note.timing.end_sec for note in notes), default=0.0), 6
            ),
        }

    def public_dict(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        for track_payload, track in zip(payload["tracks"], self.tracks, strict=True):
            track_payload["notes"] = [note.public_dict() for note in track.notes]
        payload["stats"] = self.stats()
        return payload


class DetectedNote(BaseModel):
    provider_note_id: str | None = None
    pitch_midi: int = Field(ge=0, le=127)
    cents: float = Field(default=0.0, ge=-100.0, le=100.0)
    start_sec: float = Field(ge=0.0)
    end_sec: float = Field(gt=0.0)
    velocity: int = Field(default=96, ge=0, le=127)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def end_follows_start(self) -> "DetectedNote":
        if self.end_sec <= self.start_sec:
            raise ValueError("detected note end_sec must be greater than start_sec")
        return self


class DetectedTrack(BaseModel):
    track_id: str | None = None
    name: str | None = None
    instrument: str = "unknown"
    stem: str | None = None
    polyphonic: bool | None = None
    notes: list[DetectedNote] = Field(default_factory=list)

    @field_validator("instrument")
    @classmethod
    def validate_instrument(cls, value: str) -> str:
        return normalize_instrument(value)


class TranscriptionResult(BaseModel):
    provider_id: str
    provider_version: str | None = None
    tier: ProviderTier = ProviderTier.FREE
    mode: str = "unknown"
    tracks: list[DetectedTrack]
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _PROVIDER_ID.fullmatch(normalized):
            raise ValueError("invalid provider id")
        return normalized

    @property
    def note_count(self) -> int:
        return sum(len(track.notes) for track in self.tracks)


class NotePatchRequest(BaseModel):
    pitch_midi: int | None = Field(default=None, ge=0, le=127)
    cents: float | None = Field(default=None, ge=-100.0, le=100.0)
    start_sec: float | None = Field(default=None, ge=0.0)
    end_sec: float | None = Field(default=None, gt=0.0)
    velocity: int | None = Field(default=None, ge=0, le=127)
    instrument: str | None = None
    track_id: str | None = None
    stem: str | None = None
    muted: bool | None = None
    deleted: bool | None = None
    review_state: ReviewState | None = None
    edit_reason: str = Field(default="manual note edit", min_length=1, max_length=500)

    @model_validator(mode="after")
    def has_change(self) -> "NotePatchRequest":
        fields = (
            "pitch_midi",
            "cents",
            "start_sec",
            "end_sec",
            "velocity",
            "instrument",
            "track_id",
            "stem",
            "muted",
            "deleted",
            "review_state",
        )
        if all(getattr(self, name) is None for name in fields):
            raise ValueError("at least one note field must be changed")
        if self.instrument is not None:
            self.instrument = normalize_instrument(self.instrument)
        if self.track_id is not None:
            normalized = self.track_id.strip().lower()
            if not _TRACK_ID.fullmatch(normalized):
                raise ValueError("invalid target track id")
            self.track_id = normalized
        return self


class NoteEditReceipt(BaseModel):
    music_ir_id: str
    note_id: str
    revision: int
    operation: str = "note-patch"
    reason: str
    before: dict[str, Any]
    after: dict[str, Any]
    audio_changed: bool = False
    audio_render_required: bool = True
    created_at: datetime = Field(default_factory=utc_now)


def _weighted_mean(values: Iterable[tuple[float, float]]) -> float:
    materialized = list(values)
    total = sum(weight for _, weight in materialized)
    if total <= 0:
        return fmean(value for value, _ in materialized)
    return sum(value * weight for value, weight in materialized) / total


def _overlap_ratio(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    overlap = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    union = max(a_end, b_end) - min(a_start, b_start)
    return overlap / union if union > 0 else 0.0


def fuse_transcriptions(
    *,
    project_id: str,
    source_artifact_id: str | None,
    title: str,
    results: list[TranscriptionResult],
    tempo_bpm: float = 120.0,
    time_signature: TimeSignature | None = None,
    onset_tolerance_sec: float = 0.12,
    minimum_review_confidence: float = 0.82,
) -> MusicIR:
    if not results:
        raise ValueError("at least one transcription result is required")
    if onset_tolerance_sec <= 0:
        raise ValueError("onset tolerance must be positive")

    total_provider_ids = {result.provider_id for result in results}
    candidates: list[tuple[str, str | None, bool | None, DetectedNote, TranscriptionResult]] = []
    for result in results:
        for track in result.tracks:
            for note in track.notes:
                candidates.append((track.instrument, track.stem, track.polyphonic, note, result))
    candidates.sort(key=lambda item: (item[3].start_sec, item[0], item[3].pitch_midi))

    groups: list[list[tuple[str, str | None, bool | None, DetectedNote, TranscriptionResult]]] = []
    for candidate in candidates:
        instrument, _stem, _polyphonic, note, _result = candidate
        selected: list[tuple[str, str | None, bool | None, DetectedNote, TranscriptionResult]] | None = None
        best_distance = math.inf
        for group in groups:
            group_instrument = group[0][0]
            if group_instrument != instrument:
                continue
            representative = group[0][3]
            onset_distance = abs(representative.start_sec - note.start_sec)
            if onset_distance > onset_tolerance_sec:
                continue
            if abs(representative.pitch_midi - note.pitch_midi) > 1:
                continue
            overlap = _overlap_ratio(
                representative.start_sec,
                representative.end_sec,
                note.start_sec,
                note.end_sec,
            )
            if overlap < 0.25 and abs(representative.end_sec - note.end_sec) > 0.2:
                continue
            distance = onset_distance + abs(representative.pitch_midi - note.pitch_midi) * 0.04
            if distance < best_distance:
                selected = group
                best_distance = distance
        if selected is None:
            groups.append([candidate])
        else:
            selected.append(candidate)

    by_instrument: dict[str, list[tuple[MusicNote, str | None]]] = {}
    ordinal_by_signature: dict[tuple[str, int, int, int], int] = {}
    for group in groups:
        instrument = group[0][0]
        weights = [max(0.05, item[3].confidence) for item in group]
        start = _weighted_mean((item[3].start_sec, weight) for item, weight in zip(group, weights, strict=True))
        end = _weighted_mean((item[3].end_sec, weight) for item, weight in zip(group, weights, strict=True))
        if end <= start:
            end = start + 0.01
        pitch_float = _weighted_mean((float(item[3].pitch_midi), weight) for item, weight in zip(group, weights, strict=True))
        pitch = int(clamp(round(pitch_float), 0, 127))
        cents = _weighted_mean((item[3].cents, weight) for item, weight in zip(group, weights, strict=True))
        velocity = int(
            clamp(
                round(_weighted_mean((float(item[3].velocity), weight) for item, weight in zip(group, weights, strict=True))),
                0,
                127,
            )
        )
        provider_ids = {item[4].provider_id for item in group}
        pitch_values = {item[3].pitch_midi for item in group}
        mean_input_confidence = fmean(item[3].confidence for item in group)
        provider_coverage = len(provider_ids) / max(1, len(total_provider_ids))
        onset_values = [item[3].start_sec for item in group]
        timing_spread = pstdev(onset_values) if len(onset_values) > 1 else 0.0
        timing_confidence = clamp(1.0 - timing_spread / max(onset_tolerance_sec, 1e-6), 0.0, 1.0)
        pitch_confidence = clamp(1.0 - (len(pitch_values) - 1) * 0.32, 0.0, 1.0)
        instrument_confidence = 1.0
        consensus_bonus = 0.12 if len(provider_ids) > 1 else 0.0
        overall = clamp(
            mean_input_confidence * 0.56
            + timing_confidence * 0.14
            + pitch_confidence * 0.14
            + provider_coverage * 0.04
            + consensus_bonus,
            0.0,
            1.0,
        )
        review = overall < minimum_review_confidence or len(pitch_values) > 1
        stem_values = [item[1] for item in group if item[1]]
        stem = stem_values[0] if stem_values else None
        polyphonic_values = [item[2] for item in group if item[2] is not None]
        if polyphonic_values and all(value is False for value in polyphonic_values):
            editability = AudioEditability.MONOPHONIC_PITCH
        elif polyphonic_values and any(value is True for value in polyphonic_values):
            editability = AudioEditability.RESYNTHESIS_REQUIRED
        else:
            editability = AudioEditability.SYMBOLIC_ONLY

        track_id = stable_track_id(instrument)
        signature = (instrument, pitch, round(start * 1000), round(end * 1000))
        ordinal = ordinal_by_signature.get(signature, 0)
        ordinal_by_signature[signature] = ordinal + 1
        note_id = stable_note_id(
            project_id=project_id,
            source_artifact_id=source_artifact_id,
            track_id=track_id,
            pitch_midi=pitch,
            start_sec=start,
            end_sec=end,
            ordinal=ordinal,
        )
        votes = [
            ProviderVote(
                provider_id=item[4].provider_id,
                provider_note_id=item[3].provider_note_id,
                pitch_midi=item[3].pitch_midi,
                cents=item[3].cents,
                start_sec=item[3].start_sec,
                end_sec=item[3].end_sec,
                confidence=item[3].confidence,
            )
            for item in group
        ]
        note = MusicNote(
            note_id=note_id,
            track_id=track_id,
            instrument=instrument,
            stem=stem,
            pitch=NotePitch(midi=pitch, cents=round(cents, 3)),
            timing=NoteTiming(start_sec=round(start, 6), end_sec=round(end, 6)),
            velocity=velocity,
            review_state=ReviewState.REVIEW if review else ReviewState.AUTO,
            audio_editability=editability,
            confidence=NoteConfidence(
                pitch=round(pitch_confidence, 4),
                timing=round(timing_confidence, 4),
                instrument=instrument_confidence,
                overall=round(overall, 4),
            ),
            source_region=SourceRegion(artifact_id=source_artifact_id, stem_id=stem),
            provenance=votes,
            tags=["provider-disagreement"] if len(pitch_values) > 1 else [],
        )
        by_instrument.setdefault(instrument, []).append((note, stem))

    tracks: list[MusicTrack] = []
    used_track_ids: set[str] = set()
    for instrument, note_pairs in sorted(by_instrument.items()):
        base_track_id = stable_track_id(instrument)
        track_id = base_track_id
        ordinal = 2
        while track_id in used_track_ids:
            track_id = stable_track_id(instrument, ordinal)
            ordinal += 1
        used_track_ids.add(track_id)
        notes: list[MusicNote] = []
        for note, _stem in sorted(note_pairs, key=lambda pair: (pair[0].timing.start_sec, pair[0].pitch.midi)):
            if note.track_id != track_id:
                note = note.model_copy(update={"track_id": track_id})
            notes.append(note)
        stems = [stem for _, stem in note_pairs if stem]
        tracks.append(
            MusicTrack(
                track_id=track_id,
                name=instrument.replace("-", " ").title(),
                instrument=instrument,
                stem=stems[0] if stems else None,
                notes=notes,
            )
        )

    receipts = [
        ProviderReceipt(
            provider_id=result.provider_id,
            tier=result.tier,
            version=result.provider_version,
            mode=result.mode,
            note_count=result.note_count,
            warnings=result.warnings,
        )
        for result in results
    ]
    return MusicIR(
        music_ir_id=uuid.uuid4().hex,
        project_id=project_id,
        title=title,
        source_artifact_id=source_artifact_id,
        tempo_bpm=tempo_bpm,
        time_signature=time_signature or TimeSignature(),
        tracks=tracks,
        providers=receipts,
        limitations=[
            "Automatic transcription is evidence, not ground truth; review low-confidence notes.",
            "Note edits change Music IR and MIDI only. Original audio remains immutable.",
            "A single note inside polyphonic audio generally requires resynthesis or a specialist editor.",
        ],
    )


def apply_note_patch(ir: MusicIR, note_id: str, patch: NotePatchRequest) -> tuple[MusicIR, NoteEditReceipt]:
    updated = ir.model_copy(deep=True)
    try:
        track_index, note_index, note = updated.locate_note(note_id)
    except KeyError as exc:
        raise KeyError(f"note not found: {note_id}") from exc

    before = note.public_dict()
    old_duration = note.timing.duration_sec
    new_start = patch.start_sec if patch.start_sec is not None else note.timing.start_sec
    if patch.end_sec is not None:
        new_end = patch.end_sec
    elif patch.start_sec is not None:
        new_end = new_start + old_duration
    else:
        new_end = note.timing.end_sec
    timing = NoteTiming(
        start_sec=new_start,
        end_sec=new_end,
        bar=note.timing.bar,
        beat=note.timing.beat,
    )
    pitch = NotePitch(
        midi=patch.pitch_midi if patch.pitch_midi is not None else note.pitch.midi,
        cents=patch.cents if patch.cents is not None else note.pitch.cents,
    )
    changes: dict[str, Any] = {
        "pitch": pitch,
        "timing": timing,
        "velocity": patch.velocity if patch.velocity is not None else note.velocity,
        "instrument": patch.instrument if patch.instrument is not None else note.instrument,
        "stem": patch.stem if patch.stem is not None else note.stem,
        "muted": patch.muted if patch.muted is not None else note.muted,
        "deleted": patch.deleted if patch.deleted is not None else note.deleted,
        "review_state": patch.review_state or ReviewState.EDITED,
    }
    target_track_id = patch.track_id or note.track_id
    changes["track_id"] = target_track_id
    changed_note = note.model_copy(update=changes)

    if target_track_id == note.track_id:
        updated.tracks[track_index].notes[note_index] = changed_note
    else:
        target = next((track for track in updated.tracks if track.track_id == target_track_id), None)
        if target is None:
            raise ValueError(f"target track not found: {target_track_id}")
        updated.tracks[track_index].notes.pop(note_index)
        target.notes.append(changed_note)
        target.notes.sort(key=lambda item: (item.timing.start_sec, item.pitch.midi))

    updated.revision += 1
    updated.updated_at = utc_now()
    updated = MusicIR.model_validate(updated.model_dump(mode="python"))
    _ti, _ni, final_note = updated.locate_note(note_id)
    receipt = NoteEditReceipt(
        music_ir_id=updated.music_ir_id,
        note_id=note_id,
        revision=updated.revision,
        reason=patch.edit_reason,
        before=before,
        after=final_note.public_dict(),
        audio_changed=False,
        audio_render_required=True,
    )
    return updated, receipt


def review_queue(ir: MusicIR, *, threshold: float = 0.82) -> list[dict[str, Any]]:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    notes = [
        note
        for note in ir.iter_notes()
        if note.review_state == ReviewState.REVIEW or note.confidence.overall < threshold
    ]
    notes.sort(key=lambda note: (note.confidence.overall, note.timing.start_sec, note.pitch.midi))
    return [note.public_dict() for note in notes]


def _vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError("VLQ cannot encode a negative integer")
    buffer = value & 0x7F
    encoded = bytearray([buffer])
    value >>= 7
    while value:
        buffer = (value & 0x7F) | 0x80
        encoded.insert(0, buffer)
        value >>= 7
    return bytes(encoded)


def _midi_track(events: list[tuple[int, int, bytes]]) -> bytes:
    events.sort(key=lambda item: (item[0], item[1]))
    body = bytearray()
    previous_tick = 0
    for tick, _priority, data in events:
        tick = max(previous_tick, tick)
        body.extend(_vlq(tick - previous_tick))
        body.extend(data)
        previous_tick = tick
    body.extend(b"\x00\xff\x2f\x00")
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def _track_name_event(name: str) -> bytes:
    payload = name.encode("utf-8")[:127]
    return b"\xff\x03" + _vlq(len(payload)) + payload


def music_ir_to_midi_bytes(ir: MusicIR, *, ppq: int = 480) -> bytes:
    if not 24 <= ppq <= 9600:
        raise ValueError("ppq must be between 24 and 9600")
    microseconds_per_quarter = round(60_000_000 / ir.tempo_bpm)
    denominator_power = int(math.log2(ir.time_signature.denominator))
    conductor_events = [
        (0, 0, _track_name_event(ir.title)),
        (0, 1, b"\xff\x51\x03" + microseconds_per_quarter.to_bytes(3, "big")),
        (
            0,
            2,
            bytes(
                [
                    0xFF,
                    0x58,
                    0x04,
                    ir.time_signature.numerator,
                    denominator_power,
                    24,
                    8,
                ]
            ),
        ),
    ]
    tracks = [_midi_track(conductor_events)]
    channel_pool = [channel for channel in range(16) if channel != 9]
    channel_cursor = 0
    seconds_to_ticks = ir.tempo_bpm * ppq / 60.0
    for track in ir.tracks:
        is_drum = "drum" in track.instrument or "percussion" in track.instrument
        channel = 9 if is_drum else channel_pool[channel_cursor % len(channel_pool)]
        if not is_drum:
            channel_cursor += 1
        events: list[tuple[int, int, bytes]] = [(0, 0, _track_name_event(track.name))]
        for note in track.notes:
            if note.deleted or note.muted or note.velocity <= 0:
                continue
            start_tick = max(0, round(note.timing.start_sec * seconds_to_ticks))
            end_tick = max(start_tick + 1, round(note.timing.end_sec * seconds_to_ticks))
            velocity = max(1, min(127, note.velocity))
            events.append((start_tick, 2, bytes([0x90 | channel, note.pitch.midi, velocity])))
            events.append((end_tick, 1, bytes([0x80 | channel, note.pitch.midi, 0])))
        tracks.append(_midi_track(events))
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), ppq)
    return header + b"".join(tracks)
