from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "drive-reference-image" / "scripts" / "validate_receipt.py"
SPEC = importlib.util.spec_from_file_location("validate_receipt", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture(name: str) -> dict:
    return json.loads((Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8"))


def test_synthetic_native_pass_is_valid() -> None:
    assert MODULE.validate_receipt(fixture("pass_native.synthetic.json")) == []


def test_real_fetch_only_blocked_receipt_is_valid_and_not_pass() -> None:
    receipt = fixture("fetch_only.blocked.json")
    assert receipt["status"] != "PASS_NATIVE"
    assert MODULE.validate_receipt(receipt) == []


def test_fetch_only_cannot_claim_pass_native() -> None:
    receipt = fixture("fetch_only.blocked.json")
    receipt["status"] = "PASS_NATIVE"
    receipt["error_code"] = None
    errors = MODULE.validate_receipt(receipt)
    assert any("reference bind" in error for error in errors)
    assert any("not invoked" in error for error in errors)
    assert any("not inline" in error for error in errors)


def test_api_fallback_invalidates_pass() -> None:
    receipt = fixture("pass_native.synthetic.json")
    receipt["native_generation"]["api_fallback_used"] = True
    receipt["native_generation"]["external_api_calls"] = 1
    errors = MODULE.validate_receipt(receipt)
    assert any("external image API" in error for error in errors)
    assert any("fallback" in error for error in errors)


def test_digest_mutation_invalidates_receipt() -> None:
    receipt = copy.deepcopy(fixture("pass_native.synthetic.json"))
    receipt["integrity"]["sha256_before_bind"] = "b" * 64
    errors = MODULE.validate_receipt(receipt)
    assert "source digest changed before bind" in errors
