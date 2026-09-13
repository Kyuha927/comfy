import copy
import importlib.util
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "tool-intake" / "TOOL_CAPABILITY_REGISTRY.json"
CONTRACT_PATH = ROOT / "tool-intake" / "SELECTION_CONTRACT.json"
MODULE_PATH = ROOT / "router" / "capability_guard.py"
spec = importlib.util.spec_from_file_location("capability_guard", MODULE_PATH)
guard = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(guard)


def load_registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def refresh_summary(registry):
    counts = Counter(record["status"] for record in registry["records"])
    registry["summary"] = {
        "records": len(registry["records"]),
        "verified_for_lin_3d": counts["VERIFIED_FOR_LIN_3D"],
        "absorbed_generic": counts["ABSORBED_GENERIC"],
        "lin_3d_test_required": counts["LIN_3D_TEST_REQUIRED"],
        "blocked": counts["BLOCKED"],
        "superseded": counts["SUPERSEDED"],
    }


class CapabilityGuardTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()
        self.contract = load_contract()
        self.head = self.contract["authority"]["branch_head_at_reconciliation"]

    def test_real_registry_and_contract_are_valid_and_have_zero_final_capabilities(self):
        self.assertEqual([], guard.validate_registry(self.registry))
        self.assertEqual([], guard.validate_contract(self.registry, self.contract))
        self.assertEqual(40, self.registry["summary"]["records"])
        self.assertEqual(0, self.registry["summary"]["verified_for_lin_3d"])

    def test_generic_internal_guard_is_allowed_only_at_exact_version(self):
        allowed = guard.authorize(
            self.registry,
            contract=self.contract,
            capability_id="cap.production_skill_os.fail_closed_selection",
            requested_version="1.0.0-candidate.20260914",
            scope="GENERIC_PRODUCTION",
            lin_authority_head="",
        )
        self.assertTrue(allowed["ok"])
        self.assertFalse(allowed["canon_promotion_allowed"])

        denied = guard.authorize(
            self.registry,
            contract=self.contract,
            capability_id="cap.production_skill_os.fail_closed_selection",
            requested_version="latest",
            scope="GENERIC_PRODUCTION",
            lin_authority_head="",
        )
        self.assertEqual("BLOCKED_VERSION_MISMATCH", denied["code"])

    def test_h31_head_is_denied_from_final_path(self):
        denied = guard.authorize(
            self.registry,
            contract=self.contract,
            capability_id="cap.tripo.h31.head_component_ultra",
            requested_version="v3.1-20260211",
            scope="LIN_3D_FINAL",
            lin_authority_head=self.head,
        )
        self.assertEqual("BLOCKED_CAPABILITY_NOT_VERIFIED_FOR_LIN_3D", denied["code"])

    def test_h31_validation_requires_all_isolation_flags(self):
        denied = guard.authorize(
            self.registry,
            contract=self.contract,
            capability_id="cap.tripo.h31.head_component_ultra",
            requested_version="v3.1-20260211",
            scope="LIN_3D_VALIDATION",
            lin_authority_head=self.head,
        )
        self.assertEqual("BLOCKED_VALIDATION_ISOLATION_REQUIRED", denied["code"])

        allowed = guard.authorize(
            self.registry,
            contract=self.contract,
            capability_id="cap.tripo.h31.head_component_ultra",
            requested_version="v3.1-20260211",
            scope="LIN_3D_VALIDATION",
            lin_authority_head=self.head,
            isolated_workspace=True,
            no_production_mutation=True,
            no_canon_mutation=True,
        )
        self.assertTrue(allowed["ok"])
        self.assertFalse(allowed["production_3d_mutation_allowed"])

    def test_selection_contract_current_head_overrides_registry_snapshot(self):
        registry_head = self.registry["lin_3d_authority"]["branch_head_at_reconciliation"]
        self.assertNotEqual(registry_head, self.head)

        allowed = guard.authorize(
            self.registry,
            contract=self.contract,
            capability_id="cap.tripo.h31.head_component_ultra",
            requested_version="v3.1-20260211",
            scope="LIN_3D_VALIDATION",
            lin_authority_head=self.head,
            isolated_workspace=True,
            no_production_mutation=True,
            no_canon_mutation=True,
        )
        self.assertTrue(allowed["ok"])
        self.assertEqual(self.head, allowed["lin_authority_head"])

        denied = guard.authorize(
            self.registry,
            contract=self.contract,
            capability_id="cap.tripo.h31.head_component_ultra",
            requested_version="v3.1-20260211",
            scope="LIN_3D_VALIDATION",
            lin_authority_head=registry_head,
            isolated_workspace=True,
            no_production_mutation=True,
            no_canon_mutation=True,
        )
        self.assertEqual("BLOCKED_STALE_LIN_AUTHORITY", denied["code"])

    def test_stale_lin_authority_is_denied(self):
        denied = guard.authorize(
            self.registry,
            contract=self.contract,
            capability_id="cap.tripo.h31.head_component_ultra",
            requested_version="v3.1-20260211",
            scope="LIN_3D_VALIDATION",
            lin_authority_head="075e-stale",
            isolated_workspace=True,
            no_production_mutation=True,
            no_canon_mutation=True,
        )
        self.assertEqual("BLOCKED_STALE_LIN_AUTHORITY", denied["code"])

    def test_superseded_p2_hero_route_is_denied(self):
        record = next(r for r in self.registry["records"] if r["capability_id"] == "cap.tripo.p2.full_body_primary_hero_base")
        denied = guard.authorize(
            self.registry,
            contract=self.contract,
            capability_id=record["capability_id"],
            requested_version=record["exact_version_or_commit"],
            scope="LIN_3D_FINAL",
            lin_authority_head=self.head,
        )
        self.assertFalse(denied["ok"])
        self.assertEqual("SUPERSEDED", denied["status"])

    def test_duplicate_id_invalidates_registry(self):
        mutated = copy.deepcopy(self.registry)
        mutated["records"].append(copy.deepcopy(mutated["records"][0]))
        refresh_summary(mutated)
        errors = guard.validate_registry(mutated)
        self.assertTrue(any("duplicate capability_id" in error for error in errors))

    def test_fake_verified_without_same_path_is_rejected(self):
        mutated = copy.deepcopy(self.registry)
        record = next(r for r in mutated["records"] if r["capability_id"] == "cap.tripo.h31.head_component_ultra")
        record["status"] = "VERIFIED_FOR_LIN_3D"
        record["evidence_level"] = "L8"
        record["authorized_scopes"] = ["LIN_3D_VALIDATION", "LIN_3D_FINAL"]
        refresh_summary(mutated)
        errors = guard.validate_registry(mutated)
        self.assertTrue(any("same-path test must be PASS" in error for error in errors))

    def test_synthetic_complete_l8_record_proves_positive_final_gate(self):
        mutated = copy.deepcopy(self.registry)
        record = next(r for r in mutated["records"] if r["capability_id"] == "cap.tripo.h31.head_component_ultra")
        record["status"] = "VERIFIED_FOR_LIN_3D"
        record["evidence_level"] = "L8"
        record["authorized_scopes"] = ["LIN_3D_VALIDATION", "LIN_3D_FINAL"]
        record["lin_3d_same_path_test"] = {
            "status": "PASS",
            "execution_path": "synthetic-test-only",
            "environment": "synthetic-test-only",
            "artifact_ids": ["artifact-test-1"],
        }
        record["lin_3d_evidence"] = ["synthetic://test-only"]
        record["regression_tests"] = [{"name": "synthetic", "status": "PASS", "evidence": "synthetic://test-only"}]
        record["rollback_behavior"] = ["Synthetic rollback receipt exists for unit-test fixture only."]
        refresh_summary(mutated)
        self.assertEqual([], guard.validate_registry(mutated))
        allowed = guard.authorize(
            mutated,
            contract=self.contract,
            capability_id=record["capability_id"],
            requested_version=record["exact_version_or_commit"],
            scope="LIN_3D_FINAL",
            lin_authority_head=self.head,
        )
        self.assertTrue(allowed["ok"])
        self.assertTrue(allowed["production_3d_mutation_allowed"])
        self.assertFalse(allowed["canon_promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
