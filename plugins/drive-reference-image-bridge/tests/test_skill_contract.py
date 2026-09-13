from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parents[1]


def load_validator():
    path = PLUGIN / "scripts" / "validate_plugin.py"
    spec = importlib.util.spec_from_file_location("validate_plugin", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plugin_static_gate() -> None:
    validator = load_validator()
    assert validator.validate(PLUGIN, REPO) == []


def test_manifest_is_skill_only() -> None:
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["skills"] == "./skills/"
    assert "mcpServers" not in manifest
    assert "apps" not in manifest


def test_skill_forbids_api_fallback_and_false_success() -> None:
    skill = (PLUGIN / "skills" / "drive-reference-image" / "SKILL.md").read_text(encoding="utf-8")
    assert "Never use the OpenAI Image API" in skill
    assert "A successful Drive search or download is not a successful reference bind" in skill
    assert "PASS_NATIVE" in skill
    assert "BLOCKED_NATIVE_REFERENCE_BIND_UNVERIFIED" in skill


def test_marketplace_points_inside_repo() -> None:
    marketplace = json.loads((REPO / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    entry = next(item for item in marketplace["plugins"] if item["name"] == "drive-reference-image-bridge")
    assert entry["source"]["source"] == "local"
    assert entry["source"]["path"] == "./plugins/drive-reference-image-bridge"
