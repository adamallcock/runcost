#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "PROJECT_PLAN.md",
    "PROGRESS_TRACKER.md",
    "docs/reference/api-reference.md",
    "docs/reference/aggregation-and-streaming.md",
    "docs/reference/custom-pricing-and-discounts.md",
    "docs/reference/debug-trace.md",
    "docs/reports/fixture-coverage.md",
    "docs/guides/package-installation.md",
    "docs/guides/quickstart.md",
    "docs/process/release-process.md",
    "docs/reference/source-adapters.md",
    "docs/reference/supported-surfaces.md",
    "docs/reference/warnings-and-limitations.md",
    "docs/decisions/polyglot-toolchain-decision.md",
    "docs/notes/api-parity-matrix.md",
    "docs/notes/provider-extractor-notes.md",
    "docs/notes/framework-adapter-notes.md",
    "scripts/check_fixture_coverage.py",
    "scripts/check_fixture_generator.py",
    "scripts/check_package_installs.py",
    "scripts/check_release_readiness.py",
    "scripts/check_schema_taxonomy.py",
    "scripts/check_source_refresh.py",
    "scripts/create_fixture.py",
    "scripts/refresh_price_sources.py",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "packages/javascript/core/index.d.ts",
    "packages/python/runcost/types.py",
    "schemas/debug-trace.schema.json",
    "schemas/fixture.schema.json",
    "schemas/taxonomy.json",
    "packages/go/ledger/example_test.go",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
]

PUBLIC_API_NAMES = [
    "calculate_cost",
    "calculateCost",
    "CalculateCost",
    "CalculateCostWithOptions",
    "from_response",
    "fromResponse",
    "FromResponse",
    "aggregate_cost_ledgers",
    "aggregateCostLedgers",
    "AggregateCostLedgers",
    "from_langchain_message",
    "fromLangChainMessage",
    "FromLangChainMessage",
    "track_langchain_costs",
    "RunCostLangChainCallback",
    "from_vercel_ai_sdk_result",
    "fromVercelAISDKResult",
    "FromVercelAISDKResult",
    "createRunCostVercelMiddleware",
    "from_llamaindex_token_counter",
    "fromLlamaIndexTokenCounter",
    "FromLlamaIndexTokenCounter",
    "from_haystack_generator_result",
    "fromHaystackGeneratorResult",
    "FromHaystackGeneratorResult",
    "from_litellm_response",
    "fromLiteLLMResponse",
    "FromLiteLLMResponse",
    "from_ag2_usage_summary",
    "fromAG2UsageSummary",
    "FromAG2UsageSummary",
    "DebugTrace",
    "debug_trace",
    "debugTrace",
    "extract_gemini_generate_content_usage",
    "extractGeminiGenerateContentUsage",
    "extractBedrockConverseUsage",
    "extract_bedrock_converse_usage",
    "extractCohereChatUsage",
    "extract_cohere_chat_usage",
    "extractLangChainChatUsage",
    "extract_langchain_chat_usage",
    "extractVercelAISDKUsage",
    "extract_vercel_ai_sdk_usage",
    "extractLlamaIndexTokenCounterUsage",
    "extract_llamaindex_token_counter_usage",
    "extractHaystackGeneratorUsage",
    "extract_haystack_generator_usage",
    "extractLiteLLMProxyResponseUsage",
    "extract_litellm_proxy_response_usage",
    "extractAG2UsageSummaryUsage",
    "extract_ag2_usage_summary_usage",
    "extractOpenRouterChatCompletionsUsage",
    "extract_openrouter_chat_completions_usage",
    "extractOpenAICompatibleChatCompletionsUsage",
    "extract_openai_compatible_chat_completions_usage",
    "price_cards_from_litellm",
    "priceCardsFromLiteLLM",
    "PriceCardsFromLiteLLM",
    "price_cards_from_models_dev",
    "priceCardsFromModelsDev",
    "PriceCardsFromModelsDev",
    "price_cards_from_official_snapshot",
    "priceCardsFromOfficialSnapshot",
    "PriceCardsFromOfficialSnapshot",
    "price_cards_from_openrouter_models",
    "priceCardsFromOpenRouterModels",
    "PriceCardsFromOpenRouterModels",
    "price_cards_from_portkey",
    "priceCardsFromPortkey",
    "PriceCardsFromPortkey",
    "price_cards_from_source_cache",
    "priceCardsFromSourceCache",
    "PriceCardsFromSourceCache",
    "price_cards_from_user_pricing",
    "priceCardsFromUserPricing",
    "PriceCardsFromUserPricing",
    "price_cards_from_helicone",
    "priceCardsFromHelicone",
    "PriceCardsFromHelicone",
    "price_cards_from_json_file",
    "priceCardsFromJSONFile",
    "PriceCardsFromJSONFile",
    "price_cards_from_yaml_file",
    "priceCardsFromYAMLFile",
    "PriceCardsFromYAMLFile",
]


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_required_files() -> None:
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        assert_true(path.exists(), f"required file is missing: {relative}")


