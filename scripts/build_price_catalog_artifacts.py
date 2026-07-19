#!/usr/bin/env python3
"""Build caller-owned catalog artifacts from a RunCost source-cache envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def artifact(path: str, encoded: bytes, card_count: int, provider: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": path,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "bytes": len(encoded),
        "price_card_count": card_count,
    }
    if provider is not None:
        result["provider"] = provider
    return result


def provider_slug(provider: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", provider.lower()).strip("-") or "unknown"


def source_cards(source_cache: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    entries = source_cache.get("sources") if isinstance(source_cache.get("sources"), list) else [source_cache]
    for source in entries:
        if not isinstance(source, dict):
            continue
        raw_cards = source.get("price_cards", source.get("priceCards", source.get("cards", [])))
        cards.extend(card for card in raw_cards if isinstance(card, dict))
    return cards


def provider_source_cache(source_cache: dict[str, Any], provider: str) -> dict[str, Any]:
    result = {key: value for key, value in source_cache.items() if key != "sources"}
    entries = source_cache.get("sources") if isinstance(source_cache.get("sources"), list) else [source_cache]
    sources = []
    for source in entries:
        if not isinstance(source, dict):
            continue
        raw_cards = source.get("price_cards", source.get("priceCards", source.get("cards", [])))
        cards = [card for card in raw_cards if isinstance(card, dict) and str(card.get("provider") or "unknown") == provider]
        if cards:
            entry = dict(source)
            entry["price_cards"] = cards
            entry.pop("priceCards", None)
            entry.pop("cards", None)
            sources.append(entry)
    result["sources"] = sources
    metadata = dict(result.get("metadata") or {})
    metadata.update({"provider_shard": True, "price_card_count": sum(len(source["price_cards"]) for source in sources)})
    result["metadata"] = metadata
    return result


def build_catalog_artifacts(source_cache: dict[str, Any], output_dir: Path, *, catalog_name: str = "catalog.json") -> dict[str, Any]:
    if source_cache.get("schema_version") != "0.1":
        raise ValueError("source cache must have schema_version 0.1")
    cards = source_cards(source_cache)
    if not cards:
        raise ValueError("source cache contains no price cards")
    if Path(catalog_name).name != catalog_name or not catalog_name.endswith(".json"):
        raise ValueError("catalog_name must be a JSON filename without path separators")

    output_dir.mkdir(parents=True, exist_ok=True)
    catalog_bytes = canonical_bytes(source_cache)
    (output_dir / catalog_name).write_bytes(catalog_bytes)
    providers_dir = output_dir / "providers"
    providers_dir.mkdir(parents=True, exist_ok=True)
    expected_names: set[str] = set()
    shards = []
    providers = sorted({str(card.get("provider") or "unknown") for card in cards})
    for provider in providers:
        shard = provider_source_cache(source_cache, provider)
        encoded = canonical_bytes(shard)
        filename = f"{provider_slug(provider)}.json"
        expected_names.add(filename)
        (providers_dir / filename).write_bytes(encoded)
        count = sum(len(source.get("price_cards", [])) for source in shard["sources"])
        shards.append(artifact(f"providers/{filename}", encoded, count, provider))
    for stale in providers_dir.glob("*.json"):
        if stale.name not in expected_names:
            stale.unlink()
    manifest = {
        "schema_version": "0.1",
        "algorithm": "sha256",
        "catalog": artifact(catalog_name, catalog_bytes, len(cards)),
        "shards": shards,
    }
    (output_dir / "catalog-manifest.json").write_bytes(canonical_bytes(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build caller-owned catalog and provider shards from a source-cache JSON file.")
    parser.add_argument("--source-cache", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--catalog-name", default="catalog.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_cache = json.loads(args.source_cache.read_text(encoding="utf-8"))
    manifest = build_catalog_artifacts(source_cache, args.output_dir, catalog_name=args.catalog_name)
    print(f"Wrote {manifest['catalog']['price_card_count']} price cards and {len(manifest['shards'])} provider shards to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
