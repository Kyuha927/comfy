#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def candidate_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def invoke(path: Path, *, timeout_seconds: int = 180) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": 124,
            "result": {
                "status": "BLOCKED_GATE_RUNNER_TIMEOUT",
                "timeout_seconds": timeout_seconds,
                "stdout": exc.stdout or "",
            },
            "stderr": exc.stderr or "",
        }
    parsed: Any
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed = {"raw_stdout": completed.stdout}
    return {"exit_code": completed.returncode, "result": parsed, "stderr": completed.stderr}


def load_artifact(name: str) -> dict[str, Any] | None:
    path = ROOT / "artifacts" / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "FAIL", "error": "invalid JSON", "path": str(path)}


def main() -> int:
    offline = invoke(ROOT / "scripts" / "run_offline_acceptance.py", timeout_seconds=150)
    mcp = invoke(ROOT / "scripts" / "run_mcp_acceptance.py", timeout_seconds=90)
    http_process = invoke(ROOT / "scripts" / "run_http_process_smoke.py", timeout_seconds=30)
    browser_probe = invoke(ROOT / "scripts" / "probe_system_chromium.py", timeout_seconds=30)
    static_security = invoke(ROOT / "scripts" / "security_static_checks.py", timeout_seconds=30)
    package_secret_scan = invoke(ROOT / "scripts" / "scan_package_secrets.py", timeout_seconds=30)
    sbom = invoke(ROOT / "scripts" / "generate_sbom.py", timeout_seconds=30)
    supply_chain = invoke(ROOT / "scripts" / "generate_supply_chain.py", timeout_seconds=30)
    source_integrity = invoke(ROOT / "scripts" / "verify_source_manifest.py", timeout_seconds=30)
    engine_sources = invoke(ROOT / "scripts" / "verify_engine_sources.py", timeout_seconds=30)
    burn_in = load_artifact("burn-in-30s.json")
    exit_stability = load_artifact("repeated-suite-10x.json")

    gates: dict[str, dict[str, Any]] = {
        "G0_OFFICIAL_ROUTE_RECONCILIATION": {
            "status": "PASS_DESIGN_ONLY",
            "evidence": "OFFICIAL_ROUTE_RECONCILIATION.md",
        },
        "G1_ARCHITECTURE_AND_THREAT_MODEL_CLOSURE": {
            "status": "PASS_OFFLINE_ONLY"
            if offline["exit_code"] == 0 and engine_sources["exit_code"] == 0
            else "FAIL",
            "evidence": {"offline_suite": offline, "engine_source_lock": engine_sources},
        },
        "G2_IDENTITY_SESSION_AND_ACCOUNT_CORRECTNESS": {"status": "NOT_RUN"},
        "G3_AUTHORIZATION_AND_ECONOMIC_SAFETY": {
            "status": "PASS_OFFLINE_ONLY" if offline["exit_code"] == 0 else "FAIL",
            "evidence": "policy, permit, approval, concurrency, idempotency, and cost-cap tests",
        },
        "G4_TRANSPORT_AND_CHATGPT_INTEGRATION": {
            "status": "PASS_OFFLINE_ONLY"
            if mcp["exit_code"] == 0 and http_process["exit_code"] == 0
            else "FAIL",
            "evidence": {"mcp_suite": mcp, "real_http_process": http_process},
            "remaining": "real ChatGPT invocation and Secure MCP Tunnel or approved desktop route",
        },
        "G5_BROWSER_WORKER_INTEGRITY": {
            "status": "PASS_OFFLINE_ONLY" if browser_probe["exit_code"] == 0 else "BLOCKED",
            "evidence": {
                "real_chromium_offline": "test_playwright_real_chromium_offline.py",
                "live_network_probe": browser_probe,
            },
            "remaining": "target-Mac live network, browser identity, DNS rebinding, and authenticated-site proof",
        },
        "G6_POSTCONDITION_AND_FALSE_SUCCESS_RESISTANCE": {
            "status": "PASS_OFFLINE_ONLY" if offline["exit_code"] == 0 else "FAIL",
            "evidence": "DOM, rendered-pixel, and provider-receipt enforcement regressions",
        },
        "G7_RELIABILITY_RECOVERY_AND_CONCURRENCY": {
            "status": "PASS_OFFLINE_ONLY"
            if (
                offline["exit_code"] == 0
                and exit_stability
                and exit_stability.get("status") == "PASS"
                and exit_stability.get("run_count") == 10
                and isinstance(exit_stability.get("expected_tests_per_run"), int)
                and exit_stability.get("expected_tests_per_run", 0) > 0
                and exit_stability.get("total_tests")
                == exit_stability.get("run_count", 0)
                * exit_stability.get("expected_tests_per_run", 0)
            )
            else "NOT_RUN",
            "evidence": {"offline_suite": offline, "repeated_suite": exit_stability},
            "remaining": "kill every transition, browser/tunnel crash, reboot, partition, disk full, backup/restore, and migration rollback",
        },
        "G8_SECURITY_VERIFICATION": {
            "status": "PASS_OFFLINE_ONLY"
            if static_security["exit_code"] == 0 and package_secret_scan["exit_code"] == 0
            else "FAIL",
            "evidence": {
                "static_source_scan": static_security,
                "package_secret_scan": package_secret_scan,
            },
            "remaining": "independent ASVS mapping, dependency vulnerability analysis, parser fuzzing, and authorized penetration test",
        },
        "G9_EVIDENCE_PRIVACY_AND_OBSERVABILITY": {
            "status": "PASS_OFFLINE_ONLY",
            "evidence": "local HMAC chain and Ed25519 checkpoint tests",
            "remaining": "managed key custody, external anchor, OTel export, retention enforcement, and privacy review",
        },
        "G10_PERFORMANCE_AND_SERVICE_LEVEL_OBJECTIVES": {
            "status": "PASS_OFFLINE_ONLY"
            if burn_in and burn_in.get("status") == "PASS"
            else "NOT_RUN",
            "evidence": burn_in,
            "remaining": "production SLO proof and mandatory 24-hour mixed read/write soak",
        },
        "G11_SUPPLY_CHAIN_PACKAGING_AND_UPGRADE_SAFETY": {
            "status": "PASS_OFFLINE_ONLY"
            if (
                sbom["exit_code"] == 0
                and supply_chain["exit_code"] == 0
                and source_integrity["exit_code"] == 0
                and engine_sources["exit_code"] == 0
            )
            else "FAIL",
            "evidence": {
                "sbom": sbom,
                "candidate_provenance": supply_chain,
                "frozen_source_integrity": source_integrity,
                "engine_source_lock": engine_sources,
            },
            "remaining": "complete transitive hash lock, vulnerability scan, legal review, trusted-builder provenance, external signature, upgrade and rollback proof",
        },
        "G12_REPRESENTATIVE_REAL_JOURNEYS": {"status": "NOT_RUN"},
        "G13_ASTRA_INDEPENDENT_RELEASE_DECISION": {"status": "NOT_RUN"},
        "G14_EXPLICIT_USER_PRODUCTION_PROMOTION": {"status": "NOT_GRANTED"},
    }
    hard_nonpass = [name for name, gate in gates.items() if gate["status"] != "PASS"]
    release_ready = not hard_nonpass
    report = {
        "suite": "WBCP_COMMERCIAL_RELEASE_GATES",
        "candidate_version": candidate_version(),
        "generated_at_epoch": time.time(),
        "release_ready": release_ready,
        "verdict": "PRODUCTION_ACCEPTED"
        if release_ready
        else "CONDITIONAL_OFFLINE_AND_LOCAL_TRANSPORT_PASS_PRODUCTION_BLOCKED",
        "hard_nonpass_gates": hard_nonpass,
        "gates": gates,
    }
    output = ROOT / "artifacts" / "release-gates.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if release_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