def check_json_files() -> None:
    for path in sorted(ROOT.rglob("*.json")):
        if "node_modules" in path.parts:
            continue
        try:
            load_json(path)
        except json.JSONDecodeError as exc:
            relative = path.relative_to(ROOT)
            raise AssertionError(f"{relative}: invalid JSON: {exc}") from exc


def check_package_metadata() -> None:
    root_package = load_json(ROOT / "package.json")
    scripts = root_package.get("scripts", {})
    assert_true("check_fixtures.py" in scripts.get("test", ""), "root npm test must run fixture checks")
    assert_true(
        "check_fixture_generator.py" in scripts.get("test", ""),
        "root npm test must run fixture generator checks",
    )
    assert_true(
        "check_schema_taxonomy.py" in scripts.get("test", ""),
        "root npm test must run schema taxonomy checks",
    )
    assert_true(
        "check_source_refresh.py" in scripts.get("test", ""),
        "root npm test must run source refresh command checks",
    )
    assert_true("check_fixture_coverage.py" in scripts.get("test", ""), "root npm test must run fixture coverage checks")
    assert_true(
        "check_fixture_coverage.py" in scripts.get("check:coverage", ""),
        "root check:coverage must run fixture coverage checks",
    )
    assert_true("go test ./packages/go/..." in scripts.get("test", ""), "root npm test must run Go tests")
    assert_true(
        "check_project_hygiene.py" in scripts.get("test", ""),
        "root npm test must run project hygiene checks",
    )
    assert_true(
        "check_package_installs.py" in scripts.get("check:packages", ""),
        "root check:packages must run clean package install checks",
    )
    assert_true(
        "check_release_readiness.py" in scripts.get("check:release", ""),
        "root check:release must run release readiness checks",
    )
    assert_true(
        "check_schema_taxonomy.py" in scripts.get("check:taxonomy", ""),
        "root check:taxonomy must run schema taxonomy checks",
    )
    assert_true("create_fixture.py" in scripts.get("fixture:new", ""), "root fixture:new must run fixture generator")
    assert_true(
        "refresh_price_sources.py" in scripts.get("prices:refresh", ""),
        "root prices:refresh must run source refresh command",
    )

    js_package_path = ROOT / "packages/javascript/core/package.json"
    js_package = load_json(js_package_path)
    types_path = ROOT / "packages/javascript/core" / js_package.get("types", "")
    assert_true(types_path.exists(), "JavaScript package types field must point to an existing file")
    exports = js_package.get("exports", {}).get(".", {})
    assert_true(exports.get("types") == "./index.d.ts", "JavaScript package exports must expose index.d.ts")
    assert_true(not js_package.get("private", False), "JavaScript package must be publishable")
    assert_true("files" in js_package, "JavaScript package must define a publish file allowlist")
    assert_true(js_package.get("license") == "MIT", "JavaScript package must declare MIT license")


