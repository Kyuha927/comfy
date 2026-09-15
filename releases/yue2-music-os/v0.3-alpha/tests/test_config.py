from __future__ import annotations

from dataclasses import replace

import pytest

from yue2_music_os.config import ConfigurationError


def test_commercial_scope_requires_record(settings) -> None:
    with pytest.raises(ConfigurationError):
        replace(settings, model_use_scope="commercial-licensed").validate()


def test_commercial_scope_accepts_explicit_record(settings) -> None:
    candidate = replace(
        settings,
        model_use_scope="commercial-licensed",
        commercial_license_reference="contract-2026-001",
    )
    candidate.validate()
    candidate.assert_real_engine_allowed()


def test_alpha_rejects_multiple_gpu_workers(settings) -> None:
    with pytest.raises(ConfigurationError):
        replace(settings, gpu_workers=2).validate()


def test_relative_runtime_paths_are_resolved_from_launch_directory(
    monkeypatch, tmp_path
) -> None:
    from yue2_music_os.config import Settings

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("YUE2_MUSIC_OS_YUE2_PYTHON", "runtime/yue2/python")
    monkeypatch.setenv("YUE2_MUSIC_OS_YUE2_REPO", "runtime/yue2/YuE")
    monkeypatch.setenv("YUE2_MUSIC_OS_SHEETSAGE2_PYTHON", "runtime/sheetsage/python")
    monkeypatch.setenv("YUE2_MUSIC_OS_SHEETSAGE2_DIR", "runtime/sheetsage/model")
    resolved = Settings.from_env()
    assert resolved.yue2_python == (tmp_path / "runtime/yue2/python").resolve()
    assert resolved.yue2_repo == (tmp_path / "runtime/yue2/YuE").resolve()
    assert resolved.sheetsage2_python == (tmp_path / "runtime/sheetsage/python").resolve()
    assert resolved.sheetsage2_dir == (tmp_path / "runtime/sheetsage/model").resolve()


def test_relative_optional_base_model_path_is_resolved(monkeypatch, tmp_path) -> None:
    from yue2_music_os.config import Settings

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("YUE2_MUSIC_OS_SHEETSAGE2_BASE_MODEL", "runtime/mert-base")
    resolved = Settings.from_env()
    assert resolved.sheetsage2_base_model == (tmp_path / "runtime/mert-base").resolve()


def test_wildcard_allowed_hosts_require_token(settings) -> None:
    from dataclasses import replace

    with pytest.raises(ConfigurationError, match="wildcard"):
        replace(settings, allowed_hosts=("*",), api_token=None).validate()
    replace(settings, allowed_hosts=("*",), api_token="secret").validate()


def test_allowed_hosts_reject_url_syntax(settings) -> None:
    from dataclasses import replace

    with pytest.raises(ConfigurationError, match="invalid allowed host"):
        replace(settings, allowed_hosts=("https://example.com",)).validate()


def test_command_render_provider_config_is_parsed(monkeypatch, tmp_path) -> None:
    import json
    import sys

    from yue2_music_os.config import Settings

    monkeypatch.setenv(
        "YUE2_MUSIC_OS_RENDER_PROVIDERS_JSON",
        json.dumps(
            {
                "licensed-bridge": {
                    "label": "Licensed bridge",
                    "mode": "command",
                    "argv": [
                        str(__import__("pathlib").Path(sys.executable).resolve()),
                        "adapter.py",
                        "{request_json}",
                        "{output_dir}",
                    ],
                    "commercial_status": "operator-verified",
                    "terms_reference": "contract-001",
                }
            }
        ),
    )
    parsed = Settings.from_env()
    provider = next(
        item for item in parsed.render_providers if item.provider_id == "licensed-bridge"
    )
    assert provider.mode == "command"
    assert provider.commercial_status == "operator-verified"


def test_command_render_provider_rejects_relative_executable(settings) -> None:
    from dataclasses import replace

    from yue2_music_os.config import RenderProviderConfig

    bad = RenderProviderConfig(
        provider_id="bad",
        label="Bad",
        mode="command",
        argv=("python", "adapter.py", "{request_json}", "{output_dir}"),
    )
    with pytest.raises(ConfigurationError, match="absolute executable"):
        replace(settings, render_providers=(bad,)).validate()
