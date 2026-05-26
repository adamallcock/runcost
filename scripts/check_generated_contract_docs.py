#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "generate_contract_docs.py"
EXPECTED = ROOT / "docs" / "generated" / "contract-taxonomy.md"


def main() -> int:
    assert GENERATOR.exists(), "missing generated contract-doc generator"
    assert EXPECTED.exists(), "missing generated contract taxonomy docs"
    with tempfile.TemporaryDirectory() as temp_dir:
        generated = Path(temp_dir) / "contract-taxonomy.md"
        subprocess.run(
            [sys.executable, str(GENERATOR), "--output", str(generated)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        actual = generated.read_text(encoding="utf-8")
    expected = EXPECTED.read_text(encoding="utf-8")
    if actual != expected:
        raise AssertionError(
            "generated contract docs are stale; run "
            "`python3 scripts/generate_contract_docs.py --write`"
        )
    print("Generated contract docs checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
