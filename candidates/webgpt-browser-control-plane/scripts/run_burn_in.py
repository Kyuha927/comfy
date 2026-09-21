#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import resource
import tempfile
import time
from pathlib import Path

from wbcp.models import RiskTier
from wbcp.runtime import BrowserControlRuntime, build_runtime
from wbcp.settings import RuntimeSettings

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--max-iterations", type=int, default=10_000)
    parser.add_argument(
        "--output",
        default=str(ROOT / "artifacts" / "burn-in-30s.json"),
        help="Write the bounded burn-in receipt used by the release-gate reader.",
    )
    args = parser.parse_args()
    if args.seconds <= 0 or args.seconds > 3600:
        raise SystemExit("seconds must be between 0 and 3600")
    if args.max_iterations < 1:
        raise SystemExit("max-iterations must be positive")

    started = time.monotonic()
    latencies: list[float] = []
    failures: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as td:
        runtime = BrowserControlRuntime(build_runtime(RuntimeSettings.for_tests(Path(td))))
        try:
            iteration = 0
            while time.monotonic() - started < args.seconds and iteration < args.max_iterations:
                iteration += 1
                lap = time.monotonic()
                session_id = f"burn-{iteration}"
                try:
                    permit = runtime.issue_permit(
                        {
                            "session_id": session_id,
                            "allowed_actions": ["session_create", "inspect", "session_close"],
                            "exact_hosts": ["example.com"],
                            "risk_ceiling": int(RiskTier.R1_LOCAL_REVERSIBLE),
                            "max_calls": 3,
                        }
                    )["token"]
                    runtime.create_session(
                        {
                            "sessionId": session_id,
                            "initialUrl": "https://example.com/",
                            "permitToken": permit,
                            "idempotencyKey": f"burn-create-{iteration}",
                        }
                    )
                    job = runtime.preflight(
                        {
                            "sessionId": session_id,
                            "idempotencyKey": f"burn-inspect-{iteration}",
                            "actionType": "inspect",
                            "targetUrl": "https://example.com/",
                            "expected": {"text_contains": "ready"},
                        }
                    )["job"]
                    runtime.authorize({"jobId": job["job_id"], "permitToken": permit})
                    receipt = runtime.commit({"jobId": job["job_id"], "sessionId": session_id})[
                        "receipt"
                    ]
                    if receipt["state"] != "SUCCEEDED":
                        failures.append({"iteration": iteration, "receipt": receipt})
                    runtime.close_session(
                        {
                            "sessionId": session_id,
                            "permitToken": permit,
                            "idempotencyKey": f"burn-close-{iteration}",
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    failures.append(
                        {"iteration": iteration, "type": type(exc).__name__, "error": str(exc)}
                    )
                latencies.append(time.monotonic() - lap)
            verification = runtime.components.evidence.verify().to_dict()
            active_sessions = runtime.components.sessions.count()
        finally:
            runtime.close()

    elapsed = time.monotonic() - started
    ordered = sorted(latencies)
    def percentile(p: float) -> float:
        if not ordered:
            return 0.0
        index = min(len(ordered) - 1, int((len(ordered) - 1) * p))
        return round(ordered[index] * 1000, 3)

    report = {
        "suite": "WBCP_BOUNDED_BURN_IN",
        "status": "PASS" if not failures and verification["valid"] and active_sessions == 0 else "FAIL",
        "production_ready": False,
        "duration_seconds": round(elapsed, 3),
        "iterations": len(latencies),
        "failures": failures[:20],
        "failure_count": len(failures),
        "latency_ms": {
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
            "max": round(max(ordered, default=0.0) * 1000, 3),
        },
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "active_sessions_after_run": active_sessions,
        "evidence": verification,
        "note": "This is a bounded accelerated burn-in, not the mandatory 24-hour production soak.",
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
