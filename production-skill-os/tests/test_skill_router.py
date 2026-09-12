import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "router" / "skill_router.py"
CATALOG = ROOT / "router" / "failure_catalog.jsonl"


class SkillRouterTests(unittest.TestCase):
    def run_router(self, *args):
        return subprocess.run(
            [sys.executable, str(ROUTER), "--catalog", str(CATALOG), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_catalog_validates(self):
        result = self.run_router("validate")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_advisory_is_not_selected_by_default(self):
        result = self.run_router(
            "lookup", "--domain", "unity", "--text", "skinned mesh frozen using AnimationMode SampleAnimationClip offscreen"
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["route"], "NOVEL_OR_UNVERIFIED")

    def test_advisory_can_be_inspected_but_not_auto_executed(self):
        result = self.run_router(
            "lookup", "--include-advisory", "--domain", "unity",
            "--text", "skinned mesh frozen using AnimationMode SampleAnimationClip offscreen"
        )
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["route"]["id"], "UNITY_SKINNED_MESH_FROZEN_OFFSCREEN_SAMPLE")
        self.assertFalse(payload["auto_execute_allowed"])
        self.assertTrue(payload["escalate"])

    def test_exact_error_code_wins(self):
        result = self.run_router(
            "lookup", "--include-advisory", "--domain", "blender_bridge",
            "--error-code", "HTTP_429", "--text", "MCP SSE probe returned 429"
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["route"]["id"], "BLENDER_BRIDGE_SSE_429")
        self.assertIn("exact_error_code", payload["route"]["route_reasons"])

    def test_duplicate_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.jsonl"
            first = json.loads(CATALOG.read_text(encoding="utf-8").splitlines()[0])
            bad.write_text(json.dumps(first) + "\n" + json.dumps(first) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROUTER), "--catalog", str(bad), "validate"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate id", result.stdout)


if __name__ == "__main__":
    unittest.main()
