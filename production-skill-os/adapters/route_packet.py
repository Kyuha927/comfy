#!/usr/bin/env python3
"""Convert one failure event into a compact Skill OS route packet."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "router" / "failure_catalog.jsonl",
    )
    parser.add_argument("--include-advisory", action="store_true")
    args = parser.parse_args(argv)

    try:
        event = json.loads(args.event.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"invalid event: {exc}"}, ensure_ascii=False))
        return 3
    if not isinstance(event, dict):
        print(json.dumps({"ok": False, "error": "event must be object"}, ensure_ascii=False))
        return 3

    router = Path(__file__).resolve().parents[1] / "router" / "skill_router.py"
    command = [
        sys.executable,
        str(router),
        "--catalog",
        str(args.catalog),
        "lookup",
        "--domain",
        str(event.get("domain", "")),
        "--error-code",
        str(event.get("error_code", "")),
        "--text",
        str(event.get("message", "")),
    ]
    if args.include_advisory:
        command.append("--include-advisory")

    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        print(json.dumps({"ok": False, "error": "router_output_invalid"}, ensure_ascii=False))
        return 3

    if not payload.get("ok"):
        print(
            json.dumps(
                {
                    "ok": False,
                    "route": payload.get("route", "NOVEL_OR_UNVERIFIED"),
                    "escalate": True,
                    "novelty_packet": {
                        "domain": event.get("domain"),
                        "error_code": event.get("error_code"),
                        "message": event.get("message"),
                        "environment": event.get("environment"),
                        "execution_path": event.get("execution_path"),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    route = payload["route"]
    packet = {
        "ok": True,
        "record_id": route["id"],
        "status": route["status"],
        "auto_execute_allowed": bool(payload.get("auto_execute_allowed")),
        "escalate": bool(payload.get("escalate")),
        "diagnosis_probes": route.get("diagnosis_probes", []),
        "repair": route.get("repair", []),
        "verification": route.get("verification", []),
        "rollback": route.get("rollback"),
        "scope": route.get("scope"),
        "route_reasons": route.get("route_reasons", []),
    }
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
