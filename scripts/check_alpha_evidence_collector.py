#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "scripts" / "collect_alpha_evidence_bundle.py"

SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{8,}\b", re.IGNORECASE),
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def walk_no_secret(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            walk_no_secret(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_no_secret(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            assert_true(not pattern.search(value), f"secret-like value found at {path}")


def main() -> int:
    assert_true(COLLECTOR.exists(), "missing alpha evidence bundle collector")
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "bundle"
        subprocess.run(
            [
                sys.executable,
                str(COLLECTOR),
                "--mode",
                "sample",
                "--output-dir",
                str(output_dir),
                "--allow-sample-prices",
                "--openai-costs-start-time",
                "1741476542",
                "--openai-costs-runcost-ledger",
                "/private/path/ledger.json",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        manifest = load_json(output_dir / "alpha-evidence-bundle-manifest.json")
        assert_true(manifest["schema_version"] == "0.1", "collector manifest must use schema_version 0.1")
        assert_true(manifest["sanitized"] is True, "collector manifest must be sanitized")
        assert_true(manifest["safe_to_attach_to_issue"] is True, "collector manifest must be issue-safe")
        assert_true(manifest["sample_prices"] is True, "collector manifest must acknowledge sample prices")
        assert_true(manifest["require_real"] is False, "sample collector self-check must not require real evidence")
        artifacts = manifest.get("artifacts")
        assert_true(isinstance(artifacts, list) and len(artifacts) == 5, "collector manifest must list five artifacts")
        for item in artifacts:
            path = output_dir / item["path"]
            assert_true(path.exists(), f"collector artifact missing: {item['path']}")
            walk_no_secret(load_json(path))
        preflight = load_json(output_dir / "alpha-smoke-preflight.json")
        costs_item = next(item for item in preflight["scenarios"] if item["scenario"] == "openai_costs_invoice_comparison")
        assert_true(costs_item["inputs_present"] == ["openai_costs_start_time", "openai_costs_runcost_ledger"], "collector preflight must mark invoice inputs present by name")
        serialized = json.dumps(preflight, sort_keys=True)
        assert_true("1741476542" not in serialized, "collector preflight leaked timestamp value")
        assert_true("/private/path/ledger.json" not in serialized, "collector preflight leaked ledger path")
    print("Alpha evidence collector checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Alpha evidence collector check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
