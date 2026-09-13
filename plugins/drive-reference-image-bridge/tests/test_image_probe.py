from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from PIL import Image

PLUGIN = Path(__file__).resolve().parents[1]
MODULE_PATH = PLUGIN / "skills" / "drive-reference-image" / "scripts" / "image_probe.py"
SPEC = importlib.util.spec_from_file_location("image_probe", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_valid_png(tmp_path: Path) -> None:
    path = tmp_path / "sample.png"
    Image.new("RGB", (64, 96), "white").save(path)
    result = MODULE.probe_image(path)
    assert result["mime_type"] == "image/png"
    assert result["width"] == 64
    assert result["height"] == 96
    assert result["bytes_modified"] is False


def test_expected_digest_mismatch_is_blocked(tmp_path: Path) -> None:
    path = tmp_path / "sample.png"
    Image.new("RGB", (64, 96), "white").save(path)
    with pytest.raises(MODULE.ProbeError) as caught:
        MODULE.probe_image(path, "0" * 64)
    assert caught.value.code == "BLOCKED_DRIVE_BYTES_MUTATED"


def test_invalid_bytes_are_blocked(tmp_path: Path) -> None:
    path = tmp_path / "fake.png"
    path.write_bytes(b"not an image")
    with pytest.raises(MODULE.ProbeError) as caught:
        MODULE.probe_image(path)
    assert caught.value.code == "BLOCKED_IMAGE_DECODE_FAILED"
