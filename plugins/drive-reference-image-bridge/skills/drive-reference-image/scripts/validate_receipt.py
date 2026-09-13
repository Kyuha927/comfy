#!/usr/bin/env python3
"""Validate an acceptance receipt and enforce PASS_NATIVE truthfulness."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
KNOWN_BLOCKERS = {
    "BLOCKED_SURFACE_NOT_CHAT",
    "BLOCKED_GOOGLE_DRIVE_PLUGIN_UNAVAILABLE",
    "BLOCKED_DRIVE_IMAGE_NOT_FOUND",
    "BLOCKED_DRIVE_IMAGE_AMBIGUOUS",
    "BLOCKED_DRIVE_RAW_FETCH_FAILED",
    "BLOCKED_DRIVE_IMAGE_INVALID_MIME",
    "BLOCKED_IMAGE_TOO_LARGE",
    "BLOCKED_IMAGE_DIMENSIONS_UNSUPPORTED",
    "BLOCKED_IMAGE_DECODE_FAILED",
    "BLOCKED_DRIVE_BYTES_MUTATED",
    "BLOCKED_DRIVE_IMAGE_REFERENCE_BIND_FAILED",
    "BLOCKED_NATIVE_REFERENCE_BIND_UNVERIFIED",
    "BLOCKED_NATIVE_IMAGE_GEN_UNAVAILABLE",
    "BLOCKED_NATIVE_IMAGE_RESULT_NOT_INLINE",
    "BLOCKED_EXTERNAL_API_PROHIBITED",
    "BLOCKED_API_FALLBACK_NOT_CONFIGURED",
    "BLOCKED_AUDIT_EVIDENCE_INCOMPLETE",
}


class ReceiptValidationError(ValueError):
    pass


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_receipt(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "status",
        "surface",
        "source",
        "integrity",
        "reference_bind",
        "native_generation",
        "security",
    }
    _require(required.issubset(receipt), f"missing top-level fields: {sorted(required - receipt.keys())}", errors)
    if errors:
        return errors

    status = receipt["status"]
    surface = receipt["surface"]
    source = receipt["source"]
    integrity = receipt["integrity"]
    bind = receipt["reference_bind"]
    generation = receipt["native_generation"]
    security = receipt["security"]

    _require(receipt["schema_version"] == "1.0", "schema_version must be 1.0", errors)
    _require(status == "PASS_NATIVE" or status in KNOWN_BLOCKERS, "unknown status", errors)

    _require(source.get("provider") == "google-drive", "source provider must be google-drive", errors)
    _require(bool(source.get("file_id")), "source file_id is required", errors)
    _require(bool(source.get("file_name")), "source file_name is required", errors)
    _require(source.get("mime_type") in ALLOWED_MIME, "unsupported source MIME", errors)
    _require(1 <= int(source.get("size_bytes", 0)) <= 20 * 1024 * 1024, "source size outside limits", errors)
    _require(32 <= int(source.get("width", 0)) <= 8192, "source width outside limits", errors)
    _require(32 <= int(source.get("height", 0)) <= 8192, "source height outside limits", errors)

    if integrity.get("verification_available"):
        before = integrity.get("sha256_after_fetch")
        after = integrity.get("sha256_before_bind")
        _require(isinstance(before, str) and bool(SHA256_RE.fullmatch(before)), "invalid sha256_after_fetch", errors)
        _require(isinstance(after, str) and bool(SHA256_RE.fullmatch(after)), "invalid sha256_before_bind", errors)
        _require(before == after, "source digest changed before bind", errors)
        _require(integrity.get("verified") is True, "integrity must be verified when available", errors)

    _require(generation.get("external_api_calls") == 0, "external image API calls must equal zero", errors)
    _require(generation.get("api_fallback_used") is False, "API fallback is prohibited", errors)
    _require(security.get("drive_write_calls") == 0, "Drive write calls are prohibited", errors)
    _require(security.get("sharing_changes") == 0, "Drive sharing changes are prohibited", errors)
    _require(security.get("secrets_exposed") is False, "secrets must not be exposed", errors)
    _require(security.get("raw_pixels_logged") is False, "raw pixels must not be logged", errors)

    if status == "PASS_NATIVE":
        _require(surface.get("kind") == "CHAT", "PASS_NATIVE requires CHAT surface", errors)
        _require(surface.get("native_image_generation_available") is True, "native image generation unavailable", errors)
        _require(source.get("exact_match") is True, "PASS_NATIVE requires exact source match", errors)
        _require(source.get("raw_fetch") is True, "PASS_NATIVE requires raw fetch", errors)
        _require(bind.get("bound") is True, "PASS_NATIVE requires confirmed reference bind", errors)
        _require(bool(bind.get("evidence_id")), "PASS_NATIVE requires bind evidence_id", errors)
        _require(generation.get("generator") == "chatgpt-native-image-generation", "wrong generator", errors)
        _require(generation.get("invoked") is True, "native generator was not invoked", errors)
        _require(int(generation.get("reference_count", 0)) >= 1, "native generator received no image reference", errors)
        _require(generation.get("result_inline") is True, "generated image was not inline", errors)
        _require(receipt.get("error_code") in {None, ""}, "PASS_NATIVE cannot include an error_code", errors)
    else:
        _require(receipt.get("error_code") == status, "blocked receipt error_code must equal status", errors)

    return errors


def load_receipt(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptValidationError(str(exc)) from exc
    if not isinstance(value, dict):
        raise ReceiptValidationError("receipt root must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    try:
        receipt = load_receipt(args.receipt)
        errors = validate_receipt(receipt)
    except ReceiptValidationError as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2))
        return 2

    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
