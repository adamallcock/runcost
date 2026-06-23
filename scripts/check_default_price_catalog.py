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
    from_response,
)

CATALOG_PATHS = [
    ROOT / "packages" / "python" / "runcost" / "data" / "default-source-cache.json",
    ROOT / "packages" / "javascript" / "core" / "data" / "default-source-cache.json",
    ROOT / "packages" / "go" / "ledger" / "data" / "default-source-cache.json",
]

EXPECTED_SOURCES = {
    "anthropic-official": "official-snapshot",
    "google-official": "official-snapshot",
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
                "if (DEFAULT_PRICE_SOURCE_PRIORITY[0] !== 'anthropic-official') throw new Error('JS priority mismatch');"
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


def check_anthropic_fable_mythos() -> None:
    cards = default_price_cards()
    official_cards = [
        card for card in cards
        if card.get("provider") == "anthropic" and (card.get("source") or {}).get("name") == "anthropic-official"
    ]
    by_model = {card.get("model"): card for card in official_cards}
    for model in ("claude-fable-5", "claude-mythos-5"):
        assert_true(model in by_model, f"Anthropic official catalog must include {model}")
        components = {
            component.get("usage_component"): component
            for component in by_model[model].get("components", [])
            if isinstance(component, dict)
        }
        expected_components = {
            "input_uncached_tokens": "10",
            "input_cache_write_tokens": "12.50",
            "input_cache_write_1h_tokens": "20",
            "input_cache_read_tokens": "1",
            "output_text_tokens": "50",
        }
        for component_name, amount in expected_components.items():
            component = components.get(component_name)
            assert_true(component is not None, f"{model} official catalog must include {component_name}")
            assert_true((component.get("price") or {}).get("amount") == amount, f"{model} {component_name} amount mismatch")
            assert_true((component.get("price") or {}).get("per") == "1000000", f"{model} {component_name} must be priced per MTok")

        usage_ledger = {
            "schema_version": "0.1",
            "provider": "anthropic",
            "surface": "anthropic.messages",
            "model": {"requested": model, "returned": model, "billed": model, "alias_resolution": "none"},
            "components": [
                {"name": "input_uncached_tokens", "quantity": "1000", "unit": "token"},
                {"name": "input_cache_write_tokens", "quantity": "200", "unit": "token"},
                {"name": "input_cache_write_1h_tokens", "quantity": "100", "unit": "token"},
                {"name": "input_cache_read_tokens", "quantity": "500", "unit": "token"},
                {"name": "output_text_tokens", "quantity": "200", "unit": "token"},
            ],
        }
        ledger = calculate_cost(
            usage_ledger=usage_ledger,
            price_cards=cards,
            price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
        )
        warning_codes = [warning["code"] for warning in ledger.get("warnings", [])]
        assert_true("component_unpriced" not in warning_codes, f"{model} standard token/cache components must price")
        selected_sources = {source.get("name") for source in ledger.get("price_sources", [])}
        assert_true(selected_sources == {"anthropic-official"}, f"{model} must use anthropic official source")


def check_google_live_translate() -> None:
    cards = default_price_cards()
    official_cards = [
        card for card in cards
        if card.get("provider") == "google" and (card.get("source") or {}).get("name") == "google-official"
    ]
    by_model = {card.get("model"): card for card in official_cards}
    model = "gemini-3.5-live-translate-preview"
    assert_true(model in by_model, "Google official catalog must include Gemini 3.5 Live Translate")
    card = by_model[model]
    assert_true(card.get("surface") == "google.gemini.live", "Gemini Live Translate must use google.gemini.live surface")
    components = {
        component.get("usage_component"): component
        for component in card.get("components", [])
        if isinstance(component, dict)
    }
    expected_components = {
        "input_audio_tokens": "3.50",
        "output_audio_tokens": "21.00",
    }
    for component_name, amount in expected_components.items():
        component = components.get(component_name)
        assert_true(component is not None, f"Gemini Live Translate official catalog must include {component_name}")
        assert_true((component.get("price") or {}).get("amount") == amount, f"Gemini Live Translate {component_name} amount mismatch")
        assert_true((component.get("price") or {}).get("per") == "1000000", f"Gemini Live Translate {component_name} must be priced per MTok")

    usage_ledger = {
        "schema_version": "0.1",
        "provider": "google",
        "surface": "google.gemini.live",
        "model": {"requested": model, "returned": model, "billed": model, "alias_resolution": "none"},
        "components": [
            {"name": "input_audio_tokens", "quantity": "250", "unit": "token"},
            {"name": "output_audio_tokens", "quantity": "500", "unit": "token"},
        ],
    }
    ledger = calculate_cost(
        usage_ledger=usage_ledger,
        price_cards=cards,
        price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
    )
    warning_codes = [warning["code"] for warning in ledger.get("warnings", [])]
    assert_true("component_unpriced" not in warning_codes, "Gemini Live Translate audio components must price")
    assert_true(ledger["total"] == "0.011375", "Gemini Live Translate sample total mismatch")
    selected_sources = {source.get("name") for source in ledger.get("price_sources", [])}
    assert_true(selected_sources == {"google-official"}, "Gemini Live Translate must use google official source")

    raw_ledger = from_response(
        response={
            "chunks": [
                {"serverContent": {"modelTurn": {"parts": [{"inlineData": {"mimeType": "audio/pcm;rate=24000", "data": "..."}}]}}},
                {
                    "modelVersion": model,
                    "serverContent": {"turnComplete": True},
                    "usageMetadata": {
                        "promptTokenCount": 250,
                        "promptTokensDetails": [{"modality": "AUDIO", "tokenCount": 250}],
                        "responseTokenCount": 500,
                        "responseTokensDetails": [{"modality": "AUDIO", "tokenCount": 500}],
                        "totalTokenCount": 750,
                    },
                },
            ]
        },
        provider="google",
        surface="google.gemini.live",
        model=model,
        price_cards=cards,
        price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
    )
    assert_true(raw_ledger["total"] == "0.011375", "Gemini Live Translate raw extraction and default pricing total mismatch")
    raw_components = {component.get("name"): component for component in raw_ledger.get("components", [])}
    assert_true(raw_components.get("input_audio_tokens", {}).get("quantity") == "250", "Gemini Live raw input audio extraction mismatch")
    assert_true(raw_components.get("output_audio_tokens", {}).get("quantity") == "500", "Gemini Live raw output audio extraction mismatch")

    aggregate_ledger = from_response(
        response={
            "modelVersion": model,
            "usageMetadata": {
                "promptTokenCount": 250,
                "responseTokenCount": 500,
                "thoughtsTokenCount": 25,
                "totalTokenCount": 775,
            },
        },
        provider="google",
        surface="google.gemini.live",
        model=model,
        price_cards=cards,
        price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
    )
    assert_true(aggregate_ledger["total"] == "0.0119", "Gemini Live aggregate fallback and thinking total mismatch")
    aggregate_components = {component.get("name"): component for component in aggregate_ledger.get("components", [])}
    assert_true(aggregate_components.get("input_audio_tokens", {}).get("quantity") == "250", "Gemini Live aggregate input must fall back to audio")
    assert_true(aggregate_components.get("output_audio_tokens", {}).get("quantity") == "500", "Gemini Live aggregate output must fall back to audio")
    reasoning_metadata = aggregate_components.get("output_reasoning_tokens", {}).get("metadata") or {}
    assert_true(reasoning_metadata.get("priced_as_component") == "output_audio_tokens", "Gemini Live thinking must price at output audio rate")

    transcript_ledger = from_response(
        response={
            "modelVersion": model,
            "usageMetadata": {
                "promptTokenCount": 250,
                "promptTokensDetails": [{"modality": "AUDIO", "tokenCount": 250}],
                "responseTokenCount": 550,
                "responseTokensDetails": [
                    {"modality": "AUDIO", "tokenCount": 500},
                    {"modality": "TEXT", "tokenCount": 50},
                ],
                "totalTokenCount": 800,
            },
        },
        provider="google",
        surface="google.gemini.live",
        model=model,
        price_cards=cards,
        price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
    )
    assert_true(transcript_ledger["total"] == "0.011375", "Gemini Live transcript sample audio total mismatch")
    transcript_warnings = transcript_ledger.get("warnings", [])
    assert_true(
        any(
            warning.get("code") == "source_capability_unsupported"
            and (warning.get("metadata") or {}).get("component") == "output_text_tokens"
            for warning in transcript_warnings
        ),
        "Gemini Live transcript text output must warn as unsupported by the official audio-token price card",
    )


def check_google_service_tiers() -> None:
    cards = default_price_cards()
    official_cards = [
        card for card in cards
        if card.get("provider") == "google" and (card.get("source") or {}).get("name") == "google-official"
    ]
    by_id = {card.get("id"): card for card in official_cards}
    expected_ids = {
        "google:gemini-3.5-flash:standard:official-snapshot",
        "google:gemini-3.5-flash:flex:official-snapshot",
        "google:gemini-3.5-flash:priority:official-snapshot",
        "google:gemini-3.1-flash-lite:standard:official-snapshot",
        "google:gemini-3.1-flash-lite:flex:official-snapshot",
        "google:gemini-3.1-flash-lite:priority:official-snapshot",
        "google:gemini-3.1-pro-preview:standard:official-snapshot",
        "google:gemini-3.1-pro-preview:flex:official-snapshot",
        "google:gemini-3.1-pro-preview:priority:official-snapshot",
        "google:gemini-3-flash-preview:standard:official-snapshot",
        "google:gemini-3-flash-preview:flex:official-snapshot",
        "google:gemini-3-flash-preview:priority:official-snapshot",
        "google:gemini-2.5-pro:standard:official-snapshot",
        "google:gemini-2.5-pro:flex:official-snapshot",
        "google:gemini-2.5-pro:priority:official-snapshot",
        "google:gemini-2.5-flash:standard:official-snapshot",
        "google:gemini-2.5-flash:flex:official-snapshot",
        "google:gemini-2.5-flash:priority:official-snapshot",
        "google:gemini-2.5-flash-lite:standard:official-snapshot",
        "google:gemini-2.5-flash-lite:flex:official-snapshot",
        "google:gemini-2.5-flash-lite:priority:official-snapshot",
    }
    missing = sorted(expected_ids - set(by_id))
    assert_true(not missing, f"Google official catalog missing service-tier cards: {missing}")

    standard_ledger = from_response(
        response={
            "modelVersion": "gemini-3.5-flash",
            "usageMetadata": {
                "promptTokenCount": 1000,
                "candidatesTokenCount": 100,
                "totalTokenCount": 1100,
            },
        },
        provider="google",
        surface="google.gemini.generate_content",
        model="gemini-3.5-flash",
        price_cards=cards,
        price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
    )
    standard_components = {component.get("name"): component for component in standard_ledger.get("components", [])}
    assert_true(standard_ledger["total"] == "0.0024", "Gemini 3.5 Flash default standard total mismatch")
    assert_true(
        standard_components["input_uncached_tokens"]["price_card_id"] == "google:gemini-3.5-flash:standard:official-snapshot",
        "Gemini 3.5 Flash absent serviceTier must select Standard official card",
    )

    flex_ledger = from_response(
        response={
            "modelVersion": "gemini-3.5-flash",
            "usageMetadata": {
                "promptTokenCount": 1000,
                "candidatesTokenCount": 100,
                "totalTokenCount": 1100,
                "serviceTier": "flex",
            },
        },
        provider="google",
        surface="google.gemini.generate_content",
        model="gemini-3.5-flash",
        price_cards=cards,
        price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
    )
    flex_components = {component.get("name"): component for component in flex_ledger.get("components", [])}
    assert_true(flex_ledger["total"] == "0.0012", "Gemini 3.5 Flash flex total mismatch")
    assert_true(
        flex_components["input_uncached_tokens"]["price_card_id"] == "google:gemini-3.5-flash:flex:official-snapshot",
        "Gemini 3.5 Flash serviceTier flex must select Flex official card",
    )

    priority_long_context = from_response(
        response={
            "modelVersion": "gemini-2.5-pro",
            "usageMetadata": {
                "promptTokenCount": 200001,
                "candidatesTokenCount": 100,
                "totalTokenCount": 200101,
                "serviceTier": "priority",
            },
        },
        provider="google",
        surface="google.gemini.generate_content",
        model="gemini-2.5-pro",
        price_cards=cards,
        price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
    )
    priority_components = {component.get("name"): component for component in priority_long_context.get("components", [])}
    assert_true(priority_long_context["total"] == "0.9027045", "Gemini 2.5 Pro priority long-context total mismatch")
    assert_true(
        priority_components["input_uncached_tokens"]["unit_price"] == "0.0000045",
        "Gemini 2.5 Pro priority long-context input price mismatch",
    )
    assert_true(
        priority_components["output_text_tokens"]["unit_price"] == "0.000027",
        "Gemini 2.5 Pro priority long-context output price mismatch",
    )

    flash_flex = from_response(
        response={
            "modelVersion": "gemini-2.5-flash",
            "usageMetadata": {
                "promptTokenCount": 1000,
                "candidatesTokenCount": 100,
                "totalTokenCount": 1100,
                "serviceTier": "flex",
            },
        },
        provider="google",
        surface="google.gemini.generate_content",
        model="gemini-2.5-flash",
        price_cards=cards,
        price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
    )
    flash_flex_components = {component.get("name"): component for component in flash_flex.get("components", [])}
    assert_true(flash_flex["total"] == "0.000275", "Gemini 2.5 Flash flex total mismatch")
    assert_true(
        flash_flex_components["input_uncached_tokens"]["price_card_id"] == "google:gemini-2.5-flash:flex:official-snapshot",
        "Gemini 2.5 Flash serviceTier flex must select Flex official card",
    )

    flash_lite_priority = from_response(
        response={
            "modelVersion": "gemini-3.1-flash-lite",
            "usageMetadata": {
                "promptTokenCount": 1000,
                "candidatesTokenCount": 100,
                "totalTokenCount": 1100,
                "serviceTier": "priority",
            },
        },
        provider="google",
        surface="google.gemini.generate_content",
        model="gemini-3.1-flash-lite",
        price_cards=cards,
        price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
    )
    flash_lite_priority_components = {component.get("name"): component for component in flash_lite_priority.get("components", [])}
    assert_true(flash_lite_priority["total"] == "0.00072", "Gemini 3.1 Flash-Lite priority total mismatch")
    assert_true(
        flash_lite_priority_components["input_uncached_tokens"]["price_card_id"] == "google:gemini-3.1-flash-lite:priority:official-snapshot",
        "Gemini 3.1 Flash-Lite serviceTier priority must select Priority official card",
    )


def main() -> int:
    catalog = check_files_match()
    check_catalog_shape(catalog)
    check_language_loaders()
    check_xai_aliases()
    check_anthropic_fable_mythos()
    check_google_service_tiers()
    check_google_live_translate()
    print(f"Default price catalog checks passed for {catalog['metadata']['price_card_count']} price cards.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Default price catalog check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
