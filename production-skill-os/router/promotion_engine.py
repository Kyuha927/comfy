#!/usr/bin/env python3
"""Evidence-gated promotion assessor for Production Skill OS.

This tool never changes the catalog. It emits a deterministic promotion proposal.
A separate project-aware review may apply that proposal after checking local rules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

REQUIRED_GATES = (
    "reproduction",
    "repair",
    "same_path_verification",
    "rollback",
    "regression",
    "receipt",
)
ALLOWED_OUTCOMES = {"pass", "fail"}
REQUIRED_EVENT_FIELDS = {
    "event_id",
    "record_id",
    "gate",
    "outcome",
    "environment",
    "execution_path",
    "receipt",
    "observed_at",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{line_no}: event must be an object")
            item["_line"] = line_no
            events.append(item)
    return events


def validate_event(event: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_EVENT_FIELDS - set(event))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    if event.get("gate") not in REQUIRED_GATES:
        errors.append(f"invalid gate: {event.get('gate')!r}")
    if event.get("outcome") not in ALLOWED_OUTCOMES:
        errors.append(f"invalid outcome: {event.get('outcome')!r}")
    for key in ("event_id", "record_id", "environment", "execution_path", "receipt", "observed_at"):
        if key in event and (not isinstance(event[key], str) or not event[key].strip()):
            errors.append(f"{key} must be non-empty string")
    if isinstance(event.get("observed_at"), str) and event["observed_at"].strip():
        try:
            datetime.fromisoformat(event["observed_at"].replace("Z", "+00:00"))
        except ValueError:
            errors.append("observed_at must be ISO-8601")
    return errors


def validate_events(events: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for event in events:
        event_id = str(event.get("event_id", "<missing>"))
        for error in validate_event(event):
            errors.append(f"line {event.get('_line', '?')} ({event_id}): {error}")
        if event_id in seen_ids:
            errors.append(f"line {event.get('_line', '?')} ({event_id}): duplicate event_id")
        seen_ids.add(event_id)
    return errors


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_by_gate(events: list[dict[str, Any]], record_id: str) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    relevant = [event for event in events if event.get("record_id") == record_id]
    relevant.sort(key=lambda event: (str(event.get("observed_at", "")), str(event.get("event_id", ""))))
    for event in relevant:
        selected[event["gate"]] = event
    return selected


def assess(events: list[dict[str, Any]], record_id: str) -> dict[str, Any]:
    by_gate = latest_by_gate(events, record_id)
    missing = [gate for gate in REQUIRED_GATES if gate not in by_gate]
    failed = sorted(gate for gate, event in by_gate.items() if event.get("outcome") == "fail")
    pass_events = [event for event in by_gate.values() if event.get("outcome") == "pass"]
    paths = {event.get("execution_path") for event in pass_events}
    environments = {event.get("environment") for event in pass_events}
    same_path_ok = len(paths) == 1 and not missing and not failed
    same_environment_ok = len(environments) == 1 and not missing and not failed
    promotable = not missing and not failed and same_path_ok and same_environment_ok

    return {
        "record_id": record_id,
        "promotable": promotable,
        "target_status": "canonical" if promotable else None,
        "gates": {
            gate: {
                "outcome": by_gate[gate]["outcome"],
                "event_id": by_gate[gate]["event_id"],
                "receipt": by_gate[gate]["receipt"],
            }
            for gate in REQUIRED_GATES
            if gate in by_gate
        },
        "missing_gates": missing,
        "failed_gates": failed,
        "same_execution_path": same_path_ok,
        "same_environment": same_environment_ok,
        "execution_path": next(iter(paths)) if len(paths) == 1 else None,
        "environment": next(iter(environments)) if len(environments) == 1 else None,
        "scope": {
            "environment": next(iter(environments)),
            "execution_path": next(iter(paths)),
        }
        if promotable
        else None,
        "evidence_event_ids": [by_gate[gate]["event_id"] for gate in REQUIRED_GATES if gate in by_gate],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate evidence event structure")
    validate.add_argument("--evidence", type=Path, required=True)

    assess_cmd = sub.add_parser("assess", help="assess whether one record may be promoted")
    assess_cmd.add_argument("--evidence", type=Path, required=True)
    assess_cmd.add_argument("--record-id", required=True)
    args = parser.parse_args(argv)

    try:
        events = load_jsonl(args.evidence)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 3

    errors = validate_events(events)
    if args.command == "validate":
        print(json.dumps({"ok": not errors, "events": len(events), "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else 1

    if errors:
        print(json.dumps({"ok": False, "error": "evidence_invalid", "details": errors}, ensure_ascii=False, indent=2))
        return 3

    proposal = assess(events, args.record_id)
    proposal["evidence_sha256"] = sha256_file(args.evidence)
    print(json.dumps({"ok": True, "proposal": proposal}, ensure_ascii=False, indent=2))
    return 0 if proposal["promotable"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
