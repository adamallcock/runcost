#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    subprocess.run(
        ["go", "test", "./packages/go/ledger", "-run", "TestFixtures", "-count=1"],
        cwd=ROOT,
        check=True,
    )
    print("Checked shared fixtures against Go core.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
