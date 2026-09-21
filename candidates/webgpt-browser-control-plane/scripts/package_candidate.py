#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tarfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", "__pycache__", ".venv", "artifacts", "validation", "handoffs"}
EXCLUDED_SUFFIXES = {".pyc", ".sqlite3", ".log"}
# This provenance marker belongs only to a local OneClick installation.  It
# must never be packaged or published with a portable source candidate.
EXCLUDED_NAMES = {".wbcp-oneclick-source.json"}


def candidate_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return str(data["project"]["version"])


def files() -> list[Path]:
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
        if (
            path.suffix in EXCLUDED_SUFFIXES
            or path.name in EXCLUDED_NAMES
            or path.name.startswith("auth-state")
            or path.name.startswith("storage-state")
        ):
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(ROOT).as_posix())


def build_tar(output: Path, members: list[Path], *, archive_root: str) -> None:
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as archive:
                for path in members:
                    relative = path.relative_to(ROOT).as_posix()
                    info = archive.gettarinfo(str(path), arcname=f"{archive_root}/{relative}")
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    with path.open("rb") as handle:
                        archive.addfile(info, handle)


def build_zip(output: Path, members: list[Path], *, archive_root: str) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in members:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"{archive_root}/{relative}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    members = files()
    version = candidate_version()
    archive_root = f"WBCP_{version}"
    tar_path = output_dir / f"{archive_root}_SOURCE.tar.gz"
    zip_path = output_dir / f"{archive_root}_SOURCE.zip"
    build_tar(tar_path, members, archive_root=archive_root)
    build_zip(zip_path, members, archive_root=archive_root)
    report = {
        "status": "PASS",
        "version": version,
        "file_count": len(members),
        "artifacts": {
            tar_path.name: {"size": tar_path.stat().st_size, "sha256": sha256(tar_path)},
            zip_path.name: {"size": zip_path.stat().st_size, "sha256": sha256(zip_path)},
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
