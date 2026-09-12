import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "adapters" / "route_packet.py"
CATALOG = ROOT / "router" / "failure_catalog.jsonl"


class RoutePacketTests(unittest.TestCase):
    def run_adapter(self, event, *extra):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "event.json"
            path.write_text(json.dumps(event), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ADAPTER), "--event", str(path), "--catalog", str(CATALOG), *extra],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_unknown_is_small_novelty_packet(self):
        result = self.run_adapter(
            {
                "domain": "unity",
                "error_code": "X",
                "message": "never seen",
                "environment": "e",
                "execution_path": "p",
            }
        )
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["escalate"])
        self.assertIn("novelty_packet", payload)

    def test_advisory_packet_stays_non_auto(self):
        result = self.run_adapter(
            {"domain": "unity", "message": "skinned mesh frozen AnimationMode offscreen"},
            "--include-advisory",
        )
        payload = json.loads(result.stdout)
        self.assertFalse(payload["auto_execute_allowed"])
        self.assertTrue(payload["escalate"])


if __name__ == "__main__":
    unittest.main()
