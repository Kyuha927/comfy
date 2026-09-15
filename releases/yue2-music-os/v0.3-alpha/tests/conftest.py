from __future__ import annotations

from pathlib import Path

import pytest

from yue2_music_os.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    runtime = tmp_path / "runtime"
    value = Settings(
        engine="mock",
        data_dir=tmp_path / "data",
        api_token=None,
        allowed_hosts=("localhost", "127.0.0.1", "[::1]", "testserver"),
        max_upload_bytes=4 * 1024 * 1024,
        command_timeout_seconds=10,
        model_use_scope="noncommercial",
        commercial_license_reference=None,
        yue2_python=runtime / "yue2" / "python",
        yue2_repo=runtime / "YuE",
        yue2_model="m-a-p/YuE2-3B",
        yue2_revision=None,
        yue2_vae="m-a-p/YuE2-Vae",
        yue2_vae_revision=None,
        sheetsage2_python=runtime / "sheetsage2" / "python",
        sheetsage2_dir=runtime / "SheetSage2",
        sheetsage2_model="m-a-p/SheetSage2",
        sheetsage2_revision=None,
        sheetsage2_base_model=None,
        gpu_workers=1,
    )
    value.validate()
    return value
