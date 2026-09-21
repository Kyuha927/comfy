from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wbcp.checkpoints import generate_keypair, sign_ledger_checkpoint, verify_checkpoint
from wbcp.evidence import EvidenceLedger


class CheckpointTests(unittest.TestCase):
    def test_checkpoint_signs_exact_verified_evidence_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger = EvidenceLedger(root / "evidence.jsonl", hmac_key=b"E" * 32)
            ledger.append("TEST", "job-1", {"status": "SUCCEEDED"})
            keys = generate_keypair(root / "checkpoint.pem", root / "checkpoint.pub.pem")
            checkpoint = sign_ledger_checkpoint(
                ledger,
                private_key_path=keys["private_key"],
                output_path=root / "checkpoint.json",
                instance_id="candidate-test",
            )
            result = verify_checkpoint(
                root / "checkpoint.json", public_key_path=keys["public_key"]
            )
            self.assertTrue(result["valid"], result)
            self.assertEqual(result["root_hash"], ledger.root_hash())
            self.assertEqual(result["event_count"], checkpoint["event_count"])

    def test_checkpoint_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger = EvidenceLedger(root / "evidence.jsonl", hmac_key=b"E" * 32)
            ledger.append("TEST", "job-1", {"status": "SUCCEEDED"})
            keys = generate_keypair(root / "checkpoint.pem", root / "checkpoint.pub.pem")
            path = root / "checkpoint.json"
            sign_ledger_checkpoint(
                ledger,
                private_key_path=keys["private_key"],
                output_path=path,
                instance_id="candidate-test",
            )
            data = json.loads(path.read_text())
            data["event_count"] += 1
            path.write_text(json.dumps(data))
            result = verify_checkpoint(path, public_key_path=keys["public_key"])
            self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main()
