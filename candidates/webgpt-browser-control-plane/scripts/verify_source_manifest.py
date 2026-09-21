#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="MANIFEST.sha256")
    args = parser.parse_args()
    manifest_path = (ROOT / args.manifest).resolve()
    try:
        manifest_path.relative_to(ROOT.resolve())
    except ValueError:
        print(json.dumps({"status": "FAIL", "error": "MANIFEST_PATH_ESCAPE"}))
        return 1
    if not manifest_path.is_file():
        print(json.dumps({"status": "FAIL", "error": "MANIFEST_MISSING"}))
        return 1

    mismatches: list[dict[str, str]] = []
    verified = 0
    for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            expected, relative = line.split("  ", 1)
        except ValueError:
            mismatches.append({"line": str(line_number), "error": "MALFORMED_ENTRY"})
            continue
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            mismatches.append({"line": str(line_number), "error": "INVALID_SHA256"})
            continue
        path = (ROOT / relative).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError:
            mismatches.append({"path": relative, "error": "PATH_ESCAPE"})
            continue
        if not path.is_file():
            mismatches.append({"path": relative, "error": "MISSING"})
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            mismatches.append(
                {"path": relative, "error": "HASH_MISMATCH", "expected": expected, "actual": actual}
            )
        else:
            verified += 1
    report = {
        "status": "PASS" if not mismatches else "FAIL",
        "manifest": str(manifest_path.relative_to(ROOT)),
        "verified_files": verified,
        "mismatches": mismatches,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
