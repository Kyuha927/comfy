import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "router" / "promotion_engine.py"


def event(index, gate, outcome="pass", env="unity-6000.2", path="agent->unity->playmode"):
    return {
        "event_id": f"e{index}",
        "record_id": "R1",
        "gate": gate,
        "outcome": outcome,
        "environment": env,
        "execution_path": path,
        "receipt": f"receipt:{index}",
        "observed_at": f"2026-09-13T00:00:{index:02d}+09:00",
    }


class PromotionTests(unittest.TestCase):
    def run_engine(self, rows, *args):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "evidence.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ENGINE), *args, "--evidence", str(path)],
                text=True,
                capture_output=True,
                check=False,
            )

    def complete(self):
        gates = ["reproduction", "repair", "same_path_verification", "rollback", "regression", "receipt"]
        return [event(i + 1, gate) for i, gate in enumerate(gates)]

    def test_complete_same_path_is_promotable(self):
        result = self.run_engine(self.complete(), "assess", "--record-id", "R1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        proposal = json.loads(result.stdout)["proposal"]
        self.assertTrue(proposal["promotable"])
        self.assertEqual(proposal["target_status"], "canonical")
        self.assertEqual(proposal["scope"]["execution_path"], "agent->unity->playmode")

    def test_missing_gate_blocks(self):
        result = self.run_engine(self.complete()[:-1], "assess", "--record-id", "R1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("receipt", json.loads(result.stdout)["proposal"]["missing_gates"])

    def test_latest_failure_blocks(self):
        rows = self.complete() + [event(9, "regression", "fail")]
        result = self.run_engine(rows, "assess", "--record-id", "R1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("regression", json.loads(result.stdout)["proposal"]["failed_gates"])

    def test_mixed_path_blocks(self):
        rows = self.complete()
        rows[-1]["execution_path"] = "different-path"
        result = self.run_engine(rows, "assess", "--record-id", "R1")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["proposal"]["same_execution_path"])

    def test_mixed_environment_blocks(self):
        rows = self.complete()
        rows[-1]["environment"] = "other-env"
        result = self.run_engine(rows, "assess", "--record-id", "R1")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["proposal"]["same_environment"])

    def test_invalid_event_is_rejected(self):
        rows = self.complete()
        rows[0]["receipt"] = ""
        result = self.run_engine(rows, "validate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("receipt must be non-empty", result.stdout)


if __name__ == "__main__":
    unittest.main()
