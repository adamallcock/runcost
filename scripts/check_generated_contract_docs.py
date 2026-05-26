#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "generate_contract_docs.py"
EXPECTED = ROOT / "docs" / "generated" / "contract-taxonomy.md"
EXPECTED_SCHEMA = ROOT / "docs" / "generated" / "schema-fields.md"
EXPECTED_SUPPORT = ROOT / "docs" / "generated" / "fixture-support-matrix.md"


def main() -> int:
    assert GENERATOR.exists(), "missing generated contract-doc generator"
    assert EXPECTED.exists(), "missing generated contract taxonomy docs"
    assert EXPECTED_SCHEMA.exists(), "missing generated schema-field docs"
    assert EXPECTED_SUPPORT.exists(), "missing generated fixture support matrix docs"
    with tempfile.TemporaryDirectory() as temp_dir:
        generated = Path(temp_dir) / "contract-taxonomy.md"
        generated_schema = Path(temp_dir) / "schema-fields.md"
        generated_support = Path(temp_dir) / "fixture-support-matrix.md"
        subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--output",
                str(generated),
                "--schema-output",
                str(generated_schema),
                "--support-output",
                str(generated_support),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        actual = generated.read_text(encoding="utf-8")
        actual_schema = generated_schema.read_text(encoding="utf-8")
        actual_support = generated_support.read_text(encoding="utf-8")
    expected = EXPECTED.read_text(encoding="utf-8")
    expected_schema = EXPECTED_SCHEMA.read_text(encoding="utf-8")
    expected_support = EXPECTED_SUPPORT.read_text(encoding="utf-8")
    if actual != expected:
        raise AssertionError(
            "generated contract docs are stale; run "
            "`python3 scripts/generate_contract_docs.py --write`"
        )
    if actual_schema != expected_schema:
        raise AssertionError(
            "generated schema-field docs are stale; run "
            "`python3 scripts/generate_contract_docs.py --write`"
        )
    if actual_support != expected_support:
        raise AssertionError(
            "generated fixture support docs are stale; run "
            "`python3 scripts/generate_contract_docs.py --write`"
        )
    print("Generated contract docs checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
