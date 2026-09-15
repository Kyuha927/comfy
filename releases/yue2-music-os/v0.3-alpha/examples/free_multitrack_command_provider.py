#!/usr/bin/env python3
"""Free six-stem transcription worker for YuE2 Music OS Note IR.

Pipeline:
    audio-separator htdemucs_6s -> vocals/drums/bass/guitar/piano/other
    Basic Pitch -> pitched-note events for every non-drum stem
    librosa onset detector -> generic drum-hit events

The worker is intentionally isolated behind the command-provider contract. It
never writes to the source path and emits normalized JSON that the controller
validates before storing a revision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable, Iterable

PROVIDER_ID = "free-multitrack-v1"
DEFAULT_SEPARATOR_MODEL = "htdemucs_6s.yaml"
STEM_ORDER = ("vocals", "drums", "bass", "guitar", "piano", "other")
CUSTOM_OUTPUT_NAMES = {
    "Vocals": "vocals",
    "Drums": "drums",
    "Bass": "bass",
    "Guitar": "guitar",
    "Piano": "piano",
    "Other": "other",
}
INSTRUMENTS = {
    "vocals": "voice",
    "drums": "drums",
    "bass": "electric-bass",
    "guitar": "electric-guitar",
    "piano": "piano",
    "other": "other",
}
POLYPHONIC = {
    "vocals": False,
    "drums": True,
    "bass": False,
    "guitar": True,
    "piano": True,
    "other": True,
}


def _package_version(distribution: str) -> str | None:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_fingerprint(path: Path) -> dict[str, int | str]:
    stat = path.stat()
    return {
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": _sha256(path),
    }


def parse_basic_pitch_event(event: Any, *, stem: str, index: int) -> dict[str, object]:
    if isinstance(event, dict):
        start = event.get("start_time_s", event.get("start_sec"))
        end = event.get("end_time_s", event.get("end_sec"))
        pitch = event.get("pitch_midi", event.get("pitch"))
        amplitude = event.get("amplitude", event.get("confidence", 0.5))
    elif isinstance(event, (list, tuple)) and len(event) >= 4:
        start, end, pitch, amplitude = event[:4]
    else:
        raise ValueError(f"unsupported Basic Pitch event at {stem}:{index}")

    start_float = float(start)
    end_float = float(end)
    if start_float < 0 or end_float <= start_float:
        raise ValueError(f"invalid Basic Pitch timing at {stem}:{index}")
    pitch_int = int(round(float(pitch)))
    if not 0 <= pitch_int <= 127:
        raise ValueError(f"invalid MIDI pitch at {stem}:{index}")
    confidence = _clamp(float(amplitude), 0.0, 1.0)
    return {
        "provider_note_id": f"{stem}-basic-pitch-{index}",
        "pitch_midi": pitch_int,
        "cents": 0.0,
        "start_sec": start_float,
        "end_sec": end_float,
        "velocity": int(_clamp(round(confidence * 127), 1, 127)),
        "confidence": confidence,
    }


def _stem_token(path: Path) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", path.stem.lower()).strip()
    tokens = normalized.split()
    for stem in STEM_ORDER:
        if normalized == stem or stem in tokens:
            return stem
    return None


def classify_stem_outputs(paths: Iterable[Path]) -> dict[str, Path]:
    candidates: dict[str, list[Path]] = {stem: [] for stem in STEM_ORDER}
    for raw_path in paths:
        path = Path(raw_path)
        stem = _stem_token(path)
        if stem:
            candidates[stem].append(path)

    selected: dict[str, Path] = {}
    for stem, matches in candidates.items():
        if not matches:
            continue
        matches.sort(key=lambda item: (item.stem.lower() != stem, len(item.name), item.as_posix()))
        selected[stem] = matches[0]
    return selected


def _separator_outputs(
    source: Path,
    stems_dir: Path,
    *,
    model: str,
    use_autocast: bool,
    use_torch_compile: bool,
    demucs_shifts: int,
    demucs_overlap: float,
) -> tuple[dict[str, Path], dict[str, object]]:
    try:
        from audio_separator.separator import Separator
    except Exception as exc:  # pragma: no cover - optional runtime
        raise RuntimeError(f"audio-separator import failed: {type(exc).__name__}: {exc}") from exc

    stems_dir.mkdir(parents=True, exist_ok=True)
    separator = Separator(
        output_dir=str(stems_dir),
        output_format="WAV",
        log_level=logging.INFO,
        use_autocast=use_autocast,
        use_torch_compile=use_torch_compile,
        demucs_params={
            "segment_size": "Default",
            "shifts": demucs_shifts,
            "overlap": demucs_overlap,
            "segments_enabled": True,
        },
    )
    separator.load_model(model)
    raw_outputs = separator.separate(str(source), custom_output_names=CUSTOM_OUTPUT_NAMES)
    paths: list[Path] = []
    for raw in raw_outputs or []:
        path = Path(raw)
        if not path.is_absolute():
            path = stems_dir / path
        paths.append(path.resolve())
    paths.extend(path.resolve() for path in stems_dir.rglob("*.wav"))
    unique_paths = sorted({path for path in paths if path.is_file()})
    stem_paths = classify_stem_outputs(unique_paths)
    metadata = {
        "separator_model": model,
        "audio_separator_version": _package_version("audio-separator"),
        "use_autocast": use_autocast,
        "use_torch_compile_requested": use_torch_compile,
        "effective_precision": getattr(separator, "effective_precision", None),
        "effective_torch_compile": getattr(separator, "effective_torch_compile", None),
        "demucs_shifts": demucs_shifts,
        "demucs_overlap": demucs_overlap,
    }
    return stem_paths, metadata


def _basic_pitch_events(path: Path) -> list[Any]:
    try:
        from basic_pitch.inference import predict
    except Exception as exc:  # pragma: no cover - optional runtime
        raise RuntimeError(f"Basic Pitch import failed: {type(exc).__name__}: {exc}") from exc
    try:
        _model_output, _midi_data, note_events = predict(str(path))
    except Exception as exc:  # pragma: no cover - optional runtime
        raise RuntimeError(f"Basic Pitch inference failed for {path.name}: {type(exc).__name__}: {exc}") from exc
    return list(note_events)


def _drum_notes(path: Path) -> list[dict[str, object]]:
    try:
        import librosa
        import numpy as np
    except Exception as exc:  # pragma: no cover - optional runtime
        raise RuntimeError(f"librosa drum onset import failed: {type(exc).__name__}: {exc}") from exc

    try:
        audio, sample_rate = librosa.load(str(path), sr=None, mono=True)
        onset_envelope = librosa.onset.onset_strength(y=audio, sr=sample_rate)
        frames = librosa.onset.onset_detect(
            onset_envelope=onset_envelope,
            sr=sample_rate,
            units="frames",
            backtrack=False,
        )
        times = librosa.frames_to_time(frames, sr=sample_rate)
        duration = float(librosa.get_duration(y=audio, sr=sample_rate))
    except Exception as exc:  # pragma: no cover - optional runtime
        raise RuntimeError(f"drum onset analysis failed for {path.name}: {type(exc).__name__}: {exc}") from exc

    maximum = float(np.max(onset_envelope)) if len(onset_envelope) else 0.0
    notes: list[dict[str, object]] = []
    for index, (frame, start) in enumerate(zip(frames, times, strict=True)):
        start_float = float(start)
        next_start = float(times[index + 1]) if index + 1 < len(times) else duration
        end_float = max(start_float + 0.03, min(start_float + 0.12, next_start, duration))
        raw_strength = float(onset_envelope[int(frame)]) if int(frame) < len(onset_envelope) else 0.0
        confidence = _clamp(raw_strength / maximum, 0.0, 1.0) if maximum > 0 else 0.5
        notes.append(
            {
                "provider_note_id": f"drums-onset-{index}",
                "pitch_midi": 36,
                "cents": 0.0,
                "start_sec": start_float,
                "end_sec": end_float,
                "velocity": int(_clamp(round(confidence * 127), 1, 127)),
                "confidence": confidence,
            }
        )
    return notes


def _track(stem: str, notes: list[dict[str, object]]) -> dict[str, object]:
    return {
        "name": stem.replace("-", " ").title(),
        "instrument": INSTRUMENTS[stem],
        "polyphonic": POLYPHONIC[stem],
        "notes": notes,
    }


def _should_autocast(precision: str) -> bool:
    if precision == "autocast":
        return True
    if precision == "fp32":
        return False
    return platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}


def transcribe(
    *,
    source: Path,
    output_dir: Path,
    separator_model: str,
    precision: str,
    use_torch_compile: bool,
    demucs_shifts: int,
    demucs_overlap: float,
    separator_runner: Callable[..., tuple[dict[str, Path], dict[str, object]]] = _separator_outputs,
    pitch_runner: Callable[[Path], list[Any]] = _basic_pitch_events,
    drum_runner: Callable[[Path], list[dict[str, object]]] = _drum_notes,
) -> dict[str, object]:
    source = source.expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError("input is not a file")
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    before = source_fingerprint(source)

    stem_paths, separator_metadata = separator_runner(
        source,
        output_dir / "stems",
        model=separator_model,
        use_autocast=_should_autocast(precision),
        use_torch_compile=use_torch_compile,
        demucs_shifts=demucs_shifts,
        demucs_overlap=demucs_overlap,
    )
    warnings: list[str] = [
        "Per-note confidence values are routing heuristics, not calibrated probabilities.",
        "The drums track contains generic onset events on MIDI note 36; kick/snare/cymbal classification is not claimed.",
        "The 'other' stem can contain multiple instruments and always requires review.",
        "Symbolic note edits change Note IR and MIDI, not one tone inside the original polyphonic waveform.",
    ]
    tracks: list[dict[str, object]] = []
    stem_receipts: dict[str, object] = {}

    for stem in STEM_ORDER:
        path = stem_paths.get(stem)
        if path is None:
            warnings.append(f"separator did not return the expected {stem} stem")
            stem_receipts[stem] = {"status": "missing"}
            continue
        path = path.resolve(strict=True)
        try:
            path.relative_to((output_dir / "stems").resolve())
        except ValueError as exc:
            raise RuntimeError(f"separator returned a path outside the worker output directory: {path}") from exc

        try:
            if stem == "drums":
                notes = drum_runner(path)
            else:
                events = pitch_runner(path)
                notes = [parse_basic_pitch_event(event, stem=stem, index=index) for index, event in enumerate(events)]
            tracks.append(_track(stem, notes))
            stem_receipts[stem] = {
                "status": "ok",
                "file": path.relative_to(output_dir).as_posix(),
                "notes": len(notes),
            }
        except Exception as exc:
            tracks.append(_track(stem, []))
            stem_receipts[stem] = {
                "status": "failed",
                "file": path.relative_to(output_dir).as_posix(),
                "error": f"{type(exc).__name__}: {exc}"[:1000],
            }
            warnings.append(f"{stem} transcription failed and was retained as an empty review track: {type(exc).__name__}: {exc}")

    after = source_fingerprint(source)
    if before != after:
        raise RuntimeError("source audio changed while the read-only worker was running")
    total_notes = sum(len(track["notes"]) for track in tracks)
    if total_notes <= 0:
        raise RuntimeError("free multi-track worker produced no note or onset events")

    return {
        "provider_id": PROVIDER_ID,
        "provider_version": "+".join(
            value
            for value in (
                _package_version("audio-separator"),
                _package_version("basic-pitch"),
            )
            if value
        )
        or None,
        "tier": "free",
        "mode": "command",
        "tracks": tracks,
        "warnings": warnings,
        "metadata": {
            "source_fingerprint": before,
            "source_mutated": False,
            "separator": separator_metadata,
            "basic_pitch_version": _package_version("basic-pitch"),
            "stem_receipts": stem_receipts,
            "note_count": total_notes,
            "audio_editability": "resynthesis-required",
        },
    }


def self_test() -> None:
    event = parse_basic_pitch_event((0.25, 0.5, 68.4, 1.2), stem="guitar", index=3)
    assert event["pitch_midi"] == 68
    assert event["velocity"] == 127
    assert event["confidence"] == 1.0
    classified = classify_stem_outputs(
        [
            Path("vocals.wav"),
            Path("song_(Drums)_htdemucs_6s.wav"),
            Path("piano.wav"),
            Path("unrelated.wav"),
        ]
    )
    assert set(classified) == {"vocals", "drums", "piano"}
    assert _should_autocast("autocast") is True
    assert _should_autocast("fp32") is False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input")
    parser.add_argument("--output-json")
    parser.add_argument("--output-dir")
    parser.add_argument("--instrument-hint", default="unknown", help="Accepted for provider-contract compatibility; ignored for full-mix mode.")
    parser.add_argument("--separator-model", default=DEFAULT_SEPARATOR_MODEL)
    parser.add_argument("--precision", choices=("auto", "fp32", "autocast"), default="auto")
    parser.add_argument("--use-torch-compile", action="store_true")
    parser.add_argument("--demucs-shifts", type=int, choices=range(0, 5), default=2)
    parser.add_argument("--demucs-overlap", type=float, default=0.25)
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        self_test()
        print(json.dumps({"provider_id": PROVIDER_ID, "self_test": "PASS"}))
        return 0
    if not args.input or not args.output_json or not args.output_dir:
        raise SystemExit("--input, --output-json and --output-dir are required unless --self-test is used")
    if not 0.001 <= args.demucs_overlap < 1.0:
        raise SystemExit("--demucs-overlap must be between 0.001 and 1.0")

    destination = Path(args.output_json).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = transcribe(
            source=Path(args.input),
            output_dir=Path(args.output_dir),
            separator_model=args.separator_model,
            precision=args.precision,
            use_torch_compile=args.use_torch_compile,
            demucs_shifts=args.demucs_shifts,
            demucs_overlap=args.demucs_overlap,
        )
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
