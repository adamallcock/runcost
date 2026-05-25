#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "PROJECT_PLAN.md",
    "PROGRESS_TRACKER.md",
    "docs/2026-05-25-api-reference.md",
    "docs/2026-05-25-custom-pricing-and-discounts.md",
    "docs/2026-05-25-debug-trace.md",
    "docs/2026-05-25-fixture-coverage.md",
    "docs/2026-05-25-package-installation.md",
    "docs/2026-05-25-quickstart.md",
    "docs/2026-05-25-source-adapters.md",
    "docs/2026-05-25-supported-surfaces.md",
    "docs/2026-05-25-warnings-and-limitations.md",
    "docs/POLYGLOT_TOOLCHAIN_DECISION.md",
    "docs/API_PARITY_MATRIX.md",
    "docs/PROVIDER_EXTRACTOR_NOTES.md",
    "docs/FRAMEWORK_ADAPTER_NOTES.md",
    "scripts/check_fixture_coverage.py",
    "scripts/check_package_installs.py",
    "packages/javascript/core/index.d.ts",
    "packages/python/runcost/types.py",
    "schemas/debug-trace.schema.json",
    "schemas/fixture.schema.json",
    "packages/go/ledger/example_test.go",
    ".github/workflows/ci.yml",
]

PUBLIC_API_NAMES = [
    "calculate_cost",
    "calculateCost",
    "CalculateCost",
    "CalculateCostWithOptions",
    "from_response",
    "fromResponse",
    "FromResponse",
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
    "extractOpenRouterChatCompletionsUsage",
    "extract_openrouter_chat_completions_usage",
    "extractOpenAICompatibleChatCompletionsUsage",
    "extract_openai_compatible_chat_completions_usage",
    "price_cards_from_litellm",
    "priceCardsFromLiteLLM",
    "PriceCardsFromLiteLLM",
    "price_cards_from_openrouter_models",
    "priceCardsFromOpenRouterModels",
    "PriceCardsFromOpenRouterModels",
    "price_cards_from_portkey",
    "priceCardsFromPortkey",
    "PriceCardsFromPortkey",
    "price_cards_from_user_pricing",
    "priceCardsFromUserPricing",
    "PriceCardsFromUserPricing",
    "price_cards_from_helicone",
    "priceCardsFromHelicone",
    "PriceCardsFromHelicone",
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

    js_package_path = ROOT / "packages/javascript/core/package.json"
    js_package = load_json(js_package_path)
    types_path = ROOT / "packages/javascript/core" / js_package.get("types", "")
    assert_true(types_path.exists(), "JavaScript package types field must point to an existing file")
    exports = js_package.get("exports", {}).get(".", {})
    assert_true(exports.get("types") == "./index.d.ts", "JavaScript package exports must expose index.d.ts")
    assert_true(not js_package.get("private", False), "JavaScript package must be publishable")
    assert_true("files" in js_package, "JavaScript package must define a publish file allowlist")


def check_public_api_artifacts() -> None:
    parity = (ROOT / "docs/API_PARITY_MATRIX.md").read_text(encoding="utf-8")
    typescript = (ROOT / "packages/javascript/core/index.d.ts").read_text(encoding="utf-8")
    python_init = (ROOT / "packages/python/runcost/__init__.py").read_text(encoding="utf-8")
    python_types = (ROOT / "packages/python/runcost/types.py").read_text(encoding="utf-8")
    go_source = (ROOT / "packages/go/ledger/ledger.go").read_text(encoding="utf-8")
    go_examples = (ROOT / "packages/go/ledger/example_test.go").read_text(encoding="utf-8")

    for name in PUBLIC_API_NAMES:
        assert_true(name in parity, f"API parity matrix missing {name}")

    for exported in [
        "calculateCost",
        "fromResponse",
        "fromLangChainMessage",
        "createRunCostVercelMiddleware",
        "fromVercelAISDKResult",
        "fromLlamaIndexTokenCounter",
        "priceCardsFromLlmPrices",
        "priceCardsFromLiteLLM",
        "priceCardsFromOpenRouterModels",
        "priceCardsFromPortkey",
        "priceCardsFromUserPricing",
        "priceCardsFromHelicone",
        "extractOpenAICompatibleChatCompletionsUsage",
        "extractCohereChatUsage",
        "extractLangChainChatUsage",
        "extractVercelAISDKUsage",
        "extractLlamaIndexTokenCounterUsage",
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
        "from_response",
        "from_langchain_message",
        "track_langchain_costs",
        "RunCostLangChainCallback",
        "from_vercel_ai_sdk_result",
        "from_llamaindex_token_counter",
        "price_cards_from_litellm",
        "price_cards_from_openrouter_models",
        "price_cards_from_portkey",
        "price_cards_from_user_pricing",
        "price_cards_from_helicone",
        "extract_openai_compatible_chat_completions_usage",
        "extract_cohere_chat_usage",
        "extract_langchain_chat_usage",
        "extract_vercel_ai_sdk_usage",
        "extract_llamaindex_token_counter_usage",
    ]:
        assert_true(exported in python_init or exported in python_types, f"Python package missing {exported}")

    for exported in [
        "CalculateCost",
        "CalculateCostWithMode",
        "CalculateCostWithOptions",
        "ExtractUsageLedger",
        "PriceCardsFromLlmPrices",
        "PriceCardsFromLiteLLM",
        "PriceCardsFromOpenRouterModels",
        "PriceCardsFromPortkey",
        "PriceCardsFromUserPricing",
        "PriceCardsFromHelicone",
        "FromResponse",
        "FromLangChainMessage",
        "FromVercelAISDKResult",
        "FromLlamaIndexTokenCounter",
    ]:
        assert_true(
            re.search(rf"// {exported}\b", go_source) is not None,
            f"Go exported function {exported} must have a doc comment",
        )

    assert_true("ExampleCalculateCost" in go_examples, "Go example test must include ExampleCalculateCost")
    assert_true("ExampleFromResponse" in go_examples, "Go example test must include ExampleFromResponse")


def check_fixture_floor() -> None:
    fixtures = sorted((ROOT / "fixtures").glob("*.json"))
    assert_true(len(fixtures) >= 52, f"expected at least 52 fixtures, found {len(fixtures)}")
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
        "npm run check:packages",
        "npm run example:js",
        "npm run example:py",
        "python3 -m py_compile",
    ]:
        assert_true(command in workflow, f"CI workflow missing command: {command}")


def main() -> int:
    check_required_files()
    check_json_files()
    check_package_metadata()
    check_public_api_artifacts()
    check_fixture_floor()
    check_ci_workflow()
    print("Project hygiene checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
