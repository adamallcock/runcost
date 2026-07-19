#!/usr/bin/env python3
"""Verify caller-owned manifest/shard tooling and one-byte mutation detection."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "python"))

from runcost import verify_catalog_manifest  # noqa: E402
from scripts.build_price_catalog_artifacts import build_catalog_artifacts  # noqa: E402


def fixture_source_cache() -> dict:
    cards = []
    for provider, model, amount in (("openai", "fixture-a", "1"), ("anthropic", "fixture-b", "2")):
        cards.append(
            {
                "schema_version": "0.1",
                "id": f"{provider}:{model}:fixture",
                "provider": provider,
                "model": model,
                "components": [
                    {"usage_component": "input_uncached_tokens", "unit": "token", "price": {"amount": amount, "currency": "USD", "per": "1000000"}}
                ],
                "source": {"name": "fixture", "url": "https://example.com/prices", "retrieved_at": "2026-07-18T00:00:00Z"},
            }
        )
    return {
        "schema_version": "0.1",
        "generated_at": "2026-07-18T00:00:00Z",
        "sources": [{"name": "fixture", "type": "user-pricing", "url": "https://example.com/prices", "retrieved_at": "2026-07-18T00:00:00Z", "price_cards": cards}],
    }


def main() -> int:
    if verify_catalog_manifest({}, root=ROOT)["valid"]:
        raise SystemExit("empty catalog manifest was accepted")
    if verify_catalog_manifest({"algorithm": "md5", "catalog": {}}, root=ROOT)["valid"]:
        raise SystemExit("unsupported catalog manifest algorithm was accepted")

    with tempfile.TemporaryDirectory(prefix="runcost-manifest-") as directory:
        output = Path(directory)
        manifest = build_catalog_artifacts(fixture_source_cache(), output)
        if len(manifest["shards"]) != 2 or not verify_catalog_manifest(manifest, root=output)["valid"]:
            raise SystemExit("caller-owned catalog artifacts did not verify")
        catalog = output / "catalog.json"
        data = bytearray(catalog.read_bytes())
        data[len(data) // 2] ^= 1
        catalog.write_bytes(data)
        mutation = verify_catalog_manifest(manifest, root=output)
        if mutation["valid"] or mutation["artifacts"][0]["matches"]:
            raise SystemExit("one-byte catalog mutation was not detected")
        catalog.write_bytes((json.dumps(fixture_source_cache(), sort_keys=True, separators=(",", ":")) + "\n").encode())

        manifest_path = output / "catalog-manifest.json"
        python_cli = subprocess.run(
            ["python3", "-m", "runcost.cli", "catalog-verify", str(manifest_path)],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "packages" / "python")},
            check=True,
            text=True,
            capture_output=True,
        )
        javascript_cli = subprocess.run(
            ["node", "packages/javascript/core/cli.js", "catalog-verify", str(manifest_path)],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        if not json.loads(python_cli.stdout)["valid"] or not json.loads(javascript_cli.stdout)["valid"]:
            raise SystemExit("catalog verification CLI did not report valid")
    subprocess.run(
        [
            "node", "--input-type=module", "-e",
            "import {verifyCatalogManifest} from './packages/javascript/core/index.js';"
            "if((await verifyCatalogManifest({},{})).valid)throw new Error('empty manifest accepted');"
            "if((await verifyCatalogManifest({algorithm:'md5',catalog:{}},{})).valid)throw new Error('algorithm accepted');",
        ],
        cwd=ROOT,
        check=True,
    )
    print("Caller-owned catalog, two provider shards, mutation detection, and both CLIs passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
