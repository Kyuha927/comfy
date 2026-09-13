#!/usr/bin/env python3
"""Fail-closed capability selector for Production Skill OS and LIN ASTER 3D.

The capability registry is durable inventory/evidence state. The selection
contract is the mutable binding to the exact current LIN authority head.
This module never invokes a capability, mutates a 3D asset, merges a branch,
or promotes canon.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ALLOWED_STATUSES = {
    "DISCOVERED",
    "REVIEWED",
    "TEST_REQUIRED",
    "ISOLATED_PASS",
    "ISOLATED_FAIL",
    "WATCH",
    "REJECTED",
    "ABSORBED_GENERIC",
    "LIN_3D_TEST_REQUIRED",
    "VERIFIED_FOR_LIN_3D",
    "SUPERSEDED",
    "BLOCKED",
}
ALLOWED_EVIDENCE_LEVELS = {f"L{i}" for i in range(9)}
VALIDATION_STATUSES = {"REVIEWED", "TEST_REQUIRED", "ISOLATED_PASS", "LIN_3D_TEST_REQUIRED"}
TERMINAL_DENY_STATUSES = {"DISCOVERED", "ISOLATED_FAIL", "WATCH", "REJECTED", "SUPERSEDED", "BLOCKED"}
SCOPES = {"GENERIC_PRODUCTION", "LIN_3D_VALIDATION", "LIN_3D_FINAL"}

DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "tool-intake" / "TOOL_CAPABILITY_REGISTRY.json"
DEFAULT_CONTRACT = Path(__file__).resolve().parents[1] / "tool-intake" / "SELECTION_CONTRACT.json"


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be an object")
    return data


def _summary(records: list[dict[str, Any]]) -> dict[str, int]:
    statuses = Counter(str(record.get("status", "")) for record in records)
    return {
        "records": len(records),
        "verified_for_lin_3d": statuses["VERIFIED_FOR_LIN_3D"],
        "absorbed_generic": statuses["ABSORBED_GENERIC"],
        "lin_3d_test_required": statuses["LIN_3D_TEST_REQUIRED"],
        "blocked": statuses["BLOCKED"],
        "superseded": statuses["SUPERSEDED"],
    }


def validate_record(record: dict[str, Any], required_fields: set[str]) -> list[str]:
    errors: list[str] = []
    capability_id = str(record.get("capability_id", "<missing>"))
    missing = sorted(required_fields - set(record))
    if missing:
        errors.append(f"{capability_id}: missing fields: {', '.join(missing)}")

    status = record.get("status")
    if status not in ALLOWED_STATUSES:
        errors.append(f"{capability_id}: invalid status {status!r}")
    evidence_level = record.get("evidence_level")
    if evidence_level not in ALLOWED_EVIDENCE_LEVELS:
        errors.append(f"{capability_id}: invalid evidence_level {evidence_level!r}")

    for key in ("capability_id", "tool_or_system", "capability_name", "source_type", "target_subsystem", "next_gate"):
        if key in record and not _nonempty_str(record[key]):
            errors.append(f"{capability_id}: {key} must be a non-empty string")
    for key in (
        "official_source_urls",
        "review_evidence",
        "failure_modes",
        "recovery_behavior",
        "rollback_behavior",
        "security_or_privacy_notes",
        "known_incompatibilities",
        "supersedes",
        "superseded_by",
        "lin_3d_evidence",
        "regression_tests",
        "authorized_scopes",
    ):
        if key in record and not isinstance(record[key], list):
            errors.append(f"{capability_id}: {key} must be a list")

    scopes = record.get("authorized_scopes", [])
    if isinstance(scopes, list):
        unknown_scopes = sorted(set(scopes) - SCOPES)
        if unknown_scopes:
            errors.append(f"{capability_id}: unknown scopes: {', '.join(unknown_scopes)}")
    else:
        scopes = []

    version = str(record.get("exact_version_or_commit", "")).strip()
    if status in {"ABSORBED_GENERIC", "VERIFIED_FOR_LIN_3D"}:
        if not version or version.upper() in {"UNKNOWN", "UNPINNED", "LATEST"}:
            errors.append(f"{capability_id}: adopted capability requires exact pinned version")
        if not _nonempty_list(record.get("official_source_urls")):
            errors.append(f"{capability_id}: adopted capability requires source authority")

    if status == "ABSORBED_GENERIC":
        if "GENERIC_PRODUCTION" not in scopes:
            errors.append(f"{capability_id}: ABSORBED_GENERIC requires GENERIC_PRODUCTION scope")
        if "LIN_3D_FINAL" in scopes:
            errors.append(f"{capability_id}: generic absorption cannot authorize LIN_3D_FINAL")

    if status != "VERIFIED_FOR_LIN_3D" and "LIN_3D_FINAL" in scopes:
        errors.append(f"{capability_id}: only VERIFIED_FOR_LIN_3D may authorize LIN_3D_FINAL")

    if status in TERMINAL_DENY_STATUSES and scopes:
        errors.append(f"{capability_id}: terminal-deny status cannot authorize a scope")

    if status == "VERIFIED_FOR_LIN_3D":
        if evidence_level != "L8":
            errors.append(f"{capability_id}: VERIFIED_FOR_LIN_3D requires evidence level L8")
        if "LIN_3D_FINAL" not in scopes:
            errors.append(f"{capability_id}: VERIFIED_FOR_LIN_3D requires LIN_3D_FINAL scope")
        same_path = record.get("lin_3d_same_path_test")
        if not isinstance(same_path, dict) or same_path.get("status") != "PASS":
            errors.append(f"{capability_id}: same-path test must be PASS")
        else:
            for key in ("execution_path", "environment"):
                if not _nonempty_str(same_path.get(key)) or str(same_path.get(key)).startswith("NOT_"):
                    errors.append(f"{capability_id}: same-path {key} is missing")
            if not _nonempty_list(same_path.get("artifact_ids")):
                errors.append(f"{capability_id}: same-path artifact_ids are required")
        if not _nonempty_list(record.get("lin_3d_evidence")):
            errors.append(f"{capability_id}: LIN 3D evidence is required")
        regression = record.get("regression_tests")
        if not isinstance(regression, list) or not regression:
            errors.append(f"{capability_id}: regression tests are required")
        elif any(not isinstance(item, dict) or item.get("status") != "PASS" for item in regression):
            errors.append(f"{capability_id}: every regression test must be PASS")
        rollback = record.get("rollback_behavior")
        if not _nonempty_list(rollback) or any("UNKNOWN" in str(item).upper() for item in rollback):
            errors.append(f"{capability_id}: proven rollback behavior is required")
        if not _nonempty_str(record.get("last_verified_at")):
            errors.append(f"{capability_id}: last_verified_at is required")

    if record.get("mutates_3d_state") is True and not _nonempty_list(record.get("rollback_behavior")):
        errors.append(f"{capability_id}: 3D mutation requires rollback behavior")

    if not isinstance(record.get("lin_3d_same_path_test"), dict):
        errors.append(f"{capability_id}: lin_3d_same_path_test must be an object")

    return errors


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = registry.get("records")
    if not isinstance(records, list):
        return ["registry.records must be a list"]

    if set(registry.get("allowed_statuses") or []) != ALLOWED_STATUSES:
        errors.append("registry.allowed_statuses does not match the enforced status set")

    required = registry.get("required_record_fields")
    if not isinstance(required, list) or not required:
        errors.append("registry.required_record_fields must be a non-empty list")
        required_fields: set[str] = set()
    else:
        required_fields = set(str(item) for item in required) | {"evidence_level", "authorized_scopes"}

    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            errors.append("registry record must be an object")
            continue
        capability_id = str(record.get("capability_id", "<missing>"))
        if capability_id in seen:
            errors.append(f"duplicate capability_id: {capability_id}")
        seen.add(capability_id)
        errors.extend(validate_record(record, required_fields))

    known_ids = {str(record.get("capability_id")) for record in records if isinstance(record, dict)}
    for record in records:
        if not isinstance(record, dict):
            continue
        capability_id = str(record.get("capability_id", "<missing>"))
        for key in ("supersedes", "superseded_by"):
            values = record.get(key, [])
            if isinstance(values, list):
                for referenced in values:
                    if referenced not in known_ids:
                        errors.append(f"{capability_id}: {key} references unknown capability {referenced}")

    expected_summary = _summary([record for record in records if isinstance(record, dict)])
    if registry.get("summary") != expected_summary:
        errors.append(f"registry.summary mismatch: expected {expected_summary!r}")

    authority = registry.get("lin_3d_authority")
    if not isinstance(authority, dict):
        errors.append("registry.lin_3d_authority must be an object")
    else:
        for key in (
            "repository",
            "branch",
            "branch_head_at_reconciliation",
            "ssot_path",
            "ssot_blob_sha",
            "live_state_path",
            "live_state_blob_sha",
            "production_control_policy_id",
            "final_lock_authority",
        ):
            if not _nonempty_str(authority.get(key)):
                errors.append(f"registry.lin_3d_authority.{key} is required")
        if authority.get("final_lock_authority") != "USER_ONLY":
            errors.append("final lock authority must remain USER_ONLY")
        if authority.get("auto_merge") is not False or authority.get("auto_canon") is not False:
            errors.append("automatic merge/canon must remain false")

    return errors


def validate_contract(registry: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    """Validate the mutable current-authority binding without weakening registry evidence."""
    errors: list[str] = []
    if contract.get("registry_path") != "production-skill-os/tool-intake/TOOL_CAPABILITY_REGISTRY.json":
        errors.append("selection contract registry_path mismatch")

    authority = contract.get("authority")
    registry_authority = registry.get("lin_3d_authority")
    if not isinstance(authority, dict):
        errors.append("selection contract authority must be an object")
        return errors
    if not isinstance(registry_authority, dict):
        errors.append("registry.lin_3d_authority must be an object")
        return errors

    for key in (
        "repository",
        "branch",
        "branch_head_at_reconciliation",
        "ssot_path",
        "ssot_blob_sha",
        "live_state_path",
        "live_state_blob_sha",
        "production_control_policy_id",
        "final_lock_authority",
    ):
        if not _nonempty_str(authority.get(key)):
            errors.append(f"selection contract authority.{key} is required")

    for key in ("repository", "branch", "ssot_path", "live_state_path", "production_control_policy_id"):
        if authority.get(key) != registry_authority.get(key):
            errors.append(f"selection contract authority.{key} must match registry authority identity")

    if authority.get("final_lock_authority") != "USER_ONLY":
        errors.append("selection contract final lock authority must remain USER_ONLY")
    if authority.get("auto_merge") is not False or authority.get("auto_canon") is not False:
        errors.append("selection contract automatic merge/canon must remain false")

    invariants = contract.get("invariants")
    if not isinstance(invariants, dict):
        errors.append("selection contract invariants must be an object")
    else:
        if invariants.get("final_lock_authority") != "USER_ONLY":
            errors.append("selection contract must preserve USER_ONLY final lock authority")
        if invariants.get("automatic_merge") is not False:
            errors.append("selection contract automatic_merge must remain false")
        if invariants.get("automatic_canon_promotion") is not False:
            errors.append("selection contract automatic_canon_promotion must remain false")
        if invariants.get("unknown_or_unverified_final_use") != "DENY":
            errors.append("selection contract unknown/unverified final use must remain DENY")

    scopes = contract.get("scopes")
    if not isinstance(scopes, dict):
        errors.append("selection contract scopes must be an object")
    else:
        final_scope = scopes.get("LIN_3D_FINAL", {})
        if final_scope.get("allowed_statuses") != ["VERIFIED_FOR_LIN_3D"]:
            errors.append("LIN_3D_FINAL must allow only VERIFIED_FOR_LIN_3D")
        if final_scope.get("canon_promotion_allowed") is not False:
            errors.append("LIN_3D_FINAL cannot promote canon")
        validation_scope = scopes.get("LIN_3D_VALIDATION", {})
        if validation_scope.get("production_3d_mutation_allowed") is not False:
            errors.append("LIN_3D_VALIDATION cannot mutate production 3D state")
        if validation_scope.get("canon_promotion_allowed") is not False:
            errors.append("LIN_3D_VALIDATION cannot promote canon")

    return errors


def current_lin_authority(registry: dict[str, Any], contract: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return current authority. Selection contract wins for the mutable HEAD binding."""
    if contract is not None and isinstance(contract.get("authority"), dict):
        return contract["authority"]
    authority = registry.get("lin_3d_authority")
    return authority if isinstance(authority, dict) else {}


