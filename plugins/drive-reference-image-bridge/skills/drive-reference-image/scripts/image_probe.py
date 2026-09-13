#!/usr/bin/env python3
"""Deterministically inspect an image without modifying it."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

MAX_BYTES = 20 * 1024 * 1024
MIN_DIMENSION = 32
MAX_DIMENSION = 8192
ALLOWED_FORMATS = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}


class ProbeError(ValueError):
    """Image validation failure with a stable product error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_image(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise ProbeError("BLOCKED_DRIVE_RAW_FETCH_FAILED", f"File not found: {path}")

    size = path.stat().st_size
    if size < 1:
        raise ProbeError("BLOCKED_IMAGE_DECODE_FAILED", "Image file is empty")
    if size > MAX_BYTES:
        raise ProbeError("BLOCKED_IMAGE_TOO_LARGE", f"Image is {size} bytes")

    digest = sha256_file(path)
    if expected_sha256 and digest.lower() != expected_sha256.lower():
        raise ProbeError(
            "BLOCKED_DRIVE_BYTES_MUTATED",
            f"SHA-256 mismatch: expected {expected_sha256.lower()}, got {digest}",
        )

    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image_format = (image.format or "").upper()
            width, height = image.size
            mode = image.mode
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ProbeError("BLOCKED_IMAGE_DECODE_FAILED", str(exc)) from exc

    mime = ALLOWED_FORMATS.get(image_format)
    if mime is None:
        raise ProbeError(
            "BLOCKED_DRIVE_IMAGE_INVALID_MIME",
            f"Unsupported decoded image format: {image_format or 'unknown'}",
        )

    guessed_mime, _ = mimetypes.guess_type(path.name)
    extension_mime_match = guessed_mime in {None, mime}
    if not extension_mime_match:
        raise ProbeError(
            "BLOCKED_DRIVE_IMAGE_INVALID_MIME",
            f"Extension implies {guessed_mime}, decoded bytes are {mime}",
        )

    if not (MIN_DIMENSION <= width <= MAX_DIMENSION and MIN_DIMENSION <= height <= MAX_DIMENSION):
        raise ProbeError(
            "BLOCKED_IMAGE_DIMENSIONS_UNSUPPORTED",
            f"Unsupported dimensions: {width}x{height}",
        )

    return {
        "file_name": path.name,
        "mime_type": mime,
        "size_bytes": size,
        "width": width,
        "height": height,
        "mode": mode,
        "sha256": digest,
        "bytes_modified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        result = {"status": "PASS", "probe": probe_image(args.path, args.expected_sha256)}
        exit_code = 0
    except ProbeError as exc:
        result = {"status": exc.code, "error": exc.message}
        exit_code = 2

    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
