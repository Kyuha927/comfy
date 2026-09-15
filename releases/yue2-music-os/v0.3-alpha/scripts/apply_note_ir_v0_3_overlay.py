#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"required patch anchor missing in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


replace(ROOT / "pyproject.toml", 'version = "0.2.0a1"', 'version = "0.3.0a1"')
replace(
    ROOT / "src/yue2_music_os/__init__.py",
    '__version__ = "0.2.0a1"',
    '__version__ = "0.3.0a1"',
)
replace(
    ROOT / "README.md",
    "# YuE2 Music OS v0.2 alpha",
    "# YuE2 Music OS v0.3 alpha",
)
replace(
    ROOT / "src/yue2_music_os/static/index.html",
    '<div class="top-actions">',
    '<div class="top-actions">\n      <a class="ghost-button" href="/note-editor.html">음표 편집실</a>',
)

readme_addition = """

## Note IR and individual-note editing

v0.3 adds a free-first Note IR pipeline next to the existing score and production-render paths. Open `/note-editor.html` to analyze or import note detections, inspect provider votes and confidence, edit one note, restore immutable revisions, and export JSON or MIDI. Source audio is never overwritten. Polyphonic single-note waveform edits remain an explicit resynthesis or specialist-engine boundary.

See `docs/NOTE_IR.md` for provider configuration, the normalized JSON contract, free/paid adapter replacement, and acceptance gates.
"""
with (ROOT / "README.md").open("a", encoding="utf-8") as handle:
    handle.write(readme_addition)

notice_addition = """

## Optional Spotify Basic Pitch adapter

The Note IR layer can optionally import `basic-pitch` at runtime or invoke an isolated command wrapper. Basic Pitch is not bundled with this distribution. The upstream source is Copyright 2022 Spotify AB and licensed under Apache License 2.0. Operators must preserve upstream notices and verify the exact installed package, model, and dependency terms.

Upstream project: `spotify/basic-pitch`
"""
with (ROOT / "THIRD_PARTY_NOTICES.md").open("a", encoding="utf-8") as handle:
    handle.write(notice_addition)

env_addition = """

# Optional Note IR command providers. Keep executables absolute and record licenses.
# See docs/NOTE_IR.md and examples/note-provider-config.example.json.
# YUE2_MUSIC_OS_NOTE_PROVIDERS_JSON={}
"""
with (ROOT / ".env.example").open("a", encoding="utf-8") as handle:
    handle.write(env_addition)
