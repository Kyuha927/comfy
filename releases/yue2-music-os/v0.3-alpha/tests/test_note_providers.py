from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from yue2_music_os.note_ir import ProviderTier
from yue2_music_os.note_providers import (
    BasicPitchProvider,
    CommandNoteProvider,
    CommandProviderConfig,
    NoteProviderError,
    NoteProviderRegistry,
    ProviderCapability,
)


def test_basic_pitch_reports_optional_dependency_state():
    info = BasicPitchProvider().info()
    assert info.provider_id == "basic-pitch"
    assert info.tier == ProviderTier.FREE
    assert isinstance(info.ready, bool)


def test_command_provider_uses_normalized_contract(tmp_path: Path):
    script = tmp_path / "provider.py"
    script.write_text(
        """#!/usr/bin/env python3
import json, sys
out = sys.argv[2]
payload = {
  'provider_id': 'free-command',
  'tier': 'free',
  'mode': 'command',
  'tracks': [{'instrument': 'bass', 'polyphonic': False, 'notes': [
    {'pitch_midi': 40, 'start_sec': 0.1, 'end_sec': 0.9, 'velocity': 88, 'confidence': 0.93}
  ]}]
}
open(out, 'w', encoding='utf-8').write(json.dumps(payload))
""",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    source = tmp_path / "source.wav"
    source.write_bytes(b"RIFF-not-real")
    config = CommandProviderConfig(
        provider_id="free-command",
        label="Free command",
        argv=[sys.executable, str(script), "{input}", "{output_json}"],
        capabilities=ProviderCapability(isolated_stem=True, polyphonic=True),
    )
    provider = CommandNoteProvider(config)
    result = provider.transcribe(source_path=source, output_dir=tmp_path / "out", instrument_hint="bass")
    assert result.note_count == 1
    assert result.tracks[0].notes[0].pitch_midi == 40
    assert (tmp_path / "out" / "provider.stdout.log").is_file()


def test_command_provider_rejects_provider_id_mismatch(tmp_path: Path):
    script = tmp_path / "provider.py"
    script.write_text(
        """#!/usr/bin/env python3
import json, sys
open(sys.argv[2], 'w').write(json.dumps({'provider_id':'wrong','tracks':[]}))
""",
        encoding="utf-8",
    )
    source = tmp_path / "source.wav"
    source.write_bytes(b"x")
    provider = CommandNoteProvider(
        CommandProviderConfig(
            provider_id="expected",
            label="Expected",
            argv=[sys.executable, str(script), "{input}", "{output_json}"],
        )
    )
    with pytest.raises(NoteProviderError, match="provider id mismatch"):
        provider.transcribe(source_path=source, output_dir=tmp_path / "out")


def test_registry_parses_free_and_paid_command_slots(monkeypatch, tmp_path: Path):
    definition = {
        "yourmt3-free": {
            "mode": "command",
            "label": "YourMT3 wrapper",
            "tier": "free",
            "argv": [sys.executable, str(tmp_path / "missing.py"), "{input}", "{output_json}"],
            "capabilities": {"full_mix": True, "polyphonic": True},
        },
        "licensed-paid": {
            "mode": "command",
            "label": "Licensed paid wrapper",
            "tier": "paid",
            "argv": [sys.executable, str(tmp_path / "missing-paid.py"), "{input}", "{output_json}"],
        },
    }
    monkeypatch.setenv("YUE2_MUSIC_OS_NOTE_PROVIDERS_JSON", json.dumps(definition))
    registry = NoteProviderRegistry.from_env(default_timeout_seconds=60)
    infos = {info.provider_id: info for info in registry.infos()}
    assert infos["yourmt3-free"].tier == ProviderTier.FREE
    assert infos["licensed-paid"].tier == ProviderTier.PAID
    assert infos["klangio-paid-slot"].ready is False


def test_command_requires_absolute_executable():
    with pytest.raises(ValueError, match="absolute executable"):
        CommandProviderConfig(provider_id="bad", label="Bad", argv=["python", "x.py"])


def test_configured_paid_slot_replaces_disabled_placeholder(monkeypatch, tmp_path: Path):
    definition = {
        "klangio-paid-slot": {
            "mode": "command",
            "label": "Licensed bridge",
            "tier": "paid",
            "argv": [sys.executable, str(tmp_path / "bridge.py"), "{input}", "{output_json}"],
        }
    }
    monkeypatch.setenv("YUE2_MUSIC_OS_NOTE_PROVIDERS_JSON", json.dumps(definition))
    registry = NoteProviderRegistry.from_env(default_timeout_seconds=60)
    matches = [info for info in registry.infos() if info.provider_id == "klangio-paid-slot"]
    assert len(matches) == 1
    assert matches[0].mode == "command"