def check_public_api_artifacts() -> None:
    parity = (ROOT / "docs/notes/api-parity-matrix.md").read_text(encoding="utf-8")
    typescript = (ROOT / "packages/javascript/core/index.d.ts").read_text(encoding="utf-8")
    python_init = (ROOT / "packages/python/runcost/__init__.py").read_text(encoding="utf-8")
    python_types = (ROOT / "packages/python/runcost/types.py").read_text(encoding="utf-8")
    go_source = (ROOT / "packages/go/ledger/ledger.go").read_text(encoding="utf-8")
    go_examples = (ROOT / "packages/go/ledger/example_test.go").read_text(encoding="utf-8")

    for name in PUBLIC_API_NAMES:
        assert_true(name in parity, f"API parity matrix missing {name}")

    for exported in [
        "calculateCost",
        "aggregateCostLedgers",
        "fromResponse",
        "fromLangChainMessage",
        "createRunCostVercelMiddleware",
        "fromVercelAISDKResult",
        "fromLlamaIndexTokenCounter",
        "fromHaystackGeneratorResult",
        "fromLiteLLMResponse",
        "fromAG2UsageSummary",
        "priceCardsFromLlmPrices",
        "priceCardsFromLiteLLM",
        "priceCardsFromModelsDev",
        "priceCardsFromOfficialSnapshot",
        "priceCardsFromOpenRouterModels",
        "priceCardsFromPortkey",
        "priceCardsFromSourceCache",
        "priceCardsFromUserPricing",
        "priceCardsFromHelicone",
        "priceCardsFromJSONFile",
        "priceCardsFromYAMLFile",
        "extractOpenAICompatibleChatCompletionsUsage",
        "extractCohereChatUsage",
        "extractLangChainChatUsage",
        "extractVercelAISDKUsage",
        "extractLlamaIndexTokenCounterUsage",
        "extractHaystackGeneratorUsage",
        "extractLiteLLMProxyResponseUsage",
        "extractAG2UsageSummaryUsage",
        "UsageLedger",
        "PriceCard",
        "CostLedger",
        "DebugTrace",
    ]:
        assert_true(exported in typescript, f"TypeScript declarations missing {exported}")

    for exported in [
        "UsageLedger",
        "PriceCard",
        "DiscountPolicy",
        "CostLedger",
        "DebugTrace",
        "calculate_cost",
        "aggregate_cost_ledgers",
        "from_response",
        "from_langchain_message",
        "track_langchain_costs",
        "RunCostLangChainCallback",
        "from_vercel_ai_sdk_result",
        "from_llamaindex_token_counter",
        "from_haystack_generator_result",
        "from_litellm_response",
        "from_ag2_usage_summary",
        "price_cards_from_litellm",
        "price_cards_from_models_dev",
        "price_cards_from_official_snapshot",
        "price_cards_from_openrouter_models",
        "price_cards_from_portkey",
        "price_cards_from_source_cache",
        "price_cards_from_user_pricing",
        "price_cards_from_helicone",
        "price_cards_from_json_file",
        "price_cards_from_yaml_file",
        "extract_openai_compatible_chat_completions_usage",
        "extract_cohere_chat_usage",
        "extract_langchain_chat_usage",
        "extract_vercel_ai_sdk_usage",
        "extract_llamaindex_token_counter_usage",
        "extract_haystack_generator_usage",
        "extract_litellm_proxy_response_usage",
        "extract_ag2_usage_summary_usage",
    ]:
        assert_true(exported in python_init or exported in python_types, f"Python package missing {exported}")

    for exported in [
        "CalculateCost",
        "CalculateCostWithMode",
        "CalculateCostWithOptions",
        "AggregateCostLedgers",
        "ExtractUsageLedger",
        "PriceCardsFromLlmPrices",
        "PriceCardsFromLiteLLM",
        "PriceCardsFromModelsDev",
        "PriceCardsFromOfficialSnapshot",
        "PriceCardsFromOpenRouterModels",
        "PriceCardsFromPortkey",
        "PriceCardsFromSourceCache",
        "PriceCardsFromUserPricing",
        "PriceCardsFromHelicone",
        "PriceCardsFromJSONFile",
        "PriceCardsFromYAMLFile",
        "FromResponse",
        "FromLangChainMessage",
        "FromVercelAISDKResult",
        "FromLlamaIndexTokenCounter",
        "FromHaystackGeneratorResult",
        "FromLiteLLMResponse",
        "FromAG2UsageSummary",
    ]:
        assert_true(
            re.search(rf"// {exported}\b", go_source) is not None,
            f"Go exported function {exported} must have a doc comment",
        )

    assert_true("ExampleCalculateCost" in go_examples, "Go example test must include ExampleCalculateCost")
    assert_true("ExampleFromResponse" in go_examples, "Go example test must include ExampleFromResponse")


