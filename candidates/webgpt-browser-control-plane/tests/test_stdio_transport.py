from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class StdioTransportTests(unittest.TestCase):
    def test_stdio_initialize_and_tools_list(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            key = base64.b64encode(b"K" * 32).decode("ascii")
            env = {
                **os.environ,
                "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
                "WBCP_DATA_DIR": td,
                "WBCP_ALLOWED_HOSTS": "example.com",
                "WBCP_HOST_SUBJECT": "stdio-test-host",
                "WBCP_PERMIT_SIGNING_KEY": "base64:" + key,
                "WBCP_APPROVAL_SIGNING_KEY": "base64:" + key,
                "WBCP_EVIDENCE_HMAC_KEY": "base64:" + key,
                "WBCP_USE_MOCK_BROWSER": "true",
            }
            requests = [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2025-11-25"},
                },
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            ]
            process = subprocess.run(
                [sys.executable, "-m", "wbcp.cli", "serve-stdio"],
                input="".join(json.dumps(item) + "\n" for item in requests),
                text=True,
                capture_output=True,
                env=env,
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                timeout=15,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            lines = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
            self.assertEqual([line["id"] for line in lines], [1, 2])
            self.assertGreater(len(lines[1]["result"]["tools"]), 5)
            self.assertEqual(process.stderr, "")

    def test_stdio_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            key = base64.b64encode(b"K" * 32).decode("ascii")
            env = {
                **os.environ,
                "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
                "WBCP_DATA_DIR": td,
                "WBCP_ALLOWED_HOSTS": "example.com",
                "WBCP_HOST_SUBJECT": "stdio-test-host",
                "WBCP_PERMIT_SIGNING_KEY": "base64:" + key,
                "WBCP_APPROVAL_SIGNING_KEY": "base64:" + key,
                "WBCP_EVIDENCE_HMAC_KEY": "base64:" + key,
                "WBCP_USE_MOCK_BROWSER": "true",
            }
            process = subprocess.run(
                [sys.executable, "-m", "wbcp.cli", "serve-stdio"],
                input='{"jsonrpc":"2.0","id":1,"method":"ping","method":"tools/list"}\n',
                text=True,
                capture_output=True,
                env=env,
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                timeout=15,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            response = json.loads(process.stdout.strip())
            self.assertEqual(response["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()
