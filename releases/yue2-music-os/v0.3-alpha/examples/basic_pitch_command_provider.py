#!/usr/bin/env python3
"""Isolated Basic Pitch adapter for YuE2 Music OS Note IR.

Install this script in a separate compatible virtual environment:
    python -m pip install basic-pitch

The controller invokes it without a shell and reads only the normalized JSON.
"""
from __future__ import annotations

import argparse
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def parse_event(event, index: int) -> dict[str, object]:
    if isinstance(event, dict):
        start = event.get("start_time_s", event.get("start_sec"))
        end = event.get("end_time_s", event.get("end_sec"))
        pitch = event.get("pitch_midi", event.get("pitch"))
        amplitude = event.get("amplitude", event.get("confidence", 0.5))
    else:
        start, end, pitch, amplitude = event[:4]
    amplitude = max(0.0, min(1.0, float(amplitude)))
    return {
        "provider_note_id": f"basic-pitch-cli-{index}",
        "pitch_midi": int(round(float(pitch))),
        "cents": 0.0,
        "start_sec": float(start),
        "end_sec": float(end),
        "velocity": max(1, min(127, round(amplitude * 127))),
        "confidence": amplitude,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--instrument-hint", default="unknown")
    args = parser.parse_args()

    from basic_pitch.inference import predict

    source = Path(args.input).expanduser().resolve(strict=True)
    destination = Path(args.output_json).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    _model_output, midi_data, note_events = predict(str(source))
    try:
        package_version = version("basic-pitch")
    except PackageNotFoundError:
        package_version = None
    native_midi = destination.with_suffix(".mid")
    try:
        midi_data.write(str(native_midi))
    except Exception:
        native_midi = None

    payload = {
        "provider_id": "basic-pitch-cli",
        "provider_version": package_version,
        "tier": "free",
        "mode": "command",
        "tracks": [
            {
                "name": args.instrument_hint.replace("-", " ").title(),
                "instrument": args.instrument_hint,
                "polyphonic": True,
                "notes": [parse_event(event, index) for index, event in enumerate(note_events)],
            }
        ],
        "warnings": [
            "Amplitude is a routing heuristic, not a calibrated confidence probability.",
            "Use an isolated stem when possible.",
        ],
        "metadata": {"native_midi": native_midi.name if native_midi else None},
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
