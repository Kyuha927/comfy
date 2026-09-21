#!/usr/bin/env python3
from __future__ import annotations

import compileall
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            env=env,
            check=False,
            timeout=120,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": 124,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "error": "BLOCKED_ACCEPTANCE_SUBPROCESS_TIMEOUT",
        }


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT / "tests")])
    results: dict[str, Any] = {
        "suite": "WBCP_OFFLINE_ACCEPTANCE",
        "status": "RUNNING",
        "production_ready": False,
        "started_at_epoch": time.time(),
        "checks": {},
    }

    json_errors: list[str] = []
    for path in sorted(ROOT.rglob("*.json")):
        if any(part in {"artifacts", "__pycache__"} for part in path.parts):
            continue
        try:
            json.loads(path.read_text())
        except Exception as exc:  # noqa: BLE001
            json_errors.append(f"{path.relative_to(ROOT)}: {type(exc).__name__}: {exc}")
    results["checks"]["json_parse"] = {
        "passed": not json_errors,
        "errors": json_errors,
    }

    compiled = compileall.compile_dir(ROOT / "src", quiet=1, force=True)
    results["checks"]["compileall"] = {"passed": bool(compiled)}

    unit = run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        env=env,
    )
    results["checks"]["unittest"] = unit
    match = re.search(r"Ran (\d+) tests?", unit.get("stderr", ""))
    results["checks"]["unittest"]["test_count"] = int(match.group(1)) if match else None

    doctor_env = dict(env)
    doctor_env["PYTHONPATH"] = str(ROOT / "src")
    results["checks"]["doctor"] = run(
        [sys.executable, "-m", "wbcp.cli", "doctor"], env=doctor_env
    )
    results["checks"]["offline_journey"] = run(
        [sys.executable, "-m", "wbcp.cli", "simulate", "--action", "inspect"],
        env=doctor_env,
    )

    passed = (
        not json_errors
        and compiled
        and unit["exit_code"] == 0
        and results["checks"]["doctor"]["exit_code"] == 0
        and results["checks"]["offline_journey"]["exit_code"] == 0
    )
    results["status"] = "PASS" if passed else "FAIL"
    results["verdict"] = "OFFLINE_ACCEPTED_NOT_PRODUCTION" if passed else "OFFLINE_REJECTED"
    results["finished_at_epoch"] = time.time()

    output = ROOT / "artifacts" / "offline-acceptance.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
