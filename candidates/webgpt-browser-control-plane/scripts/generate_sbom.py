#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECT = ["cryptography", "httpx", "jsonschema", "playwright", "starlette", "uvicorn"]


def candidate_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return str(data["project"]["version"])


def component(name: str) -> dict[str, object]:
    try:
        version = importlib.metadata.version(name)
        return {"type": "library", "name": name, "version": version, "scope": "required"}
    except importlib.metadata.PackageNotFoundError:
        return {"type": "library", "name": name, "version": "NOT_INSTALLED", "scope": "optional"}


def main() -> int:
    components = [component(name) for name in DIRECT]
    serial = hashlib.sha256(
        json.dumps(components, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{serial[:8]}-{serial[8:12]}-{serial[12:16]}-{serial[16:20]}-{serial[20:32]}",
        "version": 1,
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "component": {
                "type": "application",
                "name": "webgpt-browser-control-plane",
                "version": candidate_version(),
            },
            "properties": [
                {"name": "python.version", "value": platform.python_version()},
                {"name": "candidate.production_ready", "value": "false"},
            ],
        },
        "components": components,
    }
    output = ROOT / "artifacts" / "sbom.cdx.json"
    output.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "PASS", "path": str(output), "components": len(components)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
