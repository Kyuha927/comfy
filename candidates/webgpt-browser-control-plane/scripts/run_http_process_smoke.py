#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def encoded_key(byte: bytes) -> str:
    return "base64:" + base64.b64encode(byte * 32).decode("ascii")


def post_health(port: int, token: str) -> tuple[int, dict[str, Any]]:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "http-process-smoke",
            "method": "tools/call",
            "params": {"name": "browser.health", "arguments": {}},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Origin": "https://chatgpt.com",
            "MCP-Protocol-Version": "2026-07-28",
        },
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        return response.status, json.loads(response.read())


def main() -> int:
    token = "process-smoke-token-" + "x" * 40
    port = free_loopback_port()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="wbcp-http-process-") as tempdir:
        env = dict(os.environ)
        env.update(
            {
                "PYTHONPATH": str(ROOT / "src"),
                "WBCP_DATA_DIR": tempdir,
                "WBCP_ALLOWED_HOSTS": "example.com",
                "WBCP_HOST_SUBJECT": "http-process-smoke-host",
                "WBCP_PERMIT_SIGNING_KEY": encoded_key(b"P"),
                "WBCP_APPROVAL_SIGNING_KEY": encoded_key(b"A"),
                "WBCP_EVIDENCE_HMAC_KEY": encoded_key(b"E"),
                "WBCP_HTTP_BEARER_TOKEN": token,
                "WBCP_HTTP_ALLOWED_HOSTS": "127.0.0.1,localhost",
                "WBCP_HTTP_ALLOWED_ORIGINS": "https://chatgpt.com",
                "WBCP_HTTP_REQUIRE_ORIGIN": "true",
                "WBCP_HTTP_PRINCIPAL_ID": "http-process-smoke-client",
                "WBCP_HTTP_ALLOWED_TOOLS": "browser.health",
                "WBCP_HTTP_REQUESTS_PER_MINUTE": "30",
                "WBCP_HTTP_MAX_CONCURRENT_REQUESTS": "2",
                "WBCP_USE_MOCK_BROWSER": "true",
                "WBCP_R4_MODE": "block",
            }
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "wbcp.cli",
                "serve-http",
                "--bind",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "error",
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        status: int | None = None
        payload: dict[str, Any] | None = None
        error: str | None = None
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                try:
                    status, payload = post_health(port, token)
                    break
                except (ConnectionError, urllib.error.URLError, TimeoutError, OSError):
                    time.sleep(0.1)
            if status != 200 or not payload:
                error = "HTTP process did not return a valid health response"
            else:
                result = payload.get("result", {}).get("structuredContent", {})
                if result.get("status") != "CANDIDATE_NOT_PRODUCTION":
                    error = "Health result did not report CANDIDATE_NOT_PRODUCTION"
        finally:
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=5)

    passed = error is None and status == 200 and process.returncode in {0, -15}
    report = {
        "suite": "WBCP_HTTP_REAL_PROCESS_SMOKE",
        "status": "PASS" if passed else "FAIL",
        "production_ready": False,
        "duration_seconds": round(time.monotonic() - started, 3),
        "http_status": status,
        "response": payload,
        "process_returncode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "error": error,
        "scope": "loopback uvicorn child process; no external network or ChatGPT roundtrip",
    }
    output = ROOT / "artifacts" / "http-process-roundtrip.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
