#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECT = [
    "browser-harness",
    "cryptography",
    "httpx",
    "jsonschema",
    "playwright",
    "starlette",
    "uvicorn",
]
EXCLUDED_PARTS = {".git", "__pycache__", ".venv", "artifacts", "validation", "handoffs"}
EXCLUDED_NAMES = {
    "MANIFEST.sha256",
    "SOURCE_MANIFEST.sha256",
    "PACKAGE_MANIFEST.sha256",
    ".wbcp-oneclick-source.json",
}


def candidate_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return str(data["project"]["version"])


def license_info(metadata: importlib.metadata.PackageMetadata) -> dict[str, object]:
    classifiers = [
        value.removeprefix("License :: ")
        for value in metadata.get_all("Classifier", [])
        if value.startswith("License :: ")
    ]
    return {
        "license_field": metadata.get("License") or "UNKNOWN",
        "license_classifiers": classifiers,
    }


def source_paths() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"BLOCKED_SOURCE_SYMLINK: {path.relative_to(ROOT)}")
        if not path.is_file():
            continue
        resolved = path.resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError(f"BLOCKED_SOURCE_PATH_ESCAPE: {path}") from exc
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if any(part.endswith(".egg-info") for part in relative.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix == ".pyc":
            continue
        paths.append(path)
    return sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix())


def main() -> int:
    dependencies: list[dict[str, object]] = []
    lock_lines = [
        "# Candidate direct-dependency pins only.",
        "# This is not a complete hash-locked transitive production lock.",
    ]
    for name in DIRECT:
        try:
            metadata = importlib.metadata.metadata(name)
            version = importlib.metadata.version(name)
            item = {
                "name": name,
                "version": version,
                "status": "INSTALLED",
                "requires": importlib.metadata.requires(name) or [],
                **license_info(metadata),
            }
            lock_lines.append(f"{name}=={version}")
        except importlib.metadata.PackageNotFoundError:
            item = {"name": name, "version": None, "status": "NOT_INSTALLED"}
        dependencies.append(item)

    (ROOT / "requirements-candidate.lock").write_text(
        "\n".join(lock_lines) + "\n", encoding="utf-8"
    )
    manifest_lines: list[str] = []
    for path in source_paths():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    manifest_text = "\n".join(manifest_lines) + "\n"
    # These are two compatibility names for the same source inventory.  Each
    # is intentionally excluded from the inventory to avoid self-hashing.
    (ROOT / "SOURCE_MANIFEST.sha256").write_text(manifest_text, encoding="utf-8")
    (ROOT / "MANIFEST.sha256").write_text(manifest_text, encoding="utf-8")

    inventory = {
        "candidate": "webgpt-browser-control-plane",
        "version": candidate_version(),
        "generated_at_epoch": time.time(),
        "dependencies": dependencies,
        "limitations": [
            "Direct dependencies only",
            "No vulnerability adjudication",
            "No legal license approval",
            "No wheel hashes or complete transitive lock",
        ],
    }
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "dependency-license-inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    provenance = {
        "candidate": "webgpt-browser-control-plane",
        "version": candidate_version(),
        "generated_at_epoch": time.time(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "source_file_count": len(manifest_lines),
        "source_manifest_sha256": hashlib.sha256(manifest_text.encode()).hexdigest(),
        "builder": "current isolated validation container",
        "signed": False,
        "production_ready": False,
        "limitations": [
            "Local candidate provenance only",
            "No trusted remote builder identity",
            "No SLSA attestation or external signature",
        ],
    }
    (artifacts / "provenance-candidate.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "PASS_CANDIDATE_ONLY",
                "dependencies": len(dependencies),
                "source_files": len(manifest_lines),
                "source_manifest_sha256": provenance["source_manifest_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
