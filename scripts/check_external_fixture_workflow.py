#!/usr/bin/env python3
"""Prove a freshly generated external fixture passes every requested language."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures"


def main() -> int:
    descriptor, raw_path = tempfile.mkstemp(prefix="external-workflow-", suffix=".json", dir=FIXTURE_DIR)
    os.close(descriptor)
    path = Path(raw_path)
    path.unlink()
    try:
        subprocess.run(
            [
                "python3",
                "scripts/create_external_fixture.py",
                "--name",
                "external-workflow-self-check",
                "--output",
                str(path),
            ],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            ["go", "test", "./packages/go/ledger", "-run", "TestFixtures", "-count=1"],
            cwd=ROOT,
            check=True,
        )
    finally:
        path.unlink(missing_ok=True)
    print("fresh external fixture workflow passed Python, JavaScript, and Go")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
