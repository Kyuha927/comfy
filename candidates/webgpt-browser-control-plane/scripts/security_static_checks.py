#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_RE = re.compile(
    r"(?i)(?:api[_-]?key|secret|password|bearer|authorization|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"
)
FORBIDDEN_CALLS = {"eval", "exec"}


def main() -> int:
    findings: list[dict[str, object]] = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in SECRET_RE.finditer(text):
            findings.append(
                {
                    "severity": "HIGH",
                    "kind": "SECRET_LITERAL_SHAPE",
                    "path": str(path.relative_to(ROOT)),
                    "offset": match.start(),
                }
            )
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            findings.append(
                {
                    "severity": "HIGH",
                    "kind": "SYNTAX_ERROR",
                    "path": str(path.relative_to(ROOT)),
                    "line": exc.lineno,
                }
            )
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    findings.append(
                        {
                            "severity": "HIGH",
                            "kind": "FORBIDDEN_DYNAMIC_EXECUTION",
                            "path": str(path.relative_to(ROOT)),
                            "line": node.lineno,
                            "call": node.func.id,
                        }
                    )
    report = {
        "suite": "WBCP_STATIC_SECURITY_CHECK",
        "generated_at_epoch": time.time(),
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "limitations": [
            "Not a substitute for dependency vulnerability scanning",
            "Not a substitute for ASVS mapping or penetration testing",
            "Does not inspect compiled browser binaries",
        ],
    }
    output = ROOT / "artifacts" / "static-security-check.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
