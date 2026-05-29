#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.refresh_price_sources import (  # noqa: E402
    PRESETS,
    build_source_cache,
    load_json_snapshot,
    read_snapshot,
    utc_now,
)

DEFAULT_SOURCES: list[dict[str, str]] = [
    {
        "preset": "llm-prices-current",
        "name": "llm-prices",
        "license": "source-specific",
    },
    {
        "source_type": "litellm",
        "name": "litellm",
        "url": "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
        "license": "MIT",
    },
    {
        "preset": "openrouter-models",
        "name": "openrouter",
        "license": "source-specific",
    },
    {
        "preset": "models-dev",
        "name": "models.dev",
        "license": "MIT",
    },
]

DEFAULT_OUTPUTS = [
    ROOT / "packages" / "python" / "runcost" / "data" / "default-source-cache.json",
    ROOT / "packages" / "javascript" / "core" / "data" / "default-source-cache.json",
    ROOT / "packages" / "go" / "ledger" / "data" / "default-source-cache.json",
]

DEFAULT_PRIORITY = ["llm-prices", "models.dev", "litellm", "openrouter"]


def source_config(raw_config: dict[str, str]) -> dict[str, str]:
    preset = PRESETS.get(raw_config.get("preset", ""), {})
    source_type = raw_config.get("source_type") or preset.get("source_type")
    url = raw_config.get("url") or preset.get("url")
    if not source_type or not url:
        raise ValueError(f"default source is missing source_type/url: {raw_config}")
    return {
        **raw_config,
        "source_type": source_type,
        "url": url,
    }


def build_catalog(retrieved_at: str | None = None, generated_at: str | None = None) -> dict[str, Any]:
    retrieved = retrieved_at or utc_now()
    generated = generated_at or retrieved
    sources = []
    for raw_config in DEFAULT_SOURCES:
        config = source_config(raw_config)
        raw = read_snapshot(None, config["url"])
        snapshot = load_json_snapshot(raw, config["url"])
        envelope = build_source_cache(
            raw,
            snapshot,
            config["source_type"],
            config["url"],
            retrieved_at=retrieved,
            generated_at=generated,
            source_name=config["name"],
        )
        source = envelope["sources"][0]
        if config.get("license"):
            source["license"] = config["license"]
        sources.append(source)

    price_card_count = sum(len(source.get("price_cards", [])) for source in sources)
    return {
        "schema_version": "0.1",
        "name": "runcost-default-source-cache",
        "description": "Reviewed default price catalog generated from public source adapters.",
        "generated_at": generated,
        "reviewed_at": generated,
        "source_priority": DEFAULT_PRIORITY,
        "sources": sources,
        "metadata": {
            "generator": "scripts/build_default_price_catalog.py",
            "source_count": len(sources),
            "price_card_count": price_card_count,
            "package_data": True,
        },
    }


def write_catalog(catalog: dict[str, Any], outputs: list[Path]) -> None:
    encoded = json.dumps(catalog, sort_keys=True, separators=(",", ":")) + "\n"
    for output in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the bundled RunCost default source-cache catalog.")
    parser.add_argument("--retrieved-at", help="override retrieved_at for all sources")
    parser.add_argument("--generated-at", help="override generated_at/reviewed_at")
    parser.add_argument("--output", action="append", type=Path, help="extra output path; defaults to all package data locations")
    parser.add_argument("--primary-only", action="store_true", help="write only the first/default output plus any --output paths")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog = build_catalog(retrieved_at=args.retrieved_at, generated_at=args.generated_at)
    outputs = [DEFAULT_OUTPUTS[0]] if args.primary_only else list(DEFAULT_OUTPUTS)
    outputs.extend(args.output or [])
    write_catalog(catalog, outputs)
    for output in outputs:
        print(f"Wrote {catalog['metadata']['price_card_count']} price cards to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
