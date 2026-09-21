#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", "__pycache__", ".venv", "artifacts", "validation", "handoffs"}
EXCLUDED_SUFFIXES = {".pyc", ".sqlite3", ".log"}
# Derived manifests and generated receipts are separately verified.  Excluding
# them avoids a hash cycle while keeping the manifest a deterministic source
# package inventory.
EXCLUDED_NAMES = {
    "MANIFEST.sha256",
    "SOURCE_MANIFEST.sha256",
    "PACKAGE_MANIFEST.sha256",
    ".wbcp-oneclick-source.json",
}


def included_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"BLOCKED_PACKAGE_SYMLINK: {path.relative_to(ROOT)}")
        if not path.is_file():
            continue
        resolved = path.resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError(f"BLOCKED_PACKAGE_PATH_ESCAPE: {path}") from exc
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if any(part.endswith(".egg-info") for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        if path.name in EXCLUDED_NAMES:
            continue
        if path.name.startswith(("auth-state", "storage-state")):
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(ROOT).as_posix())


def main() -> int:
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}"
        for path in included_files()
    ]
    output = ROOT / "PACKAGE_MANIFEST.sha256"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = {
        "status": "PASS",
        "manifest": output.name,
        "covered_files": len(lines),
        "manifest_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
