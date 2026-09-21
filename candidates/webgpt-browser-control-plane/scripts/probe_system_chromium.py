#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbcp.browser_binary import discover_chromium_executable  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = b"<html><body><h1>WBCP network probe</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def read_managed_policy() -> dict[str, Any]:
    candidates = [
        Path("/etc/chromium/policies/managed/000_policy_merge.json"),
        Path("/etc/opt/chrome/policies/managed/000_policy_merge.json"),
    ]
    for path in candidates:
        try:
            if path.is_file():
                return {"path": str(path), "content": json.loads(path.read_text())}
        except Exception as exc:  # noqa: BLE001
            return {"path": str(path), "error": f"{type(exc).__name__}: {exc}"}
    return {"path": None, "content": None}


def main() -> int:
    executable = discover_chromium_executable()
    result: dict[str, Any] = {
        "probe": "system_chromium_loopback_navigation",
        "executable": executable,
        "policy": read_managed_policy(),
        "network_navigation_verified": False,
        "status": "NOT_RUN",
    }
    if not executable:
        result.update(status="BLOCKED_BROWSER_EXECUTABLE_NOT_FOUND")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    try:
        version = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, check=False, timeout=10
        )
        result["version"] = (version.stdout or version.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        result["version_error"] = f"{type(exc).__name__}: {exc}"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        result.update(status="BLOCKED_PLAYWRIGHT_NOT_INSTALLED", error=str(exc))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://localhost:{server.server_port}/"
    result["url"] = url
    try:
        with tempfile.TemporaryDirectory() as td, sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=executable,
            )
            page = browser.new_page()
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=10_000)
                result.update(
                    status="PASS",
                    network_navigation_verified=True,
                    http_status=response.status if response else None,
                    title=page.title(),
                )
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                status = (
                    "BLOCKED_BY_BROWSER_ADMIN_POLICY"
                    if "ERR_BLOCKED_BY_ADMINISTRATOR" in message
                    else "BLOCKED_LIVE_NAVIGATION_FAILED"
                )
                result.update(status=status, error_type=type(exc).__name__, error=message)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["network_navigation_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
