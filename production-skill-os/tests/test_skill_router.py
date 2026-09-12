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
    def run_router(self, *args, catalog=None):
        return subprocess.run(
            [sys.executable, str(ROUTER), "--catalog", str(catalog or CATALOG), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_catalog_validates(self):
        result = self.run_router("validate")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_advisory_not_default(self):
        result = self.run_router(
            "lookup",
            "--domain",
            "unity",
            "--text",
            "skinned mesh frozen using AnimationMode SampleAnimationClip offscreen",
        )
        self.assertEqual(result.returncode, 2)

    def test_advisory_inspect_no_auto(self):
        result = self.run_router(
            "lookup",
            "--include-advisory",
            "--domain",
            "unity",
            "--text",
            "skinned mesh frozen using AnimationMode SampleAnimationClip offscreen",
        )
        payload = json.loads(result.stdout)
        self.assertFalse(payload["auto_execute_allowed"])
        self.assertTrue(payload["escalate"])

    def test_exact_error_code_wins(self):
        result = self.run_router(
            "lookup",
            "--include-advisory",
            "--domain",
            "blender_bridge",
            "--error-code",
            "HTTP_429",
            "--text",
            "MCP SSE probe returned 429",
        )
        self.assertIn("exact_error_code", json.loads(result.stdout)["route"]["route_reasons"])

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "catalog.jsonl"
            first = CATALOG.read_text(encoding="utf-8").splitlines()[0]
            path.write_text(first + "\n" + first + "\n", encoding="utf-8")
            result = self.run_router("validate", catalog=path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate id", result.stdout)

    def test_duplicate_fingerprint_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "catalog.jsonl"
            first = json.loads(CATALOG.read_text(encoding="utf-8").splitlines()[0])
            second = dict(first)
            second["id"] = "OTHER"
            path.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")
            result = self.run_router("validate", catalog=path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate fingerprint", result.stdout)

    def test_canonical_requires_scope(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "catalog.jsonl"
            first = json.loads(CATALOG.read_text(encoding="utf-8").splitlines()[0])
            first["status"] = "canonical"
            path.write_text(json.dumps(first) + "\n", encoding="utf-8")
            result = self.run_router("validate", catalog=path)
            self.assertEqual(result.returncode, 1)
            self.assertIn("requires non-empty scope", result.stdout)


if __name__ == "__main__":
    unittest.main()
