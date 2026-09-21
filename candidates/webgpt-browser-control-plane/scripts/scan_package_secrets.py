#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", "__pycache__", ".venv", "artifacts", "validation", "handoffs"}
LOCAL_ONLY_NAMES = {".wbcp-oneclick-source.json"}
TEXT_SUFFIXES = {
    "", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".py", ".lock",
    ".template", ".example", ".sha256", ".gitignore",
}
PATTERNS: dict[str, re.Pattern[str]] = {
    "PEM_PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "OPENAI_SECRET_KEY": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GITHUB_CLASSIC_TOKEN": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "GITHUB_FINE_GRAINED_TOKEN": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "AWS_ACCESS_KEY": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GOOGLE_API_KEY": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "SLACK_TOKEN": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "JWT_SHAPE": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
}
BLOCKED_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json", "service-account.json"}
BLOCKED_PREFIXES = ("auth-state", "storage-state")
BLOCKED_SUFFIXES = (".sqlite3", ".db", ".pem", ".key", ".p12", ".pfx")


def main() -> int:
    findings: list[dict[str, object]] = []
    scanned_files = 0
    for path in sorted(ROOT.rglob("*")):
        if path.is_symlink():
            findings.append({"severity": "HIGH", "kind": "SYMLINK_PRESENT", "path": str(path.relative_to(ROOT))})
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.name in LOCAL_ONLY_NAMES:
            continue
        if any(part.endswith(".egg-info") for part in relative.parts):
            continue
        lower_name = path.name.lower()
        if lower_name in BLOCKED_NAMES or lower_name.startswith(BLOCKED_PREFIXES) or lower_name.endswith(BLOCKED_SUFFIXES):
            findings.append({"severity": "HIGH", "kind": "BLOCKED_SENSITIVE_FILENAME", "path": relative.as_posix()})
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"Dockerfile", "Makefile"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned_files += 1
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                findings.append(
                    {
                        "severity": "HIGH",
                        "kind": kind,
                        "path": relative.as_posix(),
                        "line": text.count("\n", 0, match.start()) + 1,
                    }
                )
    report = {
        "suite": "WBCP_PACKAGE_SECRET_AND_SENSITIVE_FILE_SCAN",
        "generated_at_epoch": time.time(),
        "status": "PASS" if not findings else "FAIL",
        "scanned_text_files": scanned_files,
        "findings": findings,
        "limitations": [
            "Pattern-based candidate scan, not a substitute for gitleaks or platform secret scanning",
            "Encrypted or novel token formats may not be recognized",
        ],
    }
    output = ROOT / "artifacts" / "package-secret-scan.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
