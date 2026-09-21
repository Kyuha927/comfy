#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "ENGINE_SOURCES.lock.json"
EXPECTED_JEV_COMMIT = "1231850a0bf1a0c0341fe408ef1668dbbfdfac46"
EXPECTED_JEV_TREE = "987b481ed8ef400911ca471bce38c7adfdabc45c"
EXPECTED_HARNESS_SHA256 = "2491459e4bfc0ee8aea22dc6c4680fc0f791b7ba553446323c50d2883449d769"
EXPECTED_CUA_MINIMUM = "0.28.2"
EXPECTED_CUA_OPERATIONS = [
    "SNAPSHOT",
    "NAVIGATE",
    "CLICK",
    "TYPE_TEXT",
    "SELECT",
    "SCROLL",
    "WAIT",
]


def read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def git_value(path: Path, expression: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", expression],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git rev-parse {expression} failed")
    return result.stdout.strip()


def check_equal(errors: list[str], name: str, actual: object, expected: object) -> None:
    if actual != expected:
        errors.append(f"{name}: expected {expected!r}, got {actual!r}")


def validate_lock(lock: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    project = read_toml(ROOT / "pyproject.toml")["project"]
    check_equal(errors, "schema_version", lock.get("schema_version"), 1)
    check_equal(errors, "candidate_version", lock.get("candidate_version"), project["version"])
    jev = lock.get("jev", {})
    check_equal(errors, "jev.package", jev.get("package"), "jev-ultrafast")
    check_equal(errors, "jev.version", jev.get("version"), "0.1.0")
    check_equal(errors, "jev.commit", jev.get("commit"), EXPECTED_JEV_COMMIT)
    check_equal(errors, "jev.tree", jev.get("tree"), EXPECTED_JEV_TREE)
    check_equal(errors, "jev.requires_python", jev.get("requires_python"), ">=3.12")
    harness = jev.get("browser_harness", {})
    check_equal(errors, "browser_harness.version", harness.get("version"), "0.1.13")
    check_equal(errors, "browser_harness.wheel_sha256", harness.get("wheel_sha256"), EXPECTED_HARNESS_SHA256)
    extras = project.get("optional-dependencies", {}).get("jev", [])
    if "browser-harness==0.1.13" not in extras:
        errors.append("pyproject optional Jev extra must pin browser-harness==0.1.13")
    cua = lock.get("cua", {})
    check_equal(errors, "cua.minimum_validated_reference", cua.get("minimum_validated_reference"), EXPECTED_CUA_MINIMUM)
    check_equal(errors, "cua.bounded_mode_required", cua.get("bounded_mode_required"), True)
    check_equal(errors, "cua.typed_operation_allowlist", cua.get("typed_operation_allowlist"), EXPECTED_CUA_OPERATIONS)
    return errors


def validate_jev_source(path: Path, lock: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not path.is_dir():
        return [f"Jev source path is not a directory: {path}"]
    try:
        check_equal(errors, "source.commit", git_value(path, "HEAD^{commit}"), lock["jev"]["commit"])
        check_equal(errors, "source.tree", git_value(path, "HEAD^{tree}"), lock["jev"]["tree"])
    except RuntimeError as exc:
        errors.append(str(exc))
        return errors
    pyproject = path / "pyproject.toml"
    if not pyproject.is_file():
        return errors + ["Jev source pyproject.toml is missing"]
    project = read_toml(pyproject).get("project", {})
    check_equal(errors, "source.project.name", project.get("name"), lock["jev"]["package"])
    check_equal(errors, "source.project.version", project.get("version"), lock["jev"]["version"])
    check_equal(errors, "source.project.requires-python", project.get("requires-python"), lock["jev"]["requires_python"])
    dependencies = project.get("dependencies", [])
    if "browser-harness==0.1.13" not in dependencies:
        errors.append("Jev source dependencies do not contain browser-harness==0.1.13")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jev-source", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"ENGINE_SOURCES.lock.json unreadable: {type(exc).__name__}: {exc}")
        lock = {}
    if lock:
        errors.extend(validate_lock(lock))
    source_mode = "LOCK_ONLY"
    if args.jev_source is not None and lock:
        source_mode = "SOURCE_VERIFIED"
        errors.extend(validate_jev_source(args.jev_source.resolve(), lock))
    report = {
        "suite": "WBCP_ENGINE_SOURCE_LOCK",
        "status": ("PASS_" + source_mode) if not errors else "FAIL",
        "source_mode": source_mode,
        "lock": LOCK_PATH.name,
        "jev_source": str(args.jev_source.resolve()) if args.jev_source else None,
        "errors": errors,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
