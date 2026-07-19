#!/usr/bin/env python3
"""Create and validate a redaction-safe external billing fixture."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fixture(name: str) -> dict:
    model = "redacted-model"
    return {
        "name": name,
        "description": "Redaction-safe external cost case; replace only synthetic usage and reviewed expected values.",
        "metadata": {
            "requirement_ids": ["RC-EXTERNAL-CONFORMANCE"],
            "provider": "external",
            "surface": "external.chat_completions",
            "scenario": "conformance",
            "tags": ["conformance", "external", "redacted"],
            "expected_languages": ["python", "javascript", "go"],
        },
        "input": {
            "usage_ledger": {
                "schema_version": "0.1",
                "provider": "external",
                "surface": "external.chat_completions",
                "model": {"requested": model, "returned": model, "billed": model, "alias_resolution": "none"},
                "components": [{"name": "input_uncached_tokens", "quantity": "100", "unit": "token", "source_path": "$.usage.input_tokens"}],
                "raw_usage": {"input_tokens": 100},
            },
            "price_cards": [
                {
                    "schema_version": "0.1",
                    "id": "external:redacted-model:reviewed",
                    "provider": "external",
                    "surface": "external.chat_completions",
                    "model": model,
                    "components": [{"usage_component": "input_uncached_tokens", "unit": "token", "price": {"amount": "1", "currency": "USD", "per": "1000000"}}],
                    "source": {"name": "external-reviewed-fixture"},
                }
            ],
        },
        "expected": {
            "cost_ledger": {
                "schema_version": "0.1",
                "provider": "external",
                "surface": "external.chat_completions",
                "model": {"requested": model, "returned": model, "billed": model, "alias_resolution": "none"},
                "currency": "USD",
                "components": [{"name": "input_uncached_tokens", "quantity": "100", "unit": "token", "unit_price": "0.000001", "cost": "0.0001", "price_card_id": "external:redacted-model:reviewed", "discount_eligible": True}],
                "total": "0.0001",
                "price_sources": [{"name": "external-reviewed-fixture"}],
                "applied_discounts": [],
                "warnings": [],
            }
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="external-redacted-example")
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {output}; pass --force")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fixture(args.name), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    subprocess.run(["python3", "scripts/check_fixtures.py", "--fixture", str(output)], cwd=ROOT, check=True)
    print(f"Wrote and validated redaction-safe fixture: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
