#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import stat
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


class UnsafeArchiveError(RuntimeError):
    pass


def _safe_member_path(name: str) -> PurePosixPath:
    value = PurePosixPath(name)
    if not name or value.is_absolute() or ".." in value.parts or not value.parts:
        raise UnsafeArchiveError(f"BLOCKED_ARCHIVE_MEMBER_PATH: {name!r}")
    return value


def _prepare_output(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise UnsafeArchiveError("BLOCKED_EXTRACTION_OUTPUT_NOT_DIRECTORY")
        if any(output_dir.iterdir()):
            raise UnsafeArchiveError("BLOCKED_EXTRACTION_OUTPUT_NOT_EMPTY")
    else:
        output_dir.mkdir(parents=True, mode=0o700)


def _validate_root(member: PurePosixPath, expected_root: str | None) -> None:
    if expected_root is not None and member.parts[0] != expected_root:
        raise UnsafeArchiveError(
            f"BLOCKED_ARCHIVE_ROOT_MISMATCH: expected {expected_root!r}, got {member.parts[0]!r}"
        )


def _destination(output_dir: Path, member: PurePosixPath) -> Path:
    destination = output_dir.joinpath(*member.parts)
    try:
        destination.resolve().relative_to(output_dir.resolve())
    except ValueError as exc:
        raise UnsafeArchiveError(f"BLOCKED_ARCHIVE_MEMBER_ESCAPE: {member.as_posix()}") from exc
    return destination


def _extract_tar(archive_path: Path, output_dir: Path, expected_root: str | None) -> int:
    count = 0
    with tarfile.open(archive_path, "r:*") as archive:
        for info in archive.getmembers():
            member = _safe_member_path(info.name)
            _validate_root(member, expected_root)
            if info.issym() or info.islnk() or info.isdev() or info.isfifo():
                raise UnsafeArchiveError(f"BLOCKED_ARCHIVE_SPECIAL_MEMBER: {info.name}")
            destination = _destination(output_dir, member)
            if info.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if not info.isfile():
                raise UnsafeArchiveError(f"BLOCKED_ARCHIVE_UNKNOWN_MEMBER: {info.name}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(info)
            if source is None:
                raise UnsafeArchiveError(f"BLOCKED_ARCHIVE_UNREADABLE_MEMBER: {info.name}")
            with source, destination.open("xb") as target:
                shutil.copyfileobj(source, target)
            destination.chmod(info.mode & 0o777)
            count += 1
    return count


def _zip_is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)


def _extract_zip(archive_path: Path, output_dir: Path, expected_root: str | None) -> int:
    count = 0
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            member = _safe_member_path(info.filename.rstrip("/"))
            _validate_root(member, expected_root)
            if _zip_is_symlink(info):
                raise UnsafeArchiveError(f"BLOCKED_ARCHIVE_SPECIAL_MEMBER: {info.filename}")
            destination = _destination(output_dir, member)
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, destination.open("xb") as target:
                shutil.copyfileobj(source, target)
            mode = (info.external_attr >> 16) & 0o777
            if mode:
                destination.chmod(mode)
            count += 1
    return count


def extract_archive(
    archive_path: Path, output_dir: Path, *, expected_root: str | None = None
) -> dict[str, object]:
    archive_path = archive_path.resolve()
    output_dir = output_dir.resolve()
    _prepare_output(output_dir)
    try:
        if tarfile.is_tarfile(archive_path):
            count = _extract_tar(archive_path, output_dir, expected_root)
            archive_kind = "tar"
        elif zipfile.is_zipfile(archive_path):
            count = _extract_zip(archive_path, output_dir, expected_root)
            archive_kind = "zip"
        else:
            raise UnsafeArchiveError("BLOCKED_ARCHIVE_FORMAT_UNSUPPORTED")
    except Exception:
        # Do not leave a partial extraction that might accidentally be used as
        # source authority.  The caller may inspect the original archive.
        shutil.rmtree(output_dir, ignore_errors=True)
        raise
    return {
        "status": "PASS",
        "archive": str(archive_path),
        "archive_kind": archive_kind,
        "output": str(output_dir),
        "files_extracted": count,
        "expected_root": expected_root,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-root")
    args = parser.parse_args()
    try:
        report = extract_archive(args.archive, args.output, expected_root=args.expected_root)
    except (OSError, UnsafeArchiveError, tarfile.TarError, zipfile.BadZipFile) as exc:
        report = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
