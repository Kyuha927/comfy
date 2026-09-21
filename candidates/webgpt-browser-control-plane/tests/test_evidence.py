from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wbcp.evidence import EvidenceLedger


class EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.path = Path(self.td.name) / "evidence.jsonl"
        self.ledger = EvidenceLedger(self.path, hmac_key=b"E" * 32)

    def tearDown(self) -> None:
        self.td.cleanup()

    def test_hash_chain_verifies(self) -> None:
        self.ledger.append("ONE", "job", {"value": 1})
        self.ledger.append("TWO", "job", {"value": 2})
        result = self.ledger.verify()
        self.assertTrue(result.valid)
        self.assertEqual(result.event_count, 2)
        self.assertNotEqual(result.root_hash, "0" * 64)

    def test_secrets_are_redacted_before_commit(self) -> None:
        self.ledger.append(
            "SECRET_TEST",
            "job",
            {
                "password": "never-store-me",
                "Authorization": "Bearer abcdefghijklmnopqrstuvwxyz123456",
                "safe": "visible",
            },
        )
        raw = self.path.read_text()
        self.assertNotIn("never-store-me", raw)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", raw)
        event = json.loads(raw)
        self.assertEqual(event["payload"]["password"], "[REDACTED]")
        self.assertEqual(event["payload"]["safe"], "visible")

    def test_public_hashes_and_revisions_remain_verifiable(self) -> None:
        digest = "a" * 64
        revision = "b" * 64
        self.ledger.append(
            "HASH_TEST",
            "job",
            {"action_digest": digest, "screenshot_digest": revision},
        )
        event = json.loads(self.path.read_text())
        self.assertEqual(event["payload"]["action_digest"], digest)
        self.assertEqual(event["payload"]["screenshot_digest"], revision)
        self.assertTrue(self.ledger.verify().valid)

    def test_tampering_is_detected(self) -> None:
        self.ledger.append("ONE", "job", {"value": 1})
        event = json.loads(self.path.read_text())
        event["payload"]["value"] = 999
        self.path.write_text(json.dumps(event) + "\n")
        result = self.ledger.verify()
        self.assertFalse(result.valid)
        self.assertIn("hash mismatch", result.error or "")

    def test_root_changes_when_new_event_is_added(self) -> None:
        self.ledger.append("ONE", "job", {})
        first = self.ledger.root_hash()
        self.ledger.append("TWO", "job", {})
        second = self.ledger.root_hash()
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
