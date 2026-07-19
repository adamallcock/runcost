#!/usr/bin/env python3
"""Run the public RunCost conformance suite without competitor assumptions."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("$ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RunCost conformance checks or one external fixture.")
    parser.add_argument("--fixture", help="validate one redaction-safe standard fixture")
    args = parser.parse_args()
    if args.fixture:
        run(["python3", "scripts/check_fixtures.py", "--fixture", args.fixture])
        return 0
    run(["python3", "scripts/check_fixtures.py"])
    run(["python3", "scripts/check_product_expansion.py"])
    run(["go", "test", "./packages/go/ledger", "-run", "TestProductExpansionFixtures"])
    run(["python3", "scripts/generate_conformance_report.py", "--check"])
    print("RunCost conformance suite passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
