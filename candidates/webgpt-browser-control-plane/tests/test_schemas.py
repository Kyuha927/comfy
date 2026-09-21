from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from wbcp.models import ActionReceipt, ActionRequest, JobState, RiskTier
from wbcp.permits import PermitAuthority, PermitRegistry

ROOT = Path(__file__).resolve().parents[1]


class SchemaTests(unittest.TestCase):
    def load(self, name: str) -> dict:
        schema = json.loads((ROOT / "schemas" / name).read_text())
        Draft202012Validator.check_schema(schema)
        return schema

    def test_action_request_example_matches_schema(self) -> None:
        schema = self.load("action-request.schema.json")
        value = ActionRequest(
            session_id="schema-session",
            idempotency_key="schema-action",
            action_type="navigate",
            target_url="https://example.com/",
            payload={},
            expected={},
        ).to_dict()
        Draft202012Validator(schema).validate(value)

    def test_permit_claims_match_schema(self) -> None:
        schema = self.load("permit.schema.json")
        with tempfile.TemporaryDirectory() as td:
            registry = PermitRegistry(str(Path(td) / "permits.sqlite3"))
            authority = PermitAuthority(b"P" * 32, registry)
            token = authority.issue(
                subject="host",
                session_id="schema-session",
                allowed_actions=["navigate"],
                exact_hosts=["example.com"],
                risk_ceiling=RiskTier.R1_LOCAL_REVERSIBLE,
                max_calls=1,
            )
            claims = authority.codec.decode(token, expected_kind="permit")
            Draft202012Validator(schema).validate(claims)
            registry.close()

    def test_terminal_receipt_matches_schema(self) -> None:
        schema = self.load("receipt.schema.json")
        receipt = ActionReceipt(
            job_id="123e4567-e89b-42d3-a456-426614174000",
            state=JobState.SUCCEEDED,
            risk=RiskTier.R1_LOCAL_REVERSIBLE,
            action_digest="a" * 64,
            evidence_root="b" * 64,
            result={},
        )
        Draft202012Validator(schema).validate(receipt.to_dict())


if __name__ == "__main__":
    unittest.main()
