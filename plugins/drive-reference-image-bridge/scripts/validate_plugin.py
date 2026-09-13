#!/usr/bin/env python3
"""Static release gate for the skill-only ChatGPT plugin package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQUIRED_ERROR_CODES = {
    "BLOCKED_DRIVE_IMAGE_NOT_FOUND",
    "BLOCKED_DRIVE_IMAGE_AMBIGUOUS",
    "BLOCKED_DRIVE_RAW_FETCH_FAILED",
    "BLOCKED_DRIVE_IMAGE_INVALID_MIME",
    "BLOCKED_DRIVE_IMAGE_REFERENCE_BIND_FAILED",
    "BLOCKED_NATIVE_IMAGE_GEN_UNAVAILABLE",
    "BLOCKED_NATIVE_REFERENCE_BIND_UNVERIFIED",
    "BLOCKED_EXTERNAL_API_PROHIBITED",
}

FORBIDDEN_PATTERNS = {
    "OpenAI API key": re.compile(r"OPENAI_API_KEY", re.IGNORECASE),
    "OpenAI API endpoint": re.compile(r"api\.openai\.com", re.IGNORECASE),
    "Images API route": re.compile(r"/v1/images|images\.(generate|edit)", re.IGNORECASE),
    "Responses API route": re.compile(r"/v1/responses", re.IGNORECASE),
}

ALLOWED_API_POLICY_FILES = {
    "README.md",
    "SECURITY.md",
    "PRIVACY.md",
    "CHANGELOG.md",
    "VALIDATION_REPORT.md",
    "gates.md",
    "SKILL.md",
}


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be an object")
    return data


def validate(root: Path, repo_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    manifest_path = root / ".codex-plugin" / "plugin.json"
    skill_path = root / "skills" / "drive-reference-image" / "SKILL.md"
    marketplace_path = (repo_root / ".agents" / "plugins" / "marketplace.json") if repo_root else None

    for required in [
        manifest_path,
        skill_path,
        root / "README.md",
        root / "SECURITY.md",
        root / "PRIVACY.md",
        root / "TERMS.md",
        root / "skills" / "drive-reference-image" / "references" / "gates.md",
        root / "skills" / "drive-reference-image" / "references" / "error-codes.md",
        root / "skills" / "drive-reference-image" / "references" / "receipt-schema.json",
    ]:
        if not required.is_file():
            errors.append(f"missing required file: {required.relative_to(root)}")

    if errors:
        return errors

    manifest = read_json(manifest_path)
    for key in ("name", "version", "description", "skills"):
        if not manifest.get(key):
            errors.append(f"manifest missing {key}")
    if manifest.get("name") != "drive-reference-image-bridge":
        errors.append("manifest name mismatch")
    if manifest.get("skills") != "./skills/":
        errors.append("manifest skills path must be ./skills/")
    if "mcpServers" in manifest or "apps" in manifest:
        errors.append("release must remain skill-only; MCP/app mapping detected")

    skill = skill_path.read_text(encoding="utf-8")
    if not skill.startswith("---\nname: drive-reference-image\n"):
        errors.append("SKILL.md frontmatter is invalid")
    for token in REQUIRED_ERROR_CODES | {"PASS_NATIVE"}:
        if token not in skill and token not in (root / "skills" / "drive-reference-image" / "references" / "error-codes.md").read_text(encoding="utf-8"):
            errors.append(f"missing required contract token: {token}")

    if (root / ".mcp.json").exists() or (root / ".app.json").exists():
        errors.append("unexpected MCP configuration in native-only release")

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".pyc"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                # Policy and documentation files may name prohibited routes only to forbid them.
                if path.name not in ALLOWED_API_POLICY_FILES and "test" not in path.parts and path.name != "validate_plugin.py":
                    errors.append(f"{label} found in executable/config content: {path.relative_to(root)}")

    if marketplace_path:
        if not marketplace_path.is_file():
            errors.append("repo marketplace file is missing")
        else:
            marketplace = read_json(marketplace_path)
            entries = marketplace.get("plugins", [])
            match = [entry for entry in entries if entry.get("name") == "drive-reference-image-bridge"]
            if len(match) != 1:
                errors.append("marketplace must contain exactly one bridge entry")
            else:
                source = match[0].get("source", {})
                if source.get("path") != "./plugins/drive-reference-image-bridge":
                    errors.append("marketplace source path mismatch")
                policy = match[0].get("policy", {})
                if not policy.get("installation") or not policy.get("authentication"):
                    errors.append("marketplace policy is incomplete")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--repo-root", type=Path)
    args = parser.parse_args()
    errors = validate(args.plugin_root.resolve(), args.repo_root.resolve() if args.repo_root else None)
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
