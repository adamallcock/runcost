#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGE = ROOT / "packages" / "python"
if str(PYTHON_PACKAGE) not in sys.path:
    sys.path.insert(0, str(PYTHON_PACKAGE))

from runcost import (  # noqa: E402
    DEFAULT_PRICE_SOURCE_PRIORITY,
    calculate_cost,
    default_price_cards,
    default_source_cache,
)

CATALOG_PATHS = [
    ROOT / "packages" / "python" / "runcost" / "data" / "default-source-cache.json",
    ROOT / "packages" / "javascript" / "core" / "data" / "default-source-cache.json",
    ROOT / "packages" / "go" / "ledger" / "data" / "default-source-cache.json",
]

EXPECTED_SOURCES = {
    "llm-prices": "llm-prices",
    "litellm": "litellm",
    "openrouter": "openrouter-models",
    "models.dev": "models-dev",
    "xai-official": "official-snapshot",
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_catalog(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_files_match() -> dict:
    hashes = []
    for path in CATALOG_PATHS:
        assert_true(path.exists(), f"missing default catalog: {path.relative_to(ROOT)}")
        raw = path.read_bytes()
        hashes.append(hashlib.sha256(raw).hexdigest())
    assert_true(len(set(hashes)) == 1, "default catalog copies must be byte-identical across packages")
    return read_catalog(CATALOG_PATHS[0])


def check_catalog_shape(catalog: dict) -> None:
    assert_true(catalog.get("schema_version") == "0.1", "catalog schema_version must be 0.1")
    assert_true(catalog.get("name") == "runcost-default-source-cache", "catalog name mismatch")
    assert_true(catalog.get("source_priority") == DEFAULT_PRICE_SOURCE_PRIORITY, "catalog source priority mismatch")
    sources = catalog.get("sources")
    assert_true(isinstance(sources, list) and len(sources) == len(EXPECTED_SOURCES), "catalog must include the expected source entries")
    source_map = {source.get("name"): source for source in sources if isinstance(source, dict)}
    assert_true(set(source_map) == set(EXPECTED_SOURCES), f"unexpected catalog sources: {sorted(source_map)}")
    total_cards = 0
    for name, source_type in EXPECTED_SOURCES.items():
        source = source_map[name]
        assert_true(source.get("type") == source_type, f"{name} source type mismatch")
        assert_true(str(source.get("url", "")).startswith("https://"), f"{name} must retain source URL")
        assert_true(str(source.get("retrieved_at", "")).endswith("Z"), f"{name} must retain retrieved_at")
        assert_true(str(source.get("checksum", "")).startswith("sha256:"), f"{name} must retain sha256 checksum")
        cards = source.get("price_cards")
        assert_true(isinstance(cards, list) and cards, f"{name} must include price cards")
        total_cards += len(cards)
    metadata = catalog.get("metadata") or {}
    assert_true(metadata.get("source_count") == len(EXPECTED_SOURCES), "metadata source_count mismatch")
    assert_true(metadata.get("price_card_count") == total_cards, "metadata price_card_count mismatch")
    assert_true(total_cards >= 7000, f"default catalog should be broad, found only {total_cards} cards")


def check_language_loaders() -> None:
    python_catalog = default_source_cache()
    python_cards = default_price_cards()
    assert_true(python_catalog.get("metadata", {}).get("price_card_count") == len(python_cards), "Python default_price_cards count mismatch")

    js = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            (
                "import { defaultPriceCards, defaultSourceCache, DEFAULT_PRICE_SOURCE_PRIORITY } "
                f"from {json.dumps((ROOT / 'packages/javascript/core/index.js').as_uri())};"
                "const cache = defaultSourceCache();"
                "const cards = defaultPriceCards();"
                "if (cache.metadata.price_card_count !== cards.length) throw new Error('JS count mismatch');"
                "if (DEFAULT_PRICE_SOURCE_PRIORITY[0] !== 'xai-official') throw new Error('JS priority mismatch');"
                "console.log(cards.length);"
            ),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert_true(int(js.stdout.strip()) == len(python_cards), "JavaScript default_price_cards count mismatch")


def check_xai_aliases() -> None:
    cards = default_price_cards()
    official_cards = [
        card for card in cards
        if card.get("provider") == "xai" and (card.get("source") or {}).get("name") == "xai-official"
    ]
    by_model = {card.get("model"): card for card in official_cards}
    assert_true("grok-4.3" in by_model, "xAI official catalog must include grok-4.3")
    assert_true(by_model["grok-4.3"].get("aliases") == ["grok-4.3-latest", "grok-latest"], "grok-4.3 must only carry true rolling aliases")
    grok_components = {
        component.get("usage_component"): component
        for component in by_model["grok-4.3"].get("components", [])
        if isinstance(component, dict)
    }
    expected_tool_prices = {
        "web_search_units": ("search", "0.005"),
        "x_search_units": ("search", "0.005"),
        "code_interpreter_call_units": ("call", "0.005"),
        "attachment_search_units": ("call", "0.01"),
        "file_search_units": ("call", "0.0025"),
    }
    for component_name, (unit, amount) in expected_tool_prices.items():
        component = grok_components.get(component_name)
        assert_true(component is not None, f"xAI official catalog must include {component_name}")
        assert_true(component.get("unit") == unit, f"{component_name} unit mismatch")
        assert_true((component.get("price") or {}).get("amount") == amount, f"{component_name} price mismatch")
        assert_true((component.get("price") or {}).get("per") == "1", f"{component_name} must be priced per call/search")

    redirected_slugs = [
        "grok-3",
        "grok-3-latest",
        "grok-4",
        "grok-4-fast-reasoning",
        "grok-4-fast-reasoning-latest",
        "grok-4-1-fast-non-reasoning-latest",
    ]
    for slug in redirected_slugs:
        card = by_model.get(slug)
        assert_true(card is not None, f"xAI redirected slug {slug} must have its own price card")
        assert_true(slug not in by_model["grok-4.3"].get("aliases", []), f"xAI redirected slug {slug} must not be an alias on grok-4.3")
        official = (card.get("metadata") or {}).get("official_snapshot") or {}
        capabilities = official.get("capabilities") or {}
        assert_true(capabilities.get("redirect_target") == "grok-4.3", f"xAI redirected slug {slug} must record redirect target metadata")

    true_aliases = ["grok-4.3-latest", "grok-latest"]
    for alias in true_aliases:
        usage_ledger = {
            "schema_version": "0.1",
            "provider": "xai",
            "surface": "xai.chat",
            "model": {"requested": alias, "returned": alias, "billed": alias},
            "components": [
                {"name": "input_uncached_tokens", "quantity": "1000", "unit": "token", "source_path": "$.usage.input_tokens"},
                {"name": "output_text_tokens", "quantity": "1000", "unit": "token", "source_path": "$.usage.output_tokens"},
            ],
        }
        ledger = calculate_cost(
            usage_ledger=usage_ledger,
            price_cards=cards,
            price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
        )
        warning_codes = [warning["code"] for warning in ledger.get("warnings", [])]
        assert_true("unknown_model" not in warning_codes, f"xAI alias {alias} must resolve through the default catalog")
        assert_true(ledger["model"]["billed"] == "grok-4.3", f"xAI alias {alias} must bill as grok-4.3")
        assert_true(ledger["total"] != "0", f"xAI alias {alias} must produce a non-zero price")

    for slug in redirected_slugs:
        usage_ledger = {
            "schema_version": "0.1",
            "provider": "xai",
            "surface": "xai.chat",
            "model": {"requested": slug, "returned": slug, "billed": slug},
            "components": [
                {"name": "input_uncached_tokens", "quantity": "1000", "unit": "token", "source_path": "$.usage.input_tokens"},
                {"name": "output_text_tokens", "quantity": "1000", "unit": "token", "source_path": "$.usage.output_tokens"},
            ],
        }
        ledger = calculate_cost(
            usage_ledger=usage_ledger,
            price_cards=cards,
            price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
        )
        warning_codes = [warning["code"] for warning in ledger.get("warnings", [])]
        assert_true("unknown_model" not in warning_codes, f"xAI redirected slug {slug} must resolve through the default catalog")
        assert_true(ledger["model"]["billed"] == slug, f"xAI redirected slug {slug} must not masquerade as grok-4.3 alias")
        assert_true(ledger["total"] == "0.00375", f"xAI redirected slug {slug} must use Grok 4.3 token rates")


def main() -> int:
    catalog = check_files_match()
    check_catalog_shape(catalog)
    check_language_loaders()
    check_xai_aliases()
    print(f"Default price catalog checks passed for {catalog['metadata']['price_card_count']} price cards.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Default price catalog check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
