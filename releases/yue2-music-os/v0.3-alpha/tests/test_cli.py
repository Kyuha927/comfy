from __future__ import annotations

import json

from yue2_music_os.__main__ import main


def configure_mock(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("YUE2_MUSIC_OS_ENGINE", "mock")
    monkeypatch.setenv("YUE2_MUSIC_OS_DATA", str(tmp_path / "data"))
    monkeypatch.setenv("YUE2_MUSIC_OS_GPU_WORKERS", "1")
    monkeypatch.delenv("YUE2_MUSIC_OS_API_TOKEN", raising=False)


def test_doctor_cli(monkeypatch, tmp_path, capsys) -> None:
    configure_mock(monkeypatch, tmp_path)
    assert main(["doctor"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["engine"]["engine"] == "mock"


def test_init_demo_cli(monkeypatch, tmp_path, capsys) -> None:
    configure_mock(monkeypatch, tmp_path)
    assert main(["init-demo", "--no-generate", "--name", "CLI Demo"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["project"]["name"] == "CLI Demo"
    assert payload["score"]["kind"] == "score"


def test_non_loopback_server_requires_token(monkeypatch, tmp_path, capsys) -> None:
    configure_mock(monkeypatch, tmp_path)
    assert main(["serve", "--host", "0.0.0.0"]) == 2
    assert "refusing a non-loopback bind" in capsys.readouterr().err


def test_invalid_integer_environment_fails(monkeypatch, tmp_path, capsys) -> None:
    configure_mock(monkeypatch, tmp_path)
    monkeypatch.setenv("YUE2_MUSIC_OS_GPU_WORKERS", "many")
    assert main(["doctor"]) == 2
    assert "must be an integer" in capsys.readouterr().err
