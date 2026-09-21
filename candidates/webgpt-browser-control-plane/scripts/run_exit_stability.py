#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def one_run(
    index: int, timeout_seconds: float, expected_tests: int | None
) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT / "tests")])
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*.py",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        elapsed = round(time.monotonic() - started, 3)
        combined = completed.stdout + "\n" + completed.stderr
        match = re.search(r"Ran (\d+) tests? in ([0-9.]+)s", combined)
        test_count = int(match.group(1)) if match else None
        runner_seconds = float(match.group(2)) if match else None
        passed = (
            completed.returncode == 0
            and test_count is not None
            and (expected_tests is None or test_count == expected_tests)
            and bool(re.search(r"(?:^|\n)OK\s*$", combined.rstrip()))
        )
        return {
            "run": index,
            "status": "PASS" if passed else "FAIL",
            "exit_code": completed.returncode,
            "elapsed_seconds": elapsed,
            "runner_seconds": runner_seconds,
            "test_count": test_count,
            "stderr_tail": "\n".join(completed.stderr.splitlines()[-12:]),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "run": index,
            "status": "FAIL",
            "exit_code": 124,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "test_count": None,
            "error": "BLOCKED_TEST_PROCESS_EXIT_TIMEOUT",
            "stdout_tail": "\n".join((exc.stdout or "").splitlines()[-12:]),
            "stderr_tail": "\n".join((exc.stderr or "").splitlines()[-12:]),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument(
        "--expected-tests",
        type=int,
        default=None,
        help="Optional explicit expected count. Omit to establish it from the first passing run.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument(
        "--output", default=str(ROOT / "artifacts" / "repeated-suite-10x.json")
    )
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()
    if args.runs < 1 or args.runs > 100:
        raise SystemExit("runs must be between 1 and 100")
    if args.timeout_seconds <= 0 or args.timeout_seconds > 300:
        raise SystemExit("timeout-seconds must be between 0 and 300")

    output = Path(args.output).resolve()
    prior: list[dict[str, Any]] = []
    if args.append and output.exists():
        loaded = json.loads(output.read_text(encoding="utf-8"))
        prior = list(loaded.get("runs", []))

    expected_tests = args.expected_tests
    if expected_tests is None and prior:
        prior_count = next(
            (
                int(item["test_count"])
                for item in prior
                if item.get("status") == "PASS" and isinstance(item.get("test_count"), int)
            ),
            None,
        )
        expected_tests = prior_count

    new_runs: list[dict[str, Any]] = []
    for number in range(1, args.runs + 1):
        run = one_run(args.offset + number, args.timeout_seconds, expected_tests)
        new_runs.append(run)
        if expected_tests is None and run.get("status") == "PASS":
            count = run.get("test_count")
            if isinstance(count, int):
                expected_tests = count
    merged_by_index = {int(item["run"]): item for item in prior + new_runs}
    runs = [merged_by_index[index] for index in sorted(merged_by_index)]
    passed = bool(runs) and expected_tests is not None and all(
        item.get("status") == "PASS" and item.get("test_count") == expected_tests
        for item in runs
    )
    report = {
        "suite": "WBCP_REPEATED_FULL_SUITE_EXIT_STABILITY",
        "status": "PASS" if passed else "FAIL",
        "expected_tests_per_run": expected_tests,
        "expected_tests_source": (
            "explicit_argument" if args.expected_tests is not None else "first_passing_run"
        ),
        "run_count": len(runs),
        "total_tests": sum(int(item.get("test_count") or 0) for item in runs),
        "runs": runs,
        "note": "Every run is an independent Python process with a hard exit timeout.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
