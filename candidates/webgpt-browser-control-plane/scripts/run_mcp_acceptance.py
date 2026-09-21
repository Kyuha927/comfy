#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str]) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT / "tests")])
    started = time.monotonic()
    process = subprocess.run(
        [sys.executable, "-m", "unittest", *args, "-v"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    return {
        "exit_code": process.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def main() -> int:
    result = run(
        [
            "tests.test_mcp_protocol",
            "tests.test_mcp_http",
            "tests.test_stdio_transport",
            "tests.test_settings_and_sessions",
            "tests.test_restart_recovery",
            "tests.test_checkpoints",
            "tests.test_playwright_route_regression",
            "tests.test_engine_boundaries",
        ]
    )
    report = {
        "suite": "WBCP_MCP_TRANSPORT_ACCEPTANCE",
        "generated_at_epoch": time.time(),
        "status": "PASS" if result["exit_code"] == 0 else "FAIL",
        "production_ready": False,
        "result": result,
        "scope": [
            "legacy MCP initialize",
            "2026 server/discover",
            "tools/list and typed tools/call",
            "stdio newline-delimited JSON-RPC",
            "authenticated Streamable HTTP POST",
            "Host and Origin allowlists",
            "protocol and request-size fail-closed gates",
            "transport principal tool allowlist",
            "authenticated request rate limit",
            "finite session permits",
            "one-shot consequential approval",
            "durable restart recovery",
            "Ed25519 evidence checkpoints",
            "Jev/CUA default-deny, binding, independent-verifier, and reconciliation boundaries",
        ],
    }
    output = ROOT / "artifacts" / "mcp-transport-acceptance.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
