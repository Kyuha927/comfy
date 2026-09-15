from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"


def test_worker_installer_help_is_non_destructive() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPTS / "install_worker.sh"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--accept-noncommercial-model-license" in result.stdout


def test_worker_installer_fails_before_mutation_without_license_ack() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPTS / "install_worker.sh")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "Refusing model setup" in result.stderr


def test_worker_installer_uses_hugging_face_python_api() -> None:
    source = (SCRIPTS / "install_worker.sh").read_text(encoding="utf-8")
    assert source.count("snapshot_download") >= 2
    assert "huggingface-cli" not in source