def find_capability(registry: dict[str, Any], capability_id: str) -> dict[str, Any] | None:
    for record in registry.get("records", []):
        if isinstance(record, dict) and record.get("capability_id") == capability_id:
            return record
    return None


def _deny(code: str, message: str, *, capability: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "decision": "DENY",
        "code": code,
        "message": message,
        "capability_id": capability.get("capability_id") if capability else None,
        "status": capability.get("status") if capability else None,
        "canon_promotion_allowed": False,
        "automatic_merge_allowed": False,
        "user_final_approval_required": True,
    }


def authorize(
    registry: dict[str, Any],
    *,
    capability_id: str,
    requested_version: str,
    scope: str,
    lin_authority_head: str,
    contract: dict[str, Any] | None = None,
    isolated_workspace: bool = False,
    no_production_mutation: bool = False,
    no_canon_mutation: bool = False,
) -> dict[str, Any]:
    errors = validate_registry(registry)
    if contract is not None:
        errors.extend(validate_contract(registry, contract))
    if errors:
        result = _deny("BLOCKED_REGISTRY_INVALID", "Registry or selection contract validation failed")
        result["details"] = errors
        return result

    capability = find_capability(registry, capability_id)
    if capability is None:
        return _deny("BLOCKED_CAPABILITY_UNKNOWN", f"Unknown capability: {capability_id}")
    if scope not in SCOPES:
        return _deny("BLOCKED_CAPABILITY_SCOPE", f"Unknown scope: {scope}", capability=capability)

    expected_version = str(capability.get("exact_version_or_commit", ""))
    if requested_version != expected_version:
        return _deny(
            "BLOCKED_VERSION_MISMATCH",
            f"Requested version {requested_version!r} does not match {expected_version!r}",
            capability=capability,
        )

    authority = current_lin_authority(registry, contract)
    expected_head = str(authority.get("branch_head_at_reconciliation", ""))
    if scope.startswith("LIN_3D"):
        if not expected_head:
            return _deny("BLOCKED_REGISTRY_INVALID", "Current LIN authority head is missing", capability=capability)
        if lin_authority_head != expected_head:
            return _deny(
                "BLOCKED_STALE_LIN_AUTHORITY",
                f"LIN authority head {lin_authority_head!r} does not match {expected_head!r}",
                capability=capability,
            )

    status = capability.get("status")
    authorized_scopes = capability.get("authorized_scopes", [])
    if scope not in authorized_scopes:
        if scope == "LIN_3D_FINAL":
            return _deny(
                "BLOCKED_CAPABILITY_NOT_VERIFIED_FOR_LIN_3D",
                "Capability is not authorized for the final LIN 3D path",
                capability=capability,
            )
        return _deny("BLOCKED_CAPABILITY_SCOPE", "Capability does not authorize this scope", capability=capability)

    if scope == "GENERIC_PRODUCTION":
        if status not in {"ABSORBED_GENERIC", "VERIFIED_FOR_LIN_3D"}:
            return _deny("BLOCKED_CAPABILITY_STATUS", "Status is not adopted for generic production", capability=capability)

    elif scope == "LIN_3D_VALIDATION":
        if status not in VALIDATION_STATUSES:
            return _deny("BLOCKED_CAPABILITY_STATUS", "Status cannot enter LIN 3D validation", capability=capability)
        if not (isolated_workspace and no_production_mutation and no_canon_mutation):
            return _deny(
                "BLOCKED_VALIDATION_ISOLATION_REQUIRED",
                "Validation requires an isolated workspace and explicit no-production/no-canon mutation flags",
                capability=capability,
            )

    elif scope == "LIN_3D_FINAL":
        if status != "VERIFIED_FOR_LIN_3D":
            return _deny(
                "BLOCKED_CAPABILITY_NOT_VERIFIED_FOR_LIN_3D",
                "Only VERIFIED_FOR_LIN_3D may enter the final path",
                capability=capability,
            )
        same_path = capability.get("lin_3d_same_path_test", {})
        if same_path.get("status") != "PASS" or not same_path.get("artifact_ids"):
            return _deny("BLOCKED_SAME_PATH_EVIDENCE_MISSING", "Same-path evidence is incomplete", capability=capability)
        tests = capability.get("regression_tests", [])
        if not tests or any(not isinstance(item, dict) or item.get("status") != "PASS" for item in tests):
            return _deny(
                "BLOCKED_ROLLBACK_OR_REGRESSION_EVIDENCE_MISSING",
                "Regression evidence is incomplete",
                capability=capability,
            )
        if not capability.get("rollback_behavior"):
            return _deny(
                "BLOCKED_ROLLBACK_OR_REGRESSION_EVIDENCE_MISSING",
                "Rollback evidence is incomplete",
                capability=capability,
            )

    return {
        "ok": True,
        "decision": "ALLOW",
        "code": "CAPABILITY_AUTHORIZED",
        "capability_id": capability_id,
        "status": status,
        "scope": scope,
        "exact_version_or_commit": expected_version,
        "lin_authority_head": expected_head if scope.startswith("LIN_3D") else None,
        "constraints": capability.get("constraints", {}),
        "production_3d_mutation_allowed": scope == "LIN_3D_FINAL",
        "canon_promotion_allowed": False,
        "automatic_merge_allowed": False,
        "user_final_approval_required": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate registry and selection contract")

    auth = sub.add_parser("authorize", help="authorize one exact capability for one scope")
    auth.add_argument("--capability-id", required=True)
    auth.add_argument("--version", required=True)
    auth.add_argument("--scope", choices=sorted(SCOPES), required=True)
    auth.add_argument("--lin-authority-head", default="")
    auth.add_argument("--isolated-workspace", action="store_true")
    auth.add_argument("--no-production-mutation", action="store_true")
    auth.add_argument("--no-canon-mutation", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        registry = load_json(args.registry)
        contract = load_json(args.contract)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "decision": "DENY", "code": "BLOCKED_REGISTRY_INVALID", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 3

    errors = validate_registry(registry)
    errors.extend(validate_contract(registry, contract))

    if args.command == "validate":
        payload = {
            "ok": not errors,
            "records": len(registry.get("records", [])),
            "summary": registry.get("summary"),
            "current_lin_authority_head": current_lin_authority(registry, contract).get("branch_head_at_reconciliation"),
            "errors": errors,
            "canon_promotion_allowed": False,
            "automatic_merge_allowed": False,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if not errors else 1

    if errors:
        print(json.dumps({"ok": False, "decision": "DENY", "code": "BLOCKED_REGISTRY_INVALID", "details": errors}, ensure_ascii=False, indent=2))
        return 3

    result = authorize(
        registry,
        contract=contract,
        capability_id=args.capability_id,
        requested_version=args.version,
        scope=args.scope,
        lin_authority_head=args.lin_authority_head,
        isolated_workspace=args.isolated_workspace,
        no_production_mutation=args.no_production_mutation,
        no_canon_mutation=args.no_canon_mutation,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