def check_fixture_floor() -> None:
    fixtures = sorted((ROOT / "fixtures").glob("*.json"))
    assert_true(len(fixtures) >= 68, f"expected at least 68 fixtures, found {len(fixtures)}")
    for path in fixtures:
        fixture = load_json(path)
        metadata = fixture.get("metadata")
        assert_true(isinstance(metadata, dict), f"{path.name} must include metadata")
        for key in ["requirement_ids", "provider", "surface", "scenario", "tags", "expected_languages"]:
            assert_true(key in metadata, f"{path.name} metadata missing {key}")
        languages = metadata.get("expected_languages")
        assert_true(isinstance(languages, list) and languages, f"{path.name} must declare expected languages")
        unknown = sorted(set(languages) - {"python", "javascript", "go"})
        assert_true(not unknown, f"{path.name} declares unknown expected languages: {unknown}")


def check_ci_workflow() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for command in [
        "npm test",
        "check_fixture_coverage.py",
        "check_fixture_generator.py",
        "check_source_refresh.py",
        "check_schema_taxonomy.py",
        "refresh_price_sources.py",
        "npm run check:packages",
        "npm run check:release",
        "npm run example:js",
        "npm run example:py",
        "python3 -m py_compile",
    ]:
        assert_true(command in workflow, f"CI workflow missing command: {command}")


def check_documented_partial_framework_paths() -> None:
    framework_notes = (ROOT / "docs/notes/framework-adapter-notes.md").read_text(encoding="utf-8")
    supported_surfaces = (ROOT / "docs/reference/supported-surfaces.md").read_text(encoding="utf-8")
    parity = (ROOT / "docs/notes/api-parity-matrix.md").read_text(encoding="utf-8")

    framework_note_terms = [
        "Semantic Kernel",
        "Haystack",
        "AutoGen / AG2",
        "LangSmith",
        "LiteLLM Proxy Response Metadata",
        "OpenRouter-Compatible SDK Paths",
    ]
    for term in framework_note_terms:
        assert_true(term in framework_notes, f"framework adapter notes missing framework path: {term}")

    for term in [
        "Semantic Kernel",
        "Haystack",
        "AutoGen / AG2",
        "LangSmith",
        "LiteLLM proxy",
        "OpenRouter-compatible SDK paths",
    ]:
        assert_true(term in supported_surfaces, f"supported surfaces missing framework path: {term}")
        assert_true(term in parity, f"API parity matrix missing framework path: {term}")

    for term in [
        "Semantic Kernel",
        "LangSmith",
        "OpenRouter-compatible SDK paths",
    ]:
        assert_true(term in supported_surfaces, f"supported surfaces missing partial framework path: {term}")
        assert_true(term in parity, f"API parity matrix missing partial framework path: {term}")


def main() -> int:
    check_required_files()
    check_json_files()
    check_package_metadata()
    check_public_api_artifacts()
    check_fixture_floor()
    check_ci_workflow()
    check_documented_partial_framework_paths()
    print("Project hygiene checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
