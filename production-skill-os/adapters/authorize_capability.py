\
#!/usr/bin/env python3
"""Thin consumer adapter for the fail-closed capability guard."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capability-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--scope", choices=["GENERIC_PRODUCTION", "LIN_3D_VALIDATION", "LIN_3D_FINAL"], required=True)
    parser.add_argument("--lin-authority-head", default="")
    parser.add_argument("--isolated-workspace", action="store_true")
    parser.add_argument("--no-production-mutation", action="store_true")
    parser.add_argument("--no-canon-mutation", action="store_true")
    args = parser.parse_args(argv)

    guard = Path(__file__).resolve().parents[1] / "router" / "capability_guard.py"
    command = [
        sys.executable,
        str(guard),
        "authorize",
        "--capability-id", args.capability_id,
        "--version", args.version,
        "--scope", args.scope,
    ]
    if args.lin_authority_head:
        command += ["--lin-authority-head", args.lin_authority_head]
    if args.isolated_workspace:
        command.append("--isolated-workspace")
    if args.no_production_mutation:
        command.append("--no-production-mutation")
    if args.no_canon_mutation:
        command.append("--no-canon-mutation")

    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
