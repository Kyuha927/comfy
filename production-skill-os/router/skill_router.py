#!/usr/bin/env python3
"""Deterministic low-token router for production failure knowledge.

Standard-library only. The router never executes a repair; it only selects a
bounded record. External/candidate records are advisory unless explicitly
requested, preventing unverified fixes from becoming automatic behavior.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

ALLOWED_STATUSES = {"canonical", "candidate", "external_advisory", "deprecated"}
REQUIRED_FIELDS = {
    "id",
    "domain",
    "status",
    "match",
    "diagnosis_probes",
    "repair",
    "verification",
    "rollback",
    "confidence",
    "evidence",
}


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\b[0-9a-f]{8,}\b", "<hex>", text)
    text = re.sub(r"\b\d{5,}\b", "<num>", text)
    return re.sub(r"\s+", " ", text)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{lineno}: record must be an object")
            item["_line"] = lineno
            records.append(item)
    return records


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(record))
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    if record.get("status") not in ALLOWED_STATUSES:
        errors.append(f"invalid status: {record.get('status')!r}")
    confidence = record.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append("confidence must be a number in [0, 1]")
    match = record.get("match")
    if not isinstance(match, dict):
        errors.append("match must be an object")
    elif not any(match.get(k) for k in ("error_codes", "contains_all", "contains_any")):
        errors.append("match needs error_codes, contains_all, or contains_any")
    for key in ("diagnosis_probes", "repair", "verification", "evidence"):
        if key in record and not isinstance(record[key], list):
            errors.append(f"{key} must be a list")
    if "rollback" in record and not isinstance(record["rollback"], (str, list)):
        errors.append("rollback must be a string or list")
    return errors


def validate_catalog(records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    for rec in records:
        rid = str(rec.get("id", "<missing-id>"))
        line = rec.get("_line", "?")
        for err in validate_record(rec):
            errors.append(f"line {line} ({rid}): {err}")
        if rid in seen:
            errors.append(f"line {line} ({rid}): duplicate id; first seen on line {seen[rid]}")
        else:
            seen[rid] = int(line) if isinstance(line, int) else -1
    return errors


def _strs(value: Any) -> list[str]:
    return [str(x).lower() for x in value] if isinstance(value, list) else []


def score_record(record: dict[str, Any], domain: str, error_code: str, text: str) -> tuple[int, list[str]] | None:
    if domain and record.get("domain") not in {domain, "*"}:
        return None
    match = record.get("match", {})
    norm = normalize_text(text)
    score = 0
    reasons: list[str] = []

    error_codes = _strs(match.get("error_codes"))
    if error_code and error_code.lower() in error_codes:
        score += 100
        reasons.append("exact_error_code")

    contains_all = _strs(match.get("contains_all"))
    if contains_all:
        if all(token in norm for token in contains_all):
            score += 40 + len(contains_all)
            reasons.append("contains_all")
        else:
            return None

    contains_any = _strs(match.get("contains_any"))
    if contains_any and any(token in norm for token in contains_any):
        score += 10
        reasons.append("contains_any")

    if score == 0:
        return None
    score += int(float(record.get("confidence", 0)) * 9)
    return score, reasons


def select_record(
    records: Iterable[dict[str, Any]],
    *,
    domain: str,
    error_code: str,
    text: str,
    statuses: set[str],
) -> dict[str, Any] | None:
    candidates: list[tuple[int, str, dict[str, Any], list[str]]] = []
    for record in records:
        if record.get("status") not in statuses:
            continue
        scored = score_record(record, domain, error_code, text)
        if scored is None:
            continue
        score, reasons = scored
        candidates.append((score, str(record.get("id", "")), record, reasons))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    score, _, record, reasons = candidates[0]
    result = {k: v for k, v in record.items() if not k.startswith("_")}
    result["route_score"] = score
    result["route_reasons"] = reasons
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalog", type=Path, default=Path(__file__).with_name("failure_catalog.jsonl"))
    sub = p.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate catalog structure")
    validate.set_defaults(command="validate")

    lookup = sub.add_parser("lookup", help="select one bounded repair record")
    lookup.add_argument("--domain", default="")
    lookup.add_argument("--error-code", default="")
    lookup.add_argument("--text", default="")
    lookup.add_argument(
        "--include-advisory",
        action="store_true",
        help="also consider candidate/external_advisory records; never auto-execute them",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = load_jsonl(args.catalog)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 3

    errors = validate_catalog(records)
    if args.command == "validate":
        payload = {"ok": not errors, "records": len(records), "errors": errors}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if not errors else 1

    if errors:
        print(json.dumps({"ok": False, "error": "catalog_invalid", "details": errors}, ensure_ascii=False, indent=2))
        return 3

    statuses = {"canonical"}
    if args.include_advisory:
        statuses |= {"candidate", "external_advisory"}
    result = select_record(
        records,
        domain=args.domain,
        error_code=args.error_code,
        text=args.text,
        statuses=statuses,
    )
    if result is None:
        print(json.dumps({"ok": False, "route": "NOVEL_OR_UNVERIFIED", "escalate": True}, ensure_ascii=False))
        return 2

    auto_execute = result.get("status") == "canonical"
    print(
        json.dumps(
            {
                "ok": True,
                "route": result,
                "auto_execute_allowed": auto_execute,
                "escalate": not auto_execute,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
