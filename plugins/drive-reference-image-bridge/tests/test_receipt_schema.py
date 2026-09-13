from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

PLUGIN = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PLUGIN / "skills" / "drive-reference-image" / "references" / "receipt-schema.json"
FIXTURES = Path(__file__).parent / "fixtures"


def test_receipt_schema_is_valid_draft_2020_12() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_receipt_fixtures_conform_to_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for path in sorted(FIXTURES.glob("*.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(receipt), key=lambda error: list(error.path))
        assert errors == [], f"{path.name}: {[error.message for error in errors]}"


def test_canonical_validation_receipt_conforms_to_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    receipt = json.loads((PLUGIN / "validation" / "canonical-source-receipt.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(receipt)
