#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="runcost-fixture-generator-") as tempdir:
        fixture_path = Path(tempdir) / "fixture-generator-normalized-usage.json"
        run(
            [
                "python3",
                "scripts/create_fixture.py",
                "--example",
                "normalized_usage",
                "--write",
                str(fixture_path),
            ]
        )
        run(["python3", "scripts/check_fixtures.py", "--fixture", str(fixture_path)])
    print("Fixture generator checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
